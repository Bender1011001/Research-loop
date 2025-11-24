import os
import time
import json
import pandas as pd
import autogen
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
from agentlightning import LightningClient, LightningTask

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
    You are a COMSOL Automation Expert using the 'mph' Python library.
    Your Role: Listen to the Architect, Alchemist, and Switchman, then WRITE THE CODE.
    
    CRITICAL INSTRUCTIONS:
    1. Import 'mph'.
    2. Connect to the server using: client = mph.start(cores=4)
    3. Create/Load a model.
    4. Apply the material props (Alchemist) and waveform (Switchman).
    5. SOLVE the study.
    6. Evaluate 'volts' and 'input_power'.
    7. Save results to 'current_run.csv'.
    8. Wrap code in ```python``` blocks.
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
    
    # 2. The Mathematician should have written code, and Admin should have run it.
    # We check the artifact.
    reward = get_reward_from_file("experiments/current_run.csv")
    print(f"--- CYCLE {iteration} END. REWARD: {reward} ---")
    
    # 3. Log to Lightning (Reinforcement Learning)
    coach.log_trajectory(
        prompt=initial_message,
        response=str(chat_result.chat_history),
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