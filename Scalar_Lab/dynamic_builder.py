import json
import os

class CodeAssembler:
    """
    Universal Translator that converts a high-level JSON plan into an executable 
    Python script for a specific physics engine (COMSOL, Ansys, or ADS).
    """
    
    def __init__(self, engine):
        """
        Initialize the CodeAssembler with the target engine.
        
        Args:
            engine (str): The target physics engine ("comsol", "ansys", or "ads").
        """
        self.engine = engine.lower()
        self.library = self._load_library()

    def _load_library(self):
        """
        Load the corresponding JSON library pattern file based on the engine.
        
        Returns:
            dict: The loaded library dictionary.
            
        Raises:
            ValueError: If the engine is not supported.
            FileNotFoundError: If the library file does not exist.
        """
        base_path = os.path.dirname(os.path.abspath(__file__))
        library_path = os.path.join(base_path, 'library')
        
        if self.engine == 'comsol':
            filename = 'library_patterns.json'
        elif self.engine == 'ansys':
            filename = 'ansys_patterns.json'
        elif self.engine == 'ads':
            filename = 'ads_patterns.json'
        else:
            raise ValueError(f"Unsupported engine: {self.engine}. Must be 'comsol', 'ansys', or 'ads'.")
            
        full_path = os.path.join(library_path, filename)
        
        if not os.path.exists(full_path):
             raise FileNotFoundError(f"Library file not found: {full_path}")
             
        try:
            with open(full_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse library file {filename}: {e}")

    def assemble_script(self, plan):
        """
        Assemble the Python script based on the provided plan.
        
        Args:
            plan (dict): The high-level plan dictionary containing 'engine', 'model_name', 
                         'structure', and 'setup'.
                         
        Returns:
            str: The generated Python script.
        """
        script_lines = []
        
        # 1. Imports
        if 'imports' in self.library:
            for line in self.library['imports']:
                try:
                    # Format imports using top-level plan keys (e.g., model_name)
                    formatted_line = line.format(**plan)
                    script_lines.append(formatted_line)
                except KeyError as e:
                    raise ValueError(f"Missing parameter for import formatting: {e}")
        
        script_lines.append("") # Add spacing

        # 2. Structure/Geometry
        if 'structure' in plan:
            for item in plan['structure']:
                item_type = item.get('type')
                params = item.get('params', {})
                
                if not item_type:
                    continue
                    
                # Look up geometry shape in library
                if 'geometry_shapes' not in self.library or item_type not in self.library['geometry_shapes']:
                    raise ValueError(f"Geometry type '{item_type}' not found in library for engine '{self.engine}'")
                
                pattern_lines = self.library['geometry_shapes'][item_type]
                
                # Add comment for clarity
                script_lines.append(f"# Geometry: {item_type} (ID: {params.get('id', 'N/A')})")
                
                for line in pattern_lines:
                    try:
                        formatted_line = line.format(**params)
                        script_lines.append(formatted_line)
                    except KeyError as e:
                        raise ValueError(f"Missing parameter for geometry '{item_type}': {e}")
                script_lines.append("")

        # 3. Physics/Setup
        if 'setup' in plan:
            setup_items = plan['setup']
            # Handle both single dict and list of dicts for setup
            if isinstance(setup_items, dict):
                setup_items = [setup_items]
            
            for item in setup_items:
                item_type = item.get('type')
                params = item.get('params', {})
                
                if not item_type:
                    continue

                # Look up in physics_modules or studies
                pattern_lines = None
                category = None
                
                if 'physics_modules' in self.library and item_type in self.library['physics_modules']:
                    pattern_lines = self.library['physics_modules'][item_type]
                    category = "Physics"
                elif 'studies' in self.library and item_type in self.library['studies']:
                    pattern_lines = self.library['studies'][item_type]
                    category = "Study"
                elif 'setup' in self.library and item_type in self.library['setup']:
                    pattern_lines = self.library['setup'][item_type]
                    category = "Setup"
                
                if pattern_lines is None:
                     raise ValueError(f"Setup type '{item_type}' not found in physics_modules, studies, or setup for engine '{self.engine}'")
                
                script_lines.append(f"# {category}: {item_type}")
                
                for line in pattern_lines:
                    try:
                        formatted_line = line.format(**params)
                        script_lines.append(formatted_line)
                    except KeyError as e:
                        raise ValueError(f"Missing parameter for setup '{item_type}': {e}")
                script_lines.append("")

        return "\n".join(script_lines)