import os
import time
import json
import re
import subprocess
import pandas as pd
import autogen
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
try:
    from agentlightning import LightningClient, LightningTask
except ImportError:
    class LightningClient:
        def __init__(self, agent_name): pass
        def log_trajectory(self, prompt, response, reward): print(f"[Mock Log] Reward: {reward}")
    class LightningTask:
        pass

from dynamic_builder import CodeAssembler

# --- CONFIGURATION ---
# Pointing to your local Qwen model
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

llm_config_thinker = {
    "config_list": config_list_thinker,
    "temperature": 0.7, # Higher creativity for the theorists
    "timeout": 600,
}

llm_config_coder = {
    "config_list": config_list_coder,
    "temperature": 0.2, # Lower temperature for the coder (precision)
}

# --- AGENT DEFINITIONS ---

# 1. The Architect (Theorist)
architect = AssistantAgent(
    name="Architect",
    llm_config=llm_config_thinker,
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
    llm_config=llm_config_thinker,
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
    llm_config=llm_config_thinker,
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
    llm_config=llm_config_coder, # Uses lower temp config
    system_message="""
    You are a Simulation Architect. You do NOT write Python code directly.
    Wait for the Critic to APPROVE the design before generating the plan.

    Your Output MUST be a single valid JSON block following this schema:

    {
      "engine": "comsol", // or "ansys", "ads"
      "model_name": "Experiment_Name",
      "structure": [
        { "type": "toroid", "params": { "major_radius": "50[mm]", ... } },
        { "type": "coil", "params": { "turns": "100", ... } }
      ],
      "materials": [
        { "type": "copper", "params": { ... } }
      ],
      "physics": [
        { "type": "magnetic_fields", "params": { ... } }
      ],
      "setup": {
        "type": "frequency_domain",
        "params": { "freq_list": "range(10, 1000, 10)" }
      },
      "results": [
        { "type": "plot_b_field", "params": { ... } }
      ]
    }
    Constraint: You must only use 'type' keys that exist in the loaded Pattern Library.
    """
)

# 5. The Critic (Reviewer)
critic = AssistantAgent(
    name="Critic",
    llm_config=llm_config_thinker,
    system_message="""
    You are a Skeptical Mainstream Physicist.
    Your Role: Review the proposed experiment.
    Check for: Conservation of Energy violations (unless explained by Regauging), thermal runaway risks, and syntax errors in the code.
    If the plan looks solid, say "APPROVE" and explicitly request the 'Mathematician' to generate the JSON configuration. If not, critique it.
    """
)

# 6. The Admin (Executor)
admin = UserProxyAgent(
    name="Admin",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    code_execution_config={
        "work_dir": "experiments",
        "use_docker": True
    }
)

# --- GROUP CHAT ORCHESTRATION ---
# This manages the conversation flow between the 5 experts

def custom_speaker_selection(last_speaker, groupchat):
    """
    Enforce a specific workflow:
    Admin -> Architect -> Alchemist -> Switchman -> Critic
    Critic -> (APPROVE) -> Mathematician
    Critic -> (Reject) -> Architect
    Mathematician -> Admin (End)
    """
    # Check for questions or clarifications to break rigidity
    if groupchat.messages:
        last_msg = groupchat.messages[-1]["content"]
        if "QUESTION" in last_msg.upper() or "CLARIFY" in last_msg.upper():
            return "auto"

    if last_speaker is admin:
        return architect
    elif last_speaker is architect:
        return alchemist
    elif last_speaker is alchemist:
        return switchman
    elif last_speaker is switchman:
        return critic
    elif last_speaker is critic:
        # Check if Critic approved
        last_msg = groupchat.messages[-1]["content"]
        if "APPROVE" in last_msg:
            return mathematician
        else:
            return architect
    elif last_speaker is mathematician:
        return admin
        
    return "auto"

groupchat = GroupChat(
    agents=[admin, architect, alchemist, switchman, mathematician, critic],
    messages=[],
    max_round=20, # Allow them to debate before coding
    speaker_selection_method=custom_speaker_selection
)

manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config_thinker)

# --- LIGHTNING LEARNING LOOP ---
coach = LightningClient(agent_name="Scalar_Team_Alpha")

def get_reward_from_file(filepath="experiments/current_run.csv", metric_col="volts"):
    try:
        df = pd.read_csv(filepath)
        v_out = df[metric_col].iloc[-1]
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
    print(f"Chat History Length: {len(chat_result.chat_history)}")
    
    max_retries = 3
    retry_count = 0
    success = False
    reward = 0.0
    execution_output = ""

    while retry_count < max_retries and not success:
        # We iterate through chat history to find the last message from Mathematician
        last_math_msg = None
        for msg in reversed(chat_result.chat_history):
            if msg.get("name") == "Mathematician":
                last_math_msg = msg.get("content")
                break
        
        if last_math_msg:
            try:
                # Attempt to parse JSON
                # Clean up potential markdown code blocks
                match = re.search(r"```json\s*(.*?)\s*```", last_math_msg, re.DOTALL)
                if match:
                    clean_json = match.group(1)
                else:
                    # Fallback or handle error if no JSON block found
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

                use_docker = admin.code_execution_config.get("use_docker", False)

                if use_docker:
                    # Ensure path uses forward slashes for Linux container
                    docker_script_path = script_path.replace(os.sep, '/')
                    cmd = [
                        'docker', 'run', '--rm',
                        '-v', f'{os.getcwd()}:/app',
                        '-w', '/app',
                        'python:3.10-slim',
                        'python', docker_script_path
                    ]
                else:
                    cmd = ['python', script_path]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=os.getcwd() # Ensure running from root so paths work
                )
                
                execution_output = f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
                print(execution_output)
                
                if result.returncode == 0:
                    # Check for results file
                    reward = get_reward_from_file("experiments/current_run.csv", "volts")
                    success = True
                else:
                    print("Simulation failed.")
                    reward = -1.0
                    error_msg = f"Simulation failed with error:\n{result.stderr}\nPlease adjust the JSON plan to fix this error."
                    print(f"Feeding back error to Mathematician: {error_msg}")
                    
                    # Feed error back to the chat
                    chat_result = admin.initiate_chat(
                        manager,
                        message=error_msg,
                        clear_history=False
                    )
                    retry_count += 1
                    
            except json.JSONDecodeError:
                print("Failed to parse JSON plan from Mathematician.")
                execution_output = "JSON Parse Error"
                reward = -0.5
                error_msg = "JSON Parse Error: The output was not valid JSON. Please output ONLY a valid JSON block."
                
                chat_result = admin.initiate_chat(
                    manager,
                    message=error_msg,
                    clear_history=False
                )
                retry_count += 1

            except Exception as e:
                print(f"Error during build/execution: {e}")
                execution_output = str(e)
                reward = -1.0
                error_msg = f"Error during build/execution: {str(e)}\nPlease adjust the JSON plan."
                
                chat_result = admin.initiate_chat(
                    manager,
                    message=error_msg,
                    clear_history=False
                )
                retry_count += 1
        else:
            print("No plan received from Mathematician.")
            reward = 0.0
            break

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
    while count < 1:
        count += 1
        try:
            research_cycle(count)
        except Exception as e:
            print(f"Error in cycle {count}: {e}")
        
        print("Cooling down logic circuits...")
        time.sleep(15)