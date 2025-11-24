import json
import re
import os
import subprocess
import pandas as pd
from collections import Counter
from autogen import AssistantAgent, UserProxyAgent

# IMPORT EXISTING TOOLS
from dynamic_builder import CodeAssembler

# --- CONFIGURATION (Reusing your existing configs) ---
config_list_coder = [
    {
        "model": "qwen2.5-coder:7b",
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
    }
]

config_list_thinker = [
    {
        "model": "deepseek-r1:7b",
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
    }
]

llm_config_thinker = {"config_list": config_list_thinker, "temperature": 0.7, "timeout": 600}
llm_config_coder = {"config_list": config_list_coder, "temperature": 0.2}

class ScalarMaker:
    def __init__(self):
        # THE ATOMIC STATE (Replaces Chat History)
        self.state = {
            "hypothesis": None,
            "materials": None,
            "circuit": None,
            "simulation_plan": None
        }
        
        # --- INITIALIZE AGENTS ---
        # We reuse your prompt definitions but will use them statelessly
        self.architect = AssistantAgent(
            "Architect", 
            llm_config=llm_config_thinker, 
            system_message="You are a Visionary Physicist. Propose high-level theories for energy extraction."
        )
        self.alchemist = AssistantAgent(
            "Alchemist", 
            llm_config=llm_config_thinker, 
            system_message="You are a Condensed Matter Physicist. Select core materials and geometry."
        )
        self.switchman = AssistantAgent(
            "Switchman", 
            llm_config=llm_config_thinker, 
            system_message="You are a High-Voltage Pulse Engineer. Design the drive circuit."
        )
        # Note: Mathematician uses low temp for coding
        self.mathematician = AssistantAgent(
            "Mathematician", 
            llm_config=llm_config_coder, 
            system_message="You are a Simulation Architect. Output ONLY valid JSON for the simulation plan."
        )
        self.critic = AssistantAgent(
            "Critic", 
            llm_config=llm_config_thinker, 
            system_message="You are a Skeptical Physicist. Verify the logic."
        )
        
        # Executor (Admin)
        self.admin = UserProxyAgent("Admin", human_input_mode="NEVER", code_execution_config=False)

    def _stateless_call(self, agent, prompt):
        """
        PILLAR 1: MAXIMAL DECOMPOSITION
        Reset agent memory before every call. No history = No drift.
        """
        agent.reset() 
        self.admin.reset()
        
        # 1-turn interaction only
        result = self.admin.initiate_chat(
            agent,
            message=prompt,
            max_turns=1,
            clear_history=True
        )
        return result.chat_history[-1]['content']

    def _extract_json_strict(self, text):
        """
        PILLAR 2: RED FLAGGING
        If JSON is invalid, return None immediately. Do not attempt to repair.
        """
        try:
            # Regex to find code blocks
            match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
            if match:
                json_str = match.group(1)
            else:
                # Fallback: try to find the first { and last }
                json_str = text[text.find("{"):text.rfind("}")+1]
                
            return json.loads(json_str)
        except:
            return None

    def _generate_with_voting(self, agent, prompt, voters=3):
        """
        PILLAR 3: BEST-OF-K VOTING
        Generate multiple attempts. Filter for valid syntax. Select the best.
        """
        candidates = []
        print(f"   [Voting] Requesting {voters} drafts from {agent.name}...")
        
        for i in range(voters):
            response = self._stateless_call(agent, prompt)
            json_obj = self._extract_json_strict(response)
            
            if json_obj:
                print(f"     -> Draft {i+1}: Valid JSON")
                candidates.append(json_obj)
            else:
                print(f"     -> Draft {i+1}: [RED FLAG] Invalid JSON. Discarded.")

        if not candidates:
            raise ValueError(f"{agent.name} failed to produce valid output in {voters} attempts.")

        # If we have multiple valid candidates, ask the Critic to pick the best one
        if len(candidates) == 1:
            return candidates[0]
            
        return self._run_critic_selection(candidates)

    def _run_critic_selection(self, candidates):
        # Format candidates for the Critic
        candidates_str = "\n\n".join([f"--- OPTION {i} ---\n{json.dumps(c)}" for i, c in enumerate(candidates)])
        
        prompt = f"""
        Review these {len(candidates)} simulation plans.
        Select the best one based on: 
        1. Correct use of the Pattern Library (e.g., 'toroid', 'frequency_domain').
        2. Physical consistency with the hypothesis.
        
        Return ONLY the integer number of the best option (e.g., "0" or "1").
        
        {candidates_str}
        """
        
        selection = self._stateless_call(self.critic, prompt)
        try:
            # Extract the number
            idx = int(re.search(r"\d+", selection).group())
            return candidates[idx] if idx < len(candidates) else candidates[0]
        except:
            return candidates[0] # Fallback to first valid option

    def run_cycle(self):
        print("--- STARTING MAKER PIPELINE ---")
        
        # STEP 1: ARCHITECT
        # Pure creativity, no history needed
        self.state['hypothesis'] = self._stateless_call(
            self.architect, 
            "Goal: Propose a Scalar Electrodynamics experiment to extract energy from the vacuum using asymmetrical regauging. Output a concise hypothesis."
        )
        print(f"\n1. Hypothesis Generated:\n{self.state['hypothesis'][:100]}...\n")

        # STEP 2: ALCHEMIST
        # We manually inject the hypothesis into the prompt
        self.state['materials'] = self._stateless_call(
            self.alchemist,
            f"Based on this hypothesis:\n'{self.state['hypothesis']}'\n\nSelect core materials and geometry. Output detailed specifications."
        )
        print("2. Materials Selected.")

        # STEP 3: SWITCHMAN
        # We inject both previous states
        self.state['circuit'] = self._stateless_call(
            self.switchman,
            f"Hypothesis: {self.state['hypothesis']}\nMaterials: {self.state['materials']}\n\nDesign the pulse drive circuit (Bedini/Switching style)."
        )
        print("3. Circuit Designed.")

        # STEP 4: MATHEMATICIAN (THE CRITICAL STEP)
        # We compile the full 'Design Packet'
        design_packet = json.dumps(self.state, indent=2)
        
        # We explicitly attach the Pattern Library documentation here if needed, 
        # or rely on the system message.
        math_prompt = f"""
        You are a Simulation Architect.
        
        CONTEXT:
        {design_packet}
        
        TASK:
        Generate the JSON simulation plan for COMSOL or Ansys.
        You MUST follow the Pattern Library structure (e.g., 'structure', 'materials', 'setup').
        
        CRITICAL RULES:
        1. Output ONLY valid JSON.
        2. Do NOT use mathematical expressions (e.g., "2 * Math.PI"). Calculate the value yourself (e.g., 6.28).
        3. Do NOT use comments inside the JSON.
        """
        
        try:
            # USE VOTING HERE to ensure valid JSON
            final_plan = self._generate_with_voting(self.mathematician, math_prompt, voters=3)
            print("\n4. Plan Generated & Verified via Voting.")
            
            # STEP 5: EXECUTION (Reuse your existing logic)
            self._execute_plan(final_plan)
            
        except Exception as e:
            print(f"Pipeline Failed: {e}")

    def _execute_plan(self, plan):
        print("\n--- BUILDING SIMULATION ---")
        # Reuse your existing CodeAssembler logic
        assembler = CodeAssembler(engine=plan.get('engine', 'comsol'))
        script_content = assembler.assemble_script(plan)
        
        script_path = os.path.join("experiments", "current_run.py")
        if not os.path.exists("experiments"): os.mkdir("experiments")
        
        with open(script_path, "w") as f:
            f.write(script_content)
            
        print(f"Script saved to: {script_path}")
        print("Executing...")
        
        # Run the script
        result = subprocess.run(
            ['python', script_path],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")

if __name__ == "__main__":
    maker = ScalarMaker()
    maker.run_cycle()