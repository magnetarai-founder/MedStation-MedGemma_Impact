#!/usr/bin/env python3
"""
Enhanced codemods for Codex engine
- Import updates (add, remove, organize)
- Module moves (with import updates)
- Extract function/class operations
"""

import ast
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
import difflib


class CodemodOperations:
    """Advanced codemod operations for Python code"""
    
    @staticmethod
    def update_imports_for_moved_module(repo_root: Path, old_module_path: str, 
                                       new_module_path: str,
                                       include_globs: Optional[List[str]] = None,
                                       exclude_globs: Optional[List[str]] = None,
                                       files_list: Optional[List[str]] = None) -> str:
        """
        Update all imports when a module is moved
        e.g., 'utils.helpers' -> 'core.utils.helpers'
        """
        # Convert file paths to module paths if needed
        old_module = old_module_path.replace('/', '.').replace('.py', '')
        new_module = new_module_path.replace('/', '.').replace('.py', '')
        # JS/TS style import paths
        old_path_imp = old_module_path.replace('.py', '').replace('.', '/').replace('\\', '/')
        new_path_imp = new_module_path.replace('.py', '').replace('.', '/').replace('\\', '/')
        
        diffs = []
        
        # Search for imports of the old module
        # Build candidate file list
        candidates: List[Path] = []
        if files_list:
            for fp in files_list:
                p = (repo_root / fp).resolve()
                if p.exists() and p.is_file():
                    candidates.append(p)
        else:
            patterns = include_globs or ["**/*.py", "**/*.js", "**/*.jsx", "**/*.ts", "**/*.tsx"]
            for pat in patterns:
                for p in repo_root.glob(pat):
                    if p.is_file():
                        candidates.append(p)
        # Apply excludes
        if exclude_globs:
            excluded: Set[Path] = set()
            for pat in exclude_globs:
                for p in repo_root.glob(pat):
                    if p.is_file():
                        excluded.add(p.resolve())
            candidates = [p for p in candidates if p.resolve() not in excluded]

        for py_file in candidates:
            if not py_file.is_file():
                continue
                
            try:
                content = py_file.read_text()
                original = content
                
                if py_file.suffix == '.py':
                    # Python patterns
                    pattern1 = rf'from\s+{re.escape(old_module)}\s+import'
                    content = re.sub(pattern1, f'from {new_module} import', content)
                    pattern2 = rf'^import\s+{re.escape(old_module)}(\s|$)'
                    content = re.sub(pattern2, f'import {new_module}\\1', content, flags=re.MULTILINE)
                    pattern3 = rf'import\s+{re.escape(old_module)}\s+as'
                    content = re.sub(pattern3, f'import {new_module} as', content)
                elif py_file.suffix in {'.js', '.jsx', '.ts', '.tsx'}:
                    # JS/TS patterns
                    content = re.sub(
                        rf"(import\s+[^;]*?from\s+['\"]){re.escape(old_path_imp)}(['\"])",
                        rf"\1{new_path_imp}\2",
                        content
                    )
                    content = re.sub(
                        rf"(import\s+['\"]){re.escape(old_path_imp)}(['\"])",
                        rf"\1{new_path_imp}\2",
                        content
                    )
                    content = re.sub(
                        rf"(require\(\s*['\"]){re.escape(old_path_imp)}(['\"]\s*\))",
                        rf"\1{new_path_imp}\2",
                        content
                    )
                    content = re.sub(
                        rf"(export\s+\*\s+from\s+['\"]){re.escape(old_path_imp)}(['\"])",
                        rf"\1{new_path_imp}\2",
                        content
                    )
                
                if content != original:
                    # Generate diff
                    a = original.splitlines(keepends=True)
                    b = content.splitlines(keepends=True)
                    rel = py_file.relative_to(repo_root)
                    diff = difflib.unified_diff(a, b, fromfile=f"{rel}", tofile=f"{rel}")
                    diffs.append(''.join(diff))
                    
            except Exception:
                continue
                
        return '\n'.join(diffs)
    
    @staticmethod
    def organize_imports(file_path: Path) -> Tuple[bool, str]:
        """
        Organize imports: stdlib -> third-party -> local
        Remove duplicates and sort within each group
        """
        try:
            content = file_path.read_text()
            tree = ast.parse(content)
            
            # Collect imports
            imports = {
                'stdlib': [],
                'third_party': [],
                'local': []
            }
            
            # Standard library modules (common ones)
            stdlib_modules = {
                'os', 'sys', 're', 'json', 'math', 'random', 'time', 'datetime',
                'collections', 'itertools', 'functools', 'pathlib', 'typing',
                'subprocess', 'threading', 'multiprocessing', 'asyncio', 'logging',
                'unittest', 'tempfile', 'shutil', 'glob', 'pickle', 'csv', 'sqlite3'
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name.split('.')[0]
                        import_str = f"import {alias.name}"
                        if alias.asname:
                            import_str += f" as {alias.asname}"
                            
                        if module in stdlib_modules:
                            imports['stdlib'].append(import_str)
                        elif module.startswith('.'):
                            imports['local'].append(import_str)
                        else:
                            imports['third_party'].append(import_str)
                            
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    level = node.level
                    
                    if level > 0:  # Relative import
                        import_str = f"from {'.' * level}{module} import "
                        names = [alias.name if not alias.asname else f"{alias.name} as {alias.asname}" 
                                for alias in node.names]
                        import_str += ", ".join(names)
                        imports['local'].append(import_str)
                    else:
                        base_module = module.split('.')[0]
                        import_str = f"from {module} import "
                        names = [alias.name if not alias.asname else f"{alias.name} as {alias.asname}" 
                                for alias in node.names]
                        import_str += ", ".join(names)
                        
                        if base_module in stdlib_modules:
                            imports['stdlib'].append(import_str)
                        else:
                            imports['third_party'].append(import_str)
            
            # Remove duplicates and sort
            for category in imports:
                imports[category] = sorted(list(set(imports[category])))
            
            # Build organized import block
            import_lines = []
            if imports['stdlib']:
                import_lines.extend(imports['stdlib'])
                import_lines.append('')
            if imports['third_party']:
                import_lines.extend(imports['third_party'])
                import_lines.append('')
            if imports['local']:
                import_lines.extend(imports['local'])
                import_lines.append('')
                
            # Remove trailing empty line if exists
            if import_lines and import_lines[-1] == '':
                import_lines.pop()
                
            # Find where imports end in original file
            lines = content.splitlines()
            import_end = 0
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith(('import ', 'from ')):
                    import_end = i
                    break
                    
            # Replace imports
            new_lines = import_lines + lines[import_end:]
            new_content = '\n'.join(new_lines)
            
            if new_content != content:
                file_path.write_text(new_content)
                return True, "Imports organized"
            return True, "Imports already organized"
            
        except Exception as e:
            return False, f"Failed to organize imports: {str(e)}"
    
    @staticmethod
    def extract_class(file_path: Path, class_name: str, target_file: Path,
                     update_imports: bool = True) -> Tuple[bool, str]:
        """Extract a class to another file, optionally updating imports"""
        try:
            source_content = file_path.read_text()
            tree = ast.parse(source_content)
            
            # Find the class
            class_node = None
            class_start = None
            class_end = None
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    class_node = node
                    class_start = node.lineno - 1
                    class_end = node.end_lineno
                    break
                    
            if not class_node:
                return False, f"Class {class_name} not found"
                
            # Extract class code
            lines = source_content.splitlines()
            class_code = '\n'.join(lines[class_start:class_end])
            
            # Find imports used by the class
            class_imports = set()
            for node in ast.walk(class_node):
                if isinstance(node, ast.Name):
                    # This is a simple heuristic - might need refinement
                    class_imports.add(node.id)
                    
            # Extract relevant imports from source
            import_lines = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in class_imports or alias.asname in class_imports:
                            import_lines.append(ast.unparse(node))
                elif isinstance(node, ast.ImportFrom):
                    # Check if any imported names are used
                    for alias in node.names:
                        if alias.name in class_imports or alias.asname in class_imports:
                            import_lines.append(ast.unparse(node))
                            break
                            
            # Prepare target file content
            target_lines = []
            if target_file.exists():
                target_content = target_file.read_text()
                target_lines = target_content.splitlines()
            else:
                target_lines = []
                
            # Add imports if not already present
            existing_imports = '\n'.join(target_lines[:20])  # Check first 20 lines
            new_imports = []
            for imp in import_lines:
                if imp not in existing_imports:
                    new_imports.append(imp)
                    
            # Build new target content
            if new_imports:
                target_lines = new_imports + [''] + target_lines
                
            # Add the class
            if target_lines and target_lines[-1].strip():
                target_lines.append('')
            target_lines.append('')
            target_lines.append(class_code)
            
            # Write target file
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text('\n'.join(target_lines))
            
            # Remove from source
            new_source_lines = lines[:class_start] + lines[class_end:]
            
            # Add import in source if update_imports
            if update_imports:
                # Calculate relative import
                source_parts = file_path.parent.parts
                target_parts = target_file.parent.parts
                
                # Find common prefix
                common = 0
                for i, (s, t) in enumerate(zip(source_parts, target_parts)):
                    if s == t:
                        common = i + 1
                    else:
                        break
                        
                # Build import statement
                if source_parts[:common] == target_parts[:common]:
                    # Same package
                    levels = len(source_parts) - common
                    rel_path = '.'.join(['..'] * levels + list(target_parts[common:]) + [target_file.stem])
                    import_stmt = f"from {rel_path} import {class_name}"
                else:
                    # Different package - use absolute import
                    module_path = '.'.join(target_parts + (target_file.stem,))
                    import_stmt = f"from {module_path} import {class_name}"
                    
                # Add import after other imports
                import_added = False
                for i, line in enumerate(new_source_lines):
                    if line.strip() and not line.startswith(('import ', 'from ')):
                        new_source_lines.insert(i, import_stmt)
                        import_added = True
                        break
                        
                if not import_added:
                    new_source_lines.insert(0, import_stmt)
                    
            file_path.write_text('\n'.join(new_source_lines))
            
            return True, f"Extracted class {class_name} to {target_file}"
            
        except Exception as e:
            return False, f"Failed to extract class: {str(e)}"
    
    @staticmethod
    def update_relative_imports(file_path: Path, old_location: Path, new_location: Path) -> Tuple[bool, str]:
        """Update relative imports when a file is moved"""
        try:
            content = file_path.read_text()
            tree = ast.parse(content)
            
            # Calculate the change in relative position
            old_depth = len(old_location.parent.parts)
            new_depth = len(new_location.parent.parts)
            depth_change = new_depth - old_depth
            
            modified = False
            
            class ImportTransformer(ast.NodeTransformer):
                def visit_ImportFrom(self, node):
                    if node.level > 0:  # Relative import
                        # Adjust the level based on depth change
                        new_level = node.level + depth_change
                        if new_level > 0:
                            node.level = new_level
                            nonlocal modified
                            modified = True
                    return node
                    
            transformer = ImportTransformer()
            new_tree = transformer.visit(tree)
            
            if modified:
                new_content = ast.unparse(new_tree)
                file_path.write_text(new_content)
                return True, "Updated relative imports"
            
            return True, "No relative imports to update"
            
        except Exception as e:
            return False, f"Failed to update imports: {str(e)}"
    
    @staticmethod
    def add_docstring(file_path: Path, target: str, docstring: str,
                     target_type: str = "function") -> Tuple[bool, str]:
        """Add or update docstring for a function or class"""
        try:
            content = file_path.read_text()
            tree = ast.parse(content)
            
            target_node = None
            for node in ast.walk(tree):
                if target_type == "function" and isinstance(node, ast.FunctionDef):
                    if node.name == target:
                        target_node = node
                        break
                elif target_type == "class" and isinstance(node, ast.ClassDef):
                    if node.name == target:
                        target_node = node
                        break
                        
            if not target_node:
                return False, f"{target_type.capitalize()} {target} not found"
                
            # Add docstring
            docstring_node = ast.Expr(value=ast.Constant(value=docstring))
            
            # Insert at the beginning of the body
            if target_node.body and isinstance(target_node.body[0], ast.Expr) and \
               isinstance(target_node.body[0].value, ast.Constant):
                # Replace existing docstring
                target_node.body[0] = docstring_node
            else:
                # Add new docstring
                target_node.body.insert(0, docstring_node)
                
            # Convert back to source
            new_content = ast.unparse(tree)
            file_path.write_text(new_content)
            
            return True, f"Added docstring to {target}"
            
        except Exception as e:
            return False, f"Failed to add docstring: {str(e)}"
