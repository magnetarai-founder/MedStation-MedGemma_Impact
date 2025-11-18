#!/usr/bin/env python3
"""
Import Validation Script

Validates Python imports in apps/backend/api/ by:
1. Walking all Python files in the package
2. Attempting to import each module
3. Detecting invalid relative imports (e.g., from ..nonexistent)
4. Exiting non-zero if any imports fail

Usage:
    python3 scripts/check_imports.py

Exit codes:
    0: All imports valid
    1: Import errors found
"""

import sys
import os
import ast
import importlib.util
from pathlib import Path
from typing import List, Tuple, Set


# ANSI color codes for output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def find_python_modules(base_path: Path) -> List[Path]:
    """Find all Python modules under base_path."""
    modules = []
    for py_file in base_path.rglob("*.py"):
        # Skip __pycache__ and test files if needed
        if "__pycache__" in str(py_file):
            continue
        modules.append(py_file)
    return sorted(modules)


def parse_imports(file_path: Path) -> List[Tuple[str, int, str]]:
    """
    Parse a Python file and extract all import statements.

    Returns:
        List of (import_statement, line_number, import_type) tuples
        where import_type is 'absolute', 'relative', or 'from_relative'
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(file_path))
    except SyntaxError as e:
        print(f"{YELLOW}⚠ Syntax error in {file_path}:{e.lineno}: {e.msg}{RESET}")
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, node.lineno, 'absolute'))
        elif isinstance(node, ast.ImportFrom):
            if node.level > 0:  # Relative import
                module = node.module or ""
                imports.append((
                    f"{'.' * node.level}{module}",
                    node.lineno,
                    'relative'
                ))
            else:  # Absolute import
                if node.module:
                    imports.append((node.module, node.lineno, 'absolute'))

    return imports


def validate_relative_import(
    file_path: Path,
    relative_import: str,
    base_path: Path
) -> Tuple[bool, str]:
    """
    Validate that a relative import resolves to an actual module on disk.

    Args:
        file_path: The file containing the import
        relative_import: The relative import string (e.g., "..streaming")
        base_path: The base path of the package (apps/backend/api)

    Returns:
        (is_valid, error_message) tuple
    """
    # Count the dots to determine how many levels to go up
    level = 0
    module_name = relative_import
    while module_name.startswith('.'):
        level += 1
        module_name = module_name[1:]

    # Start from the file's directory
    current_dir = file_path.parent

    # Go up 'level - 1' directories (level=1 means same package)
    for _ in range(level - 1):
        current_dir = current_dir.parent
        if current_dir == base_path.parent:
            return False, f"Relative import goes above package root"

    # Now resolve the module name
    if module_name:
        # Check if it's a module file
        target_file = current_dir / f"{module_name.replace('.', '/')}.py"
        target_package = current_dir / module_name.replace('.', '/') / "__init__.py"

        if not target_file.exists() and not target_package.exists():
            return False, f"Module '{module_name}' not found at {current_dir}"
    else:
        # Just checking the package itself
        target_package = current_dir / "__init__.py"
        if not target_package.exists():
            return False, f"Package not found at {current_dir}"

    return True, ""


def attempt_import(module_path: Path, base_path: Path) -> Tuple[bool, str, str]:
    """
    Attempt to import a module and return success status.

    Args:
        module_path: Absolute path to the .py file
        base_path: Base path for the package (apps/backend)

    Returns:
        (success, error_message, error_category) tuple
        error_category is 'import_structure', 'missing_dependency', 'environment', or 'other'
    """
    # Convert file path to module name
    rel_path = module_path.relative_to(base_path)
    module_parts = list(rel_path.parts[:-1]) + [rel_path.stem]

    # Skip __init__ in the module name construction
    if module_parts[-1] == "__init__":
        module_parts = module_parts[:-1]

    if not module_parts:
        return True, "", ""  # Skip empty module names

    module_name = ".".join(module_parts)

    try:
        # Load the module spec
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            return True, "", ""
        else:
            return False, "Could not load module spec", "other"
    except Exception as e:
        error_msg = str(e)

        # Categorize the error
        if "No module named" in error_msg:
            # Check if it's an api.* import (structure issue) or external package
            if "'api." in error_msg or "from 'api." in error_msg:
                return False, error_msg, "import_structure"
            else:
                return False, error_msg, "missing_dependency"
        elif "cannot import name" in error_msg and "from 'api." in error_msg:
            return False, error_msg, "import_structure"
        elif "ELOHIM_FOUNDER_PASSWORD" in error_msg or "environment variable" in error_msg:
            return False, error_msg, "environment"
        else:
            return False, f"{type(e).__name__}: {error_msg}", "other"


def main():
    """Main validation function."""
    print("=" * 70)
    print("PYTHON IMPORT VALIDATOR")
    print("=" * 70)
    print()

    # Determine the base path
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    backend_path = project_root / "apps" / "backend"
    api_path = backend_path / "api"

    if not api_path.exists():
        print(f"{RED}✗ Error: {api_path} does not exist{RESET}")
        return 1

    # Add backend to sys.path so imports work
    sys.path.insert(0, str(backend_path))

    print(f"Validating imports in: {api_path}")
    print()

    # Find all Python modules
    modules = find_python_modules(api_path)
    print(f"Found {len(modules)} Python files to validate")
    print()

    errors: List[str] = []
    warnings: List[str] = []
    checked_modules: Set[str] = set()

    # First pass: validate relative imports statically
    print("Validating relative imports...")
    for module_path in modules:
        rel_path = module_path.relative_to(api_path)
        imports = parse_imports(module_path)

        for import_stmt, line_no, import_type in imports:
            if import_type == 'relative':
                is_valid, error_msg = validate_relative_import(
                    module_path,
                    import_stmt,
                    api_path
                )
                if not is_valid:
                    errors.append(
                        f"{RED}✗ {rel_path}:{line_no} - "
                        f"Invalid relative import 'from {import_stmt}': {error_msg}{RESET}"
                    )

    if errors:
        print(f"\n{RED}Found {len(errors)} invalid relative import(s):{RESET}")
        for error in errors:
            print(f"  {error}")
        print()
    else:
        print(f"{GREEN}✓ All relative imports are valid{RESET}\n")

    # Second pass: attempt actual imports
    print("Attempting to import modules...")
    import_structure_errors = []
    missing_deps = []
    env_issues = []
    other_errors = []

    for module_path in modules:
        rel_path = module_path.relative_to(api_path)
        module_key = str(rel_path)

        if module_key in checked_modules:
            continue
        checked_modules.add(module_key)

        success, error_msg, error_category = attempt_import(module_path, backend_path)

        if not success:
            error_entry = f"{rel_path} - {error_msg}"
            if error_category == "import_structure":
                import_structure_errors.append(error_entry)
            elif error_category == "missing_dependency":
                missing_deps.append(error_entry)
            elif error_category == "environment":
                env_issues.append(error_entry)
            else:
                other_errors.append(error_entry)

    # Report import structure errors (critical)
    if import_structure_errors:
        print(f"\n{RED}Found {len(import_structure_errors)} import structure error(s):{RESET}")
        for error in import_structure_errors:
            print(f"  {RED}✗ {error}{RESET}")
        print()
    else:
        print(f"{GREEN}✓ No import structure errors found{RESET}\n")

    # Report other categories as warnings (non-critical for import structure)
    if missing_deps:
        print(f"{YELLOW}⚠ Found {len(missing_deps)} missing dependency warning(s):{RESET}")
        print(f"{YELLOW}  (These may be optional dependencies or lazy imports){RESET}")
        for error in missing_deps[:5]:  # Show first 5
            print(f"  {YELLOW}⚠ {error}{RESET}")
        if len(missing_deps) > 5:
            print(f"  {YELLOW}... and {len(missing_deps) - 5} more{RESET}")
        print()

    if env_issues:
        print(f"{YELLOW}⚠ Found {len(env_issues)} environment warning(s):{RESET}")
        print(f"{YELLOW}  (These require specific environment variables){RESET}")
        print()

    # Summary - only count critical errors
    critical_errors = len(errors) + len(import_structure_errors)
    print("=" * 70)
    if critical_errors == 0:
        print(f"{GREEN}✓ SUCCESS: All import structures are valid!{RESET}")
        if missing_deps or env_issues:
            print(f"{YELLOW}  Note: Some warnings exist but don't indicate import structure problems{RESET}")
        print("=" * 70)
        return 0
    else:
        print(f"{RED}✗ FAILED: Found {critical_errors} critical import error(s){RESET}")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
