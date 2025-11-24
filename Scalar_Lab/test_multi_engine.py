import unittest
import json
import os
import sys

# Add the current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dynamic_builder import CodeAssembler

class TestMultiEngine(unittest.TestCase):
    def test_ansys_generation(self):
        """
        Verify that the system can switch to the Ansys engine and generate the correct PyAEDT script.
        """
        
        # Mock Input
        mock_json_input = {
          "engine": "ansys",
          "project_name": "SaturationTest",
          "design_name": "MaxwellDesign1",
          "structure": [
            { "type": "box", "params": { "px": "0", "py": "0", "pz": "0", "dx": "10", "dy": "10", "dz": "10", "name": "Core", "material": "iron" } }
          ],
          "setup": {
            "type": "transient",
            "params": { "stop_time": "10ms", "time_step": "0.1ms" }
          },
          "analyze": [
            { "type": "run" }
          ]
        }
        
        print(f"Testing with mock input: {json.dumps(mock_json_input, indent=2)}")

        # Instantiate CodeAssembler
        try:
            assembler = CodeAssembler(engine="ansys")
        except Exception as e:
            self.fail(f"Failed to instantiate CodeAssembler: {e}")

        # Assemble Script
        try:
            script_content = assembler.assemble_script(mock_json_input)
        except Exception as e:
            self.fail(f"Failed to assemble script: {e}")

        # Assertions
        self.assertIn("from pyaedt import Maxwell3d", script_content, "Script should contain PyAEDT imports")
        self.assertIn("m3d = Maxwell3d", script_content, "Script should contain Maxwell3d instantiation")
        self.assertIn("m3d.modeler.create_box", script_content, "Script should contain box creation command")
        self.assertIn("m3d.create_setup", script_content, "Script should contain setup creation command")
        self.assertIn("m3d.analyze_setup", script_content, "Script should contain analyze command")

        print("\nGenerated Script Content Preview:")
        print("-" * 40)
        print(script_content[:500] + "..." if len(script_content) > 500 else script_content)
        print("-" * 40)

        # Write to file
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ansys_experiment.py")
        with open(script_path, "w") as f:
            f.write(script_content)
        
        self.assertTrue(os.path.exists(script_path), "Generated script file should exist")
        print(f"Successfully generated script at: {script_path}")

if __name__ == '__main__':
    unittest.main()