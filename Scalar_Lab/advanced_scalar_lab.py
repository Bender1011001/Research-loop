import os
import time
import json
import subprocess
import pandas as pd
import autogen
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
from agentlightning import LightningClient, LightningTask
from dynamic_builder import CodeAssembler

# --- CONFIGURATION ---
# Pointing to your local Qwen model
config_list = [
    {
        "model": "qwen2.5-coder:7b",
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
    }
]

llm_config = {
    "config_list": config_list,
    "temperature": 0.7, # Higher creativity for the theorists
    "timeout": 600,
}

code_config = {
    "config_list": config_list,
    "temperature": 0.2, # Lower temperature for the coder (precision)
}

# --- AGENT DEFINITIONS ---

# 1. The Architect (Theorist)
architect = AssistantAgent(
    name="Architect",
    llm_config=llm_config,
    system_message="""
    You are a Visionary Physicist specializing in Scalar Electrodynamics (Bearden/Tesla).
    Your Role: Propose high-level theories for energy extraction. 
    Focus on: Asymmetrical Regauging, Dipole maintenence, and breaking the Lorentz Gauge.
    Output: A clear hypothesis (e.g., "Resonate a metglas core at 4MHz to stress the A-field").
    """
)

# 2. The Alchemist (Materials)
alchemist = AssistantAgent(
    name="Alchemist",
    llm_config=llm_config,
    system_message="""
    You are a Condensed Matter Physicist. 
    Your Role: Select the core material and geometry based on the Architect's theory.
    Focus on: Magnetostriction, Barium Ferrite properties, and lattice vibration.
    Output: Material specifications (Permeability, Conductivity, Young's Modulus).
    """
)

# 3. The Switchman (Circuits)
switchman = AssistantAgent(
    name="Switchman",
    llm_config=llm_config,
    system_message="""
    You are a High-Voltage Pulse Engineer (Bedini style).
    Your Role: Design the drive circuit. 
    Focus on: Sharp gradients (di/dt), spark gaps, and avalanche transistors.
    Output: Pulse width, Duty cycle, and Voltage levels.
    """
)

# 4. The Mathematician (Coder)
mathematician = AssistantAgent(
    name="Mathematician",
    llm_config=code_config, # Uses lower temp config
    system_message="""
    You are a Simulation Architect. You do NOT write Python code directly. You translate the research team's theory into a JSON Configuration Plan for the Lab Builder.

    Your Output MUST be a single valid JSON block following this schema:

    {
      "engine": "comsol", // or "ansys", "ads"
      "model_name": "Experiment_Name",
      "structure": [
        { "type": "toroid", "params": { "major_radius": "50[mm]", ... } },
        { "type": "coil", "params": { "turns": "100", ... } }
      ],
      "setup": {
        "type": "frequency_domain",
        "params": { "freq_list": "range(10, 1000, 10)" }
      }
    }
    Constraint: You must only use 'type' keys that exist in the loaded Pattern Library.
    """
)

# 5. The Critic (Reviewer)
critic = AssistantAgent(
    name="Critic",
    llm_config=llm_config,
    system_message="""
    You are a Skeptical Mainstream Physicist.
    Your Role: Review the proposed experiment. 
    Check for: Conservation of Energy violations (unless explained by Regauging), thermal runaway risks, and syntax errors in the code.
    If the plan looks solid, say "APPROVE". If not, critique it.
    """
)

# 6. The Admin (Executor)
admin = UserProxyAgent(
    name="Admin",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    code_execution_config={
        "work_dir": "experiments",
        "use_docker": False
    }
)

# --- GROUP CHAT ORCHESTRATION ---
# This manages the conversation flow between the 5 experts
groupchat = GroupChat(
    agents=[admin, architect, alchemist, switchman, mathematician, critic], 
    messages=[], 
    max_round=12, # Allow them to debate before coding
    speaker_selection_method="auto"
)

manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config)

# --- LIGHTNING LEARNING LOOP ---
coach = LightningClient(agent_name="Scalar_Team_Alpha")

def get_reward_from_file(filepath):
    try:
        df = pd.read_csv(filepath)
        v_out = df['volts'].iloc[-1]
        # Simple Reward Function: Higher Voltage = Better
        if v_out > 1000: return 10.0
        if v_out > 100: return 5.0
        if v_out > 10: return 1.0
        return 0.1
    except:
        return -1.0 # Penalty for crashing

def research_cycle(iteration):
    print(f"--- CYCLE {iteration} START ---")
    
    # 1. Start the Team Chat
    # The Architect kicks it off
    initial_message = "Let's design a new experiment involving a Caduceus coil and a pre-stressed Ferrite core."
    
    chat_result = admin.initiate_chat(
        manager,
        message=initial_message
    )
    
    # 2. Extract JSON Plan from Mathematician's last message
    # We iterate through chat history to find the last message from Mathematician
    last_math_msg = None
    for msg in reversed(chat_result.chat_history):
        if msg.get("name") == "Mathematician":
            last_math_msg = msg.get("content")
            break
            
    reward = 0.0
    execution_output = ""
    
    if last_math_msg:
        try:
            # Attempt to parse JSON
            # Clean up potential markdown code blocks
            clean_json = last_math_msg.replace("```json", "").replace("```", "").strip()
            plan = json.loads(clean_json)
            
            print(f"Plan received: {plan.get('model_name', 'Unnamed')}")
            
            # 3. Build the Script
            assembler = CodeAssembler(engine=plan.get('engine', 'comsol'))
            script_content = assembler.assemble_script(plan)
            
            script_path = os.path.join("experiments", "current_run.py")
            with open(script_path, "w") as f:
                f.write(script_content)
                
            print(f"Script generated at: {script_path}")
            
            # 4. Execute the Script
            print("Executing simulation...")
            result = subprocess.run(
                ['python', script_path],
                capture_output=True,
                text=True,
                cwd=os.getcwd() # Ensure running from root so paths work
            )
            
            execution_output = f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            print(execution_output)
            
            if result.returncode == 0:
                # Check for results file
                reward = get_reward_from_file("experiments/current_run.csv")
            else:
                print("Simulation failed.")
                reward = -1.0
                
        except json.JSONDecodeError:
            print("Failed to parse JSON plan from Mathematician.")
            execution_output = "JSON Parse Error"
            reward = -0.5
        except Exception as e:
            print(f"Error during build/execution: {e}")
            execution_output = str(e)
            reward = -1.0
    else:
        print("No plan received from Mathematician.")
        reward = 0.0

    print(f"--- CYCLE {iteration} END. REWARD: {reward} ---")
    
    # 5. Log to Lightning (Reinforcement Learning)
    coach.log_trajectory(
        prompt=initial_message,
        response=str(chat_result.chat_history) + f"\n\nEXECUTION OUTPUT:\n{execution_output}",
        reward=reward
    )

if __name__ == "__main__":
    # Initialize
    if not os.path.exists("experiments"): os.mkdir("experiments")
    
    count = 0
    while True:
        count += 1
        try:
            research_cycle(count)
        except Exception as e:
            print(f"Error in cycle {count}: {e}")
        
        print("Cooling down logic circuits...")
        time.sleep(15)