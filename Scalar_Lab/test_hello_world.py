import unittest
import json
import os
import sys

# Add the current directory to sys.path to ensure imports work correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dynamic_builder import CodeAssembler

class TestHelloWorld(unittest.TestCase):
    def test_hello_world_simulation(self):
        """
        Simulate a simple air-core inductor at 60Hz using the CodeAssembler.
        This mocks the Mathematician agent's output and verifies the downstream execution logic.
        """
        
        # Mock Input from Mathematician Agent
        mock_json_input = {
          "engine": "comsol",
          "model_name": "AirCoreInductor",
          "structure": [
            { "type": "cylinder", "params": { "radius": "10[mm]", "height": "50[mm]", "px": "0", "py": "0", "pz": "0", "ax": "0", "ay": "0", "az": "1", "id": "1" } }
          ],
          "setup": {
            "type": "frequency_domain",
            "params": { "freq_range": "60[Hz]" }
          }
        }
        
        print(f"Testing with mock input: {json.dumps(mock_json_input, indent=2)}")

        # Instantiate CodeAssembler
        try:
            assembler = CodeAssembler(engine="comsol")
        except Exception as e:
            self.fail(f"Failed to instantiate CodeAssembler: {e}")

        # Assemble Script
        try:
            script_content = assembler.assemble_script(mock_json_input)
        except Exception as e:
            self.fail(f"Failed to assemble script: {e}")

        # Assertions
        self.assertIn("model.geometries.create", script_content, "Script should contain geometry creation command")
        self.assertIn("frequency_domain", script_content, "Script should contain frequency domain setup")
        self.assertIn("AirCoreInductor", script_content, "Script should contain the model name")
        self.assertIn("10[mm]", script_content, "Script should contain the radius parameter")
        
        print("\nGenerated Script Content Preview:")
        print("-" * 40)
        print(script_content[:500] + "..." if len(script_content) > 500 else script_content)
        print("-" * 40)

        # Optional: Attempt to run the generated script (Mocking subprocess if needed)
        # Since we likely don't have COMSOL, we just verify the file generation and content.
        
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hello_world_experiment.py")
        with open(script_path, "w") as f:
            f.write(script_content)
        
        self.assertTrue(os.path.exists(script_path), "Generated script file should exist")
        print(f"Successfully generated script at: {script_path}")
        
        # Clean up
        if os.path.exists(script_path):
            os.remove(script_path)

if __name__ == '__main__':
    unittest.main()