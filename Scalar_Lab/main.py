import autogen
import agentlightning
import pandas as pd
import json
import os

# LLM Configuration for Ollama
config_list = [
    {
        "model": "qwen2.5-coder:7b",
        "base_url": "http://localhost:11434",
        "api_key": "ollama",
    }
]
llm_config = {"config_list": config_list, "cache_seed": 42}

# Scientist Agent: Proposes simulation parameters
scientist = autogen.AssistantAgent(
    name="Scientist",
    system_message="""You are a rogue theoretical physicist specializing in Scalar Electrodynamics, Tom Bearden, and Tesla. 
Your goal is to propose simulation parameters (Frequency in Hz, Core Material e.g., 'Ferrite', Winding Type e.g., 'Bifilar') 
that might demonstrate Overunity or A-Field interactions. 
Output strictly in valid JSON format, nothing else. 
Example: {"frequency": 1000000, "core_material": "Ferrite", "winding_type": "Bifilar"}""",
    llm_config=llm_config,
)

# Engineer Agent: Writes and executes COMSOL simulation scripts
engineer_system_msg = """You are a COMSOL automation expert. You write complete, standalone Python scripts using the MPh library. 
You NEVER ask for user input or pose questions. You always write runnable code that saves results to 'experiment_result.csv' 
with exactly these columns: 'input_voltage', 'voltage_reading'.

Use this exact MPh connection and simulation pattern:

```python
import mph
import pandas as pd

try:
    client = mph.start(cores=4)
except:
    client = mph.start(executable=r"C:\Program Files\COMSOL\COMSOL64\Multiphysics\bin\win64\comsolphserver.exe")

model = client.load("base_template.mph")

# Set parameters from input JSON, e.g.:
# model.parameter("freq", str(params["frequency"]))
# model.parameter("core_material", params["core_material"])
# model.parameter("winding_type", params["winding_type"])

model.solve()

# Extract values - adjust expressions based on model (e.g., probe or global evaluation)
input_voltage = float(model.evaluate("V_in"))  # Replace with actual input voltage expression
voltage_reading = float(model.evaluate("V_out"))  # Replace with actual output voltage reading expression

pd.DataFrame({
    "input_voltage": [input_voltage],
    "voltage_reading": [voltage_reading]
}).to_csv("experiment_result.csv", index=False)

client.disconnect()
```

Adapt the parameter names and evaluation expressions to match the 'base_template.mph' model. 
Ensure the code is complete, imports everything needed, and handles the provided parameters.
After the code block, respond with only: TERMINATE."""

engineer = autogen.AssistantAgent(
    name="Engineer",
    system_message=engineer_system_msg,
    llm_config=llm_config,
)

# Admin Agent: Orchestrates, executes code automatically
code_exec_config = {
    "work_dir": "experiments",
    "use_docker": False,
}
admin = autogen.UserProxyAgent(
    name="Admin",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    is_termination_msg=lambda x: "TERMINATE" in x.get("content", "") or x.get("content", "").rstrip().endswith("TERMINATE"),
    code_execution_config=code_exec_config,
)

# Lightning Client for logging trajectories
coach = agentlightning.LightningClient(agent_name="Tesla_Bot")

def run_cycle():
    """Execute one full cycle: Scientist proposes -> Engineer simulates -> Evaluate reward -> Log."""
    print("Starting cycle...")
    
    # Step 1: Get parameters from Scientist
    scientist_prompt = """Propose simulation parameters (Frequency in Hz, Core Material e.g., 'Ferrite', Winding Type e.g., 'Bifilar') 
that might demonstrate Overunity or A-Field interactions. 
Output ONLY valid JSON: {"frequency": number, "core_material": "str", "winding_type": "str"}"""
    
    res_scientist = admin.initiate_chat(scientist, message=scientist_prompt)
    scientist_content = res_scientist.content.strip()
    
    try:
        params = json.loads(scientist_content)
        print(f"Scientist params: {params}")
    except json.JSONDecodeError as e:
        print(f"Failed to parse Scientist JSON: {e}")
        voltage_reading = 0.0
        reward = -1.0
        coach.log_trajectory(prompt="Cycle Start", response="parse_error", reward=reward)
        return
    
    # Step 2: Engineer writes and executes simulation code
    engineer_prompt = f"""Using these Scientist parameters: {json.dumps(params)}

Write the complete code to run COMSOL simulation on base_template.mph, set parameters, solve, extract input_voltage and voltage_reading, 
save to experiment_result.csv, and disconnect."""
    
    res_engineer = admin.initiate_chat(engineer, message=engineer_prompt)
    print("Engineer simulation completed.")
    
    # Step 4: Read results
    csv_path = os.path.join("experiments", "experiment_result.csv")
    try:
        df = pd.read_csv(csv_path)
        if df.empty:
            raise ValueError("CSV is empty")
        input_voltage = float(df['input_voltage'].iloc[0])
        voltage_reading = float(df['voltage_reading'].iloc[0])
        print(f"Results: input_voltage={input_voltage}, voltage_reading={voltage_reading}")
    except Exception as e:
        print(f"Failed to read/process results: {e}")
        voltage_reading = 0.0
        input_voltage = 0.0
    
    # Step 5: Calculate reward
    if voltage_reading > input_voltage:
        reward = 10.0
    elif voltage_reading > 0:
        reward = 1.0
    else:
        reward = -1.0
    
    # Step 6: Log to Lightning
    coach.log_trajectory(
        prompt="Cycle Start", 
        response=f"{voltage_reading:.6f}", 
        reward=reward
    )
    
    print(f"Cycle complete. Reward: {reward}")

if __name__ == "__main__":
    # Ensure experiments dir exists
    os.makedirs("experiments", exist_ok=True)
    run_cycle()