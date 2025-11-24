import unittest
import json
from dynamic_builder import CodeAssembler

class TestCodeAssembler(unittest.TestCase):
    def test_comsol_assembly(self):
        plan = {
            "engine": "comsol",
            "model_name": "TestModel",
            "structure": [
                { 
                    "type": "cylinder", 
                    "params": { 
                        "radius": "10[mm]", 
                        "height": "20[mm]", 
                        "px": "0", 
                        "py": "0", 
                        "pz": "0", 
                        "ax": "0", 
                        "ay": "0", 
                        "az": "1", 
                        "id": "1" 
                    } 
                }
            ],
            "setup": {
                "type": "frequency_domain",
                "params": { "freq_range": "range(10, 1000, 10)" }
            }
        }
        
        assembler = CodeAssembler("comsol")
        script = assembler.assemble_script(plan)
        
        print("\n--- Generated Script ---\n")
        print(script)
        print("\n------------------------\n")
        
        self.assertIn("import mph", script)
        self.assertIn("model = client.create('TestModel')", script)
        self.assertIn("cyl = geom.create('cyl1', 'Cylinder')", script)
        self.assertIn("cyl.property('r', '10[mm]')", script)
        self.assertIn("freq.property('plist', 'range(10, 1000, 10)')", script)

if __name__ == '__main__':
    unittest.main()