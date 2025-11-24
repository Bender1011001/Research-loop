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

    def _find_pattern(self, type_name):
        """
        Search for a component type across all top-level library categories.
        
        Args:
            type_name (str): The name of the component type to find.
            
        Returns:
            tuple: (pattern_lines, category_name) or (None, None) if not found.
        """
        # Iterate through all top-level keys in the library
        for category, content in self.library.items():
            # We only search inside dictionaries (categories like geometry_shapes, components, etc.)
            if isinstance(content, dict):
                if type_name in content:
                    return content[type_name], category
        return None, None

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

        # 1.5 Init Project (Engine Specific)
        if 'init_project' in self.library:
            for line in self.library['init_project']:
                try:
                    formatted_line = line.format(**plan)
                    script_lines.append(formatted_line)
                except KeyError as e:
                    raise ValueError(f"Missing parameter for init_project formatting: {e}")
            script_lines.append("")

        # 2. Structure/Geometry
        if 'structure' in plan:
            for item in plan['structure']:
                item_type = item.get('type')
                params = item.get('params', {})
                
                if not item_type:
                    continue
                    
                # Use helper to find pattern
                pattern_lines, category = self._find_pattern(item_type)
                
                if not pattern_lines:
                    raise ValueError(f"Component type '{item_type}' not found in library for engine '{self.engine}'")
                
                # Add comment for clarity
                script_lines.append(f"# {category}: {item_type} (ID: {params.get('id', 'N/A')})")
                
                for line in pattern_lines:
                    try:
                        formatted_line = line.format(**params)
                        script_lines.append(formatted_line)
                    except KeyError as e:
                        raise ValueError(f"Missing parameter for component '{item_type}': {e}")
                script_lines.append("")

        # 3. Materials
        if 'materials' in plan:
            for item in plan['materials']:
                item_type = item.get('type')
                params = item.get('params', {})
                
                if not item_type:
                    continue
                    
                pattern_lines, category = self._find_pattern(item_type)
                
                if not pattern_lines:
                    raise ValueError(f"Material type '{item_type}' not found in library for engine '{self.engine}'")
                
                script_lines.append(f"# {category}: {item_type}")
                
                for line in pattern_lines:
                    try:
                        formatted_line = line.format(**params)
                        script_lines.append(formatted_line)
                    except KeyError as e:
                        raise ValueError(f"Missing parameter for material '{item_type}': {e}")
                script_lines.append("")

        # 4. Physics
        if 'physics' in plan:
            for item in plan['physics']:
                item_type = item.get('type')
                params = item.get('params', {})
                
                if not item_type:
                    continue
                    
                pattern_lines, category = self._find_pattern(item_type)
                
                if not pattern_lines:
                    raise ValueError(f"Physics type '{item_type}' not found in library for engine '{self.engine}'")
                
                script_lines.append(f"# {category}: {item_type}")
                
                for line in pattern_lines:
                    try:
                        formatted_line = line.format(**params)
                        script_lines.append(formatted_line)
                    except KeyError as e:
                        raise ValueError(f"Missing parameter for physics '{item_type}': {e}")
                script_lines.append("")

        # 5. Setup/Studies
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

                # Use helper to find pattern
                pattern_lines, category = self._find_pattern(item_type)
                
                if not pattern_lines:
                     raise ValueError(f"Setup type '{item_type}' not found in library for engine '{self.engine}'")
                
                script_lines.append(f"# {category}: {item_type}")
                
                for line in pattern_lines:
                    try:
                        formatted_line = line.format(**params)
                        script_lines.append(formatted_line)
                    except KeyError as e:
                        raise ValueError(f"Missing parameter for setup '{item_type}': {e}")
                script_lines.append("")

        # 5.5 Analyze (Engine Specific)
        if 'analyze' in self.library:
            # Analyze might be a simple list of commands or a dict of types
            # For Ansys it is a dict with "run"
            # We can check if plan has an 'analyze' section or just run default
            
            # If the library has 'analyze' as a dict, we look for 'analyze' in plan
            if isinstance(self.library['analyze'], dict):
                 if 'analyze' in plan:
                    for item in plan['analyze']:
                        item_type = item.get('type')
                        params = item.get('params', {})
                        
                        if not item_type:
                            continue
                            
                        pattern_lines, category = self._find_pattern(item_type)
                        
                        if not pattern_lines:
                             raise ValueError(f"Analyze type '{item_type}' not found in library for engine '{self.engine}'")
                        
                        script_lines.append(f"# {category}: {item_type}")
                        for line in pattern_lines:
                            try:
                                formatted_line = line.format(**params)
                                script_lines.append(formatted_line)
                            except KeyError as e:
                                raise ValueError(f"Missing parameter for analyze '{item_type}': {e}")
                        script_lines.append("")
            
            # If it's a list (direct commands), just append them
            elif isinstance(self.library['analyze'], list):
                 for line in self.library['analyze']:
                    try:
                        formatted_line = line.format(**plan)
                        script_lines.append(formatted_line)
                    except KeyError as e:
                        raise ValueError(f"Missing parameter for analyze formatting: {e}")
                 script_lines.append("")

        # 6. Results
        if 'results' in plan:
            for item in plan['results']:
                item_type = item.get('type')
                params = item.get('params', {})
                
                if not item_type:
                    continue
                    
                pattern_lines, category = self._find_pattern(item_type)
                
                if not pattern_lines:
                    raise ValueError(f"Result type '{item_type}' not found in library for engine '{self.engine}'")
                
                script_lines.append(f"# {category}: {item_type}")
                
                for line in pattern_lines:
                    try:
                        formatted_line = line.format(**params)
                        script_lines.append(formatted_line)
                    except KeyError as e:
                        raise ValueError(f"Missing parameter for result '{item_type}': {e}")
                script_lines.append("")

        return "\n".join(script_lines)