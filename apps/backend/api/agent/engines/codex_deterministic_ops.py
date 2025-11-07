#!/usr/bin/env python3
"""
Deterministic Code Operations for Codex Engine
Provides reliable, non-LLM-dependent code transformations
"""

import ast
import re
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import json


class DeterministicOps:
    """Collection of deterministic code operations"""
    
    @staticmethod
    def add_import(file_path: Path, import_stmt: str) -> Tuple[bool, str]:
        """Add an import statement to a Python file"""
        try:
            content = file_path.read_text()
            tree = ast.parse(content)
            
            # Check if import already exists
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in import_stmt:
                            return True, "Import already exists"
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module in import_stmt:
                        return True, "Import already exists"
            
            # Find the right place to insert
            lines = content.splitlines(keepends=True)
            insert_line = 0
            
            # After module docstring
            if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Str):
                insert_line = tree.body[0].end_lineno
            
            # After existing imports
            for node in tree.body:
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    insert_line = max(insert_line, node.end_lineno)
                else:
                    break
            
            # Insert the import
            if insert_line > 0:
                lines.insert(insert_line, f"{import_stmt}\n")
            else:
                lines.insert(0, f"{import_stmt}\n")
            
            file_path.write_text(''.join(lines))
            return True, f"Added import at line {insert_line + 1}"
            
        except Exception as e:
            return False, f"Failed to add import: {e}"
    
    @staticmethod
    def remove_import(file_path: Path, module_name: str) -> Tuple[bool, str]:
        """Remove an import statement from a Python file"""
        try:
            content = file_path.read_text()
            tree = ast.parse(content)
            lines = content.splitlines(keepends=True)
            
            removed = False
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == module_name:
                            # Remove the line
                            del lines[node.lineno - 1:node.end_lineno]
                            removed = True
                            break
                elif isinstance(node, ast.ImportFrom):
                    if node.module == module_name:
                        del lines[node.lineno - 1:node.end_lineno]
                        removed = True
                        break
            
            if removed:
                file_path.write_text(''.join(lines))
                return True, f"Removed import of {module_name}"
            else:
                return True, f"Import {module_name} not found"
                
        except Exception as e:
            return False, f"Failed to remove import: {e}"
    
    @staticmethod
    def rename_function(file_path: Path, old_name: str, new_name: str) -> Tuple[bool, str]:
        """Rename a function in a Python file"""
        try:
            content = file_path.read_text()
            
            # Use regex for reliable renaming
            # Match function definitions
            def_pattern = rf'(\s*)def\s+{re.escape(old_name)}\s*\('
            content = re.sub(def_pattern, rf'\1def {new_name}(', content)
            
            # Match function calls (basic - won't catch all cases)
            call_pattern = rf'(?<!\w){re.escape(old_name)}\s*\('
            content = re.sub(call_pattern, f'{new_name}(', content)
            
            file_path.write_text(content)
            return True, f"Renamed {old_name} to {new_name}"
            
        except Exception as e:
            return False, f"Failed to rename function: {e}"
    
    @staticmethod
    def rename_class(file_path: Path, old_name: str, new_name: str) -> Tuple[bool, str]:
        """Rename a class in a Python file"""
        try:
            content = file_path.read_text()
            
            # Match class definitions - preserve the colon or parentheses
            def replace_class_def(match):
                indent = match.group(1)
                ending = match.group(2)
                return f"{indent}class {new_name}{ending}"
            
            class_pattern = rf'(\s*)class\s+{re.escape(old_name)}\s*([\(\:])'
            content = re.sub(class_pattern, replace_class_def, content)
            
            # Match instantiations and references (but not as part of other names)
            ref_pattern = rf'(?<!\w){re.escape(old_name)}(?!\w)'
            
            # Don't replace in class definition lines
            lines = content.splitlines(keepends=True)
            for i, line in enumerate(lines):
                if not re.match(rf'\s*class\s+{new_name}', line):
                    lines[i] = re.sub(ref_pattern, new_name, line)
            
            content = ''.join(lines)
            file_path.write_text(content)
            return True, f"Renamed class {old_name} to {new_name}"
            
        except Exception as e:
            return False, f"Failed to rename class: {e}"
    
    @staticmethod
    def add_function_parameter(file_path: Path, func_name: str, param_name: str, 
                              default_value: Optional[str] = None, 
                              after_param: Optional[str] = None) -> Tuple[bool, str]:
        """Add a parameter to a function"""
        try:
            content = file_path.read_text()
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == func_name:
                    # Build new parameter string
                    lines = content.splitlines()
                    func_line = lines[node.lineno - 1]
                    
                    # Extract current parameters
                    match = re.search(rf'def\s+{func_name}\s*\((.*?)\)', func_line, re.DOTALL)
                    if not match:
                        return False, "Could not parse function signature"
                    
                    params = match.group(1)
                    new_param = f"{param_name}={default_value}" if default_value else param_name
                    
                    if after_param and after_param in params:
                        # Insert after specific parameter
                        params = params.replace(after_param, f"{after_param}, {new_param}")
                    else:
                        # Add at the end
                        if params.strip():
                            params = f"{params}, {new_param}"
                        else:
                            params = new_param
                    
                    # Replace the function definition
                    new_func_line = re.sub(
                        rf'def\s+{func_name}\s*\(.*?\)',
                        f'def {func_name}({params})',
                        func_line
                    )
                    lines[node.lineno - 1] = new_func_line
                    
                    file_path.write_text('\n'.join(lines))
                    return True, f"Added parameter {param_name} to {func_name}"
            
            return False, f"Function {func_name} not found"
            
        except Exception as e:
            return False, f"Failed to add parameter: {e}"
    
    @staticmethod
    def extract_to_function(file_path: Path, start_line: int, end_line: int, 
                           func_name: str, params: List[str] = None) -> Tuple[bool, str]:
        """Extract lines of code into a new function"""
        try:
            lines = file_path.read_text().splitlines(keepends=True)
            
            # Extract the code block
            extracted = lines[start_line-1:end_line]
            
            # Determine indentation
            indent = len(extracted[0]) - len(extracted[0].lstrip())
            base_indent = ' ' * (indent - 4) if indent >= 4 else ''
            
            # Build function
            params_str = ', '.join(params) if params else ''
            func_lines = [f"{base_indent}def {func_name}({params_str}):\n"]
            func_lines.extend(extracted)
            
            # Replace original lines with function call
            call_args = ', '.join(params) if params else ''
            lines[start_line-1:end_line] = [f"{' ' * indent}{func_name}({call_args})\n"]
            
            # Find where to insert the function (before the current function/class)
            tree = ast.parse(file_path.read_text())
            insert_line = 0
            
            for node in tree.body:
                if hasattr(node, 'lineno') and node.lineno >= start_line:
                    insert_line = node.lineno - 1
                    break
            
            # Insert the new function
            for i, line in enumerate(func_lines):
                lines.insert(insert_line + i, line)
            
            file_path.write_text(''.join(lines))
            return True, f"Extracted lines {start_line}-{end_line} to function {func_name}"
            
        except Exception as e:
            return False, f"Failed to extract function: {e}"
    
    @staticmethod
    def update_json_file(file_path: Path, updates: Dict[str, Any], 
                        create_if_missing: bool = True) -> Tuple[bool, str]:
        """Update JSON file with new values"""
        try:
            if file_path.exists():
                data = json.loads(file_path.read_text())
            elif create_if_missing:
                data = {}
            else:
                return False, "File does not exist"
            
            # Apply updates
            for key, value in updates.items():
                if '.' in key:
                    # Handle nested keys
                    parts = key.split('.')
                    current = data
                    for part in parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    current[parts[-1]] = value
                else:
                    data[key] = value
            
            # Write back
            file_path.write_text(json.dumps(data, indent=2))
            return True, f"Updated {len(updates)} fields in {file_path.name}"
            
        except Exception as e:
            return False, f"Failed to update JSON: {e}"
    
    @staticmethod
    def add_type_hints(file_path: Path, func_name: str, 
                      param_types: Dict[str, str], 
                      return_type: Optional[str] = None) -> Tuple[bool, str]:
        """Add type hints to a function"""
        try:
            content = file_path.read_text()
            lines = content.splitlines(keepends=True)
            
            # Find function definition
            pattern = rf'def\s+{func_name}\s*\((.*?)\)(\s*)(:|->)'
            
            for i, line in enumerate(lines):
                match = re.search(pattern, line)
                if match:
                    params = match.group(1)
                    
                    # Add type hints to parameters
                    for param, type_hint in param_types.items():
                        params = re.sub(
                            rf'\b{param}\b(?!\s*[:=])',
                            f'{param}: {type_hint}',
                            params
                        )
                    
                    # Build new function signature
                    return_part = f" -> {return_type}:" if return_type else ":"
                    new_line = f"def {func_name}({params}){return_part}\n"
                    
                    lines[i] = new_line
                    file_path.write_text(''.join(lines))
                    return True, f"Added type hints to {func_name}"
            
            return False, f"Function {func_name} not found"
            
        except Exception as e:
            return False, f"Failed to add type hints: {e}"
    
    @staticmethod
    def move_function(source_file: Path, target_file: Path, 
                     func_name: str, update_imports: bool = True) -> Tuple[bool, str]:
        """Move a function from one file to another"""
        try:
            source_content = source_file.read_text()
            tree = ast.parse(source_content)
            
            # Find the function
            func_node = None
            for node in tree.body:
                if isinstance(node, ast.FunctionDef) and node.name == func_name:
                    func_node = node
                    break
            
            if not func_node:
                return False, f"Function {func_name} not found"
            
            # Extract function code
            lines = source_content.splitlines(keepends=True)
            func_code = ''.join(lines[func_node.lineno-1:func_node.end_lineno])
            
            # Remove from source
            del lines[func_node.lineno-1:func_node.end_lineno]
            source_file.write_text(''.join(lines))
            
            # Add to target
            if target_file.exists():
                target_content = target_file.read_text()
                if not target_content.endswith('\n'):
                    target_content += '\n'
                target_content += '\n' + func_code
            else:
                target_content = func_code
            
            target_file.write_text(target_content)
            
            # Update imports if requested
            if update_imports:
                # Add import to source file
                module_name = target_file.stem
                DeterministicOps.add_import(source_file, f"from {module_name} import {func_name}")
            
            return True, f"Moved {func_name} from {source_file.name} to {target_file.name}"
            
        except Exception as e:
            return False, f"Failed to move function: {e}"