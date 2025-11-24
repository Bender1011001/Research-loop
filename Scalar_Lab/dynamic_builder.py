import json
import os
from collections import defaultdict

class SafeDict(dict):
    def __missing__(self, key):
        return f"{{{key}}}"

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
        
        # Helper to safely format lines
        def safe_format(lines, params, context_name="unknown"):
            for line in lines:
                try:
                    # Use SafeDict to handle missing keys gracefully
                    formatted_line = line.format(**SafeDict(params))
                    script_lines.append(formatted_line)
                except Exception as e:
                    # Log warning instead of crashing
                    script_lines.append(f"# WARNING: Failed to format line in {context_name}: {line} -> {e}")

        # 1. Imports
        if 'imports' in self.library:
            safe_format(self.library['imports'], plan, "imports")
        
        script_lines.append("") # Add spacing

        # 1.5 Init Project (Engine Specific)
        if 'init_project' in self.library:
            safe_format(self.library['init_project'], plan, "init_project")
            script_lines.append("")

        # Helper for processing sections
        def process_section(section_name):
            if section_name in plan:
                items = plan[section_name]
                if isinstance(items, dict): items = [items]
                
                for item in items:
                    item_type = item.get('type')
                    params = item.get('params', {})
                    
                    if not item_type:
                        continue
                        
                    pattern_lines, category = self._find_pattern(item_type)
                    
                    if not pattern_lines:
                        script_lines.append(f"# WARNING: {section_name} type '{item_type}' not found in library")
                        continue
                    
                    script_lines.append(f"# {category}: {item_type} (ID: {params.get('id', 'N/A')})")
                    safe_format(pattern_lines, params, f"{section_name}:{item_type}")
                    script_lines.append("")

        # 2. Structure/Geometry
        process_section('structure')

        # 3. Materials
        process_section('materials')

        # 4. Physics
        process_section('physics')

        # 5. Setup/Studies
        process_section('setup')

        # 5.5 Analyze (Engine Specific)
        if 'analyze' in self.library:
            lib_analyze = self.library['analyze']
            
            # Case A: Library defines a set of patterns (Dict)
            if isinstance(lib_analyze, dict):
                plan_analyze = plan.get('analyze', [])
                
                # Handle if plan_analyze is a dict (single item) or list of strings
                if isinstance(plan_analyze, dict):
                    plan_analyze = [plan_analyze]
                
                if isinstance(plan_analyze, list):
                    for item in plan_analyze:
                        # Handle if item is just a string (key)
                        if isinstance(item, str):
                            item_type = item
                            params = {}
                        else:
                            item_type = item.get('type')
                            params = item.get('params', {})
                        
                        if not item_type: continue
                        
                        pattern_lines, category = self._find_pattern(item_type)
                        if not pattern_lines:
                             script_lines.append(f"# WARNING: Analyze type '{item_type}' not found.")
                             continue

                        script_lines.append(f"# {category}: {item_type}")
                        safe_format(pattern_lines, params, f"analyze:{item_type}")
                        script_lines.append("")
                                
            # Case B: Library defines a fixed list of commands (List)
            elif isinstance(lib_analyze, list):
                 safe_format(lib_analyze, plan, "analyze_fixed")
                 script_lines.append("")

        # 6. Results
        process_section('results')

        return "\n".join(script_lines)