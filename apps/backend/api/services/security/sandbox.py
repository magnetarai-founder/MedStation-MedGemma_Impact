"""
Python Code Sandbox using RestrictedPython

Provides secure execution of user-provided Python code with:
- Restricted builtins (no file I/O, network, imports)
- Resource limits (execution time, memory)
- Safe global namespace
- Audit logging
"""

import resource
import signal
from typing import Any

try:
    from RestrictedPython import compile_restricted, safe_globals
    from RestrictedPython.Eval import default_guarded_getitem, default_guarded_getiter
    from RestrictedPython.Guards import guarded_iter_unpack_sequence, safe_builtins
    RESTRICTED_PYTHON_AVAILABLE = True
except ImportError:
    RESTRICTED_PYTHON_AVAILABLE = False
    compile_restricted = None
    safe_globals = {}
    default_guarded_getitem = None
    default_guarded_getiter = None
    guarded_iter_unpack_sequence = None
    safe_builtins = {}


class SandboxExecutionError(Exception):
    """Raised when sandbox execution fails"""

    pass


class SandboxTimeoutError(SandboxExecutionError):
    """Raised when execution times out"""

    pass


class PythonSandbox:
    """
    Secure Python code sandbox using RestrictedPython.

    Restricts access to:
    - File system operations
    - Network operations
    - Process/system operations
    - Dangerous imports
    """

    # Allowed builtin functions (whitelist)
    SAFE_BUILTINS = {
        "abs",
        "all",
        "any",
        "bin",
        "bool",
        "chr",
        "dict",
        "divmod",
        "enumerate",
        "filter",
        "float",
        "format",
        "hex",
        "int",
        "isinstance",
        "issubclass",
        "iter",
        "len",
        "list",
        "map",
        "max",
        "min",
        "next",
        "oct",
        "ord",
        "pow",
        "range",
        "repr",
        "reversed",
        "round",
        "set",
        "slice",
        "sorted",
        "str",
        "sum",
        "tuple",
        "type",
        "zip",
        # String methods
        "str.upper",
        "str.lower",
        "str.strip",
        "str.split",
        "str.join",
    }

    # Allowed modules (whitelist)
    SAFE_MODULES = {
        "math",
        "json",
        "datetime",
        "re",
        "collections",
        "itertools",
        "functools",
        "operator",
        "string",
    }

    # Forbidden names/patterns
    FORBIDDEN_NAMES = {
        "exec",
        "eval",
        "compile",
        "__import__",
        "open",
        "file",
        "input",
        "raw_input",
        "execfile",
        "reload",
        "vars",
        "dir",
        "globals",
        "locals",
        "__builtins__",
        "__file__",
        "__name__",
        "breakpoint",
        "copyright",
        "credits",
        "exit",
        "help",
        "license",
        "quit",
    }

    def __init__(
        self,
        max_execution_time: int = 5,
        max_memory_mb: int = 100,
        allowed_modules: set[str] | None = None,
    ):
        """
        Initialize sandbox.

        Args:
            max_execution_time: Maximum execution time in seconds
            max_memory_mb: Maximum memory usage in MB
            allowed_modules: Additional allowed modules (beyond SAFE_MODULES)
        """
        if not RESTRICTED_PYTHON_AVAILABLE:
            raise ImportError(
                "RestrictedPython is required for sandbox functionality. "
                "Install with: pip install RestrictedPython"
            )
        self.max_execution_time = max_execution_time
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.allowed_modules = self.SAFE_MODULES.copy()
        if allowed_modules:
            self.allowed_modules.update(allowed_modules)

    def _create_safe_import(self):
        """Create a safe __import__ function that only allows whitelisted modules"""

        def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name not in self.allowed_modules:
                raise ImportError(
                    f"Import of '{name}' not allowed. Allowed modules: {', '.join(sorted(self.allowed_modules))}"
                )
            return __import__(name, globals, locals, fromlist, level)

        return safe_import

    def _create_safe_globals(self) -> dict[str, Any]:
        """Create safe global namespace for execution"""
        # Start with RestrictedPython's safe globals
        safe_ns = safe_globals.copy()

        # Add safe builtins
        safe_ns["_getiter_"] = default_guarded_getiter
        safe_ns["_getitem_"] = default_guarded_getitem
        safe_ns["_iter_unpack_sequence_"] = guarded_iter_unpack_sequence

        # Add _getattr_ for attribute access (needed for dict operations, etc.)
        from RestrictedPython.Guards import full_write_guard, safer_getattr

        safe_ns["_getattr_"] = safer_getattr
        safe_ns["_write_"] = full_write_guard

        # Add only whitelisted builtins
        builtins = {}
        for name in self.SAFE_BUILTINS:
            if "." not in name:  # Not a method
                try:
                    builtins[name] = safe_builtins[name]
                except KeyError:
                    # Fallback to real builtin if not in safe_builtins
                    import builtins as real_builtins

                    if hasattr(real_builtins, name):
                        builtins[name] = getattr(real_builtins, name)

        # Add safe __import__
        builtins["__import__"] = self._create_safe_import()

        safe_ns["__builtins__"] = builtins

        # Add safe modules (pre-imported)
        for module_name in self.allowed_modules:
            try:
                module = __import__(module_name)
                safe_ns[module_name] = module
            except ImportError:
                pass  # Module not available

        return safe_ns

    def _set_resource_limits(self):
        """Set resource limits for execution"""
        try:
            # Set CPU time limit
            signal.signal(signal.SIGALRM, self._timeout_handler)
            signal.alarm(self.max_execution_time)

            # Set memory limit (soft limit only to avoid crashes)
            resource.setrlimit(resource.RLIMIT_AS, (self.max_memory_bytes, resource.RLIM_INFINITY))
        except (ValueError, OSError, AttributeError) as e:
            # Resource limits may not be available on all platforms
            import logging

            logging.warning(f"Could not set resource limits: {e}")

    def _timeout_handler(self, signum, frame):
        """Handle execution timeout"""
        raise SandboxTimeoutError(f"Execution exceeded {self.max_execution_time} second limit")

    def _validate_code(self, code: str):
        """Validate code before execution"""
        # Check for forbidden patterns using word boundaries
        # This prevents false positives like "execute" matching "exec"
        import re

        for forbidden in self.FORBIDDEN_NAMES:
            # Use word boundaries to match only complete identifiers
            pattern = r"\b" + re.escape(forbidden) + r"\b"
            if re.search(pattern, code, re.IGNORECASE):
                raise SandboxExecutionError(f"Forbidden name '{forbidden}' found in code")

        # Check for import statements (only allowed modules)
        import ast

        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name not in self.allowed_modules:
                            raise SandboxExecutionError(
                                f"Import of '{alias.name}' not allowed. "
                                f"Allowed modules: {', '.join(sorted(self.allowed_modules))}"
                            )
                elif isinstance(node, ast.ImportFrom):
                    if node.module not in self.allowed_modules:
                        raise SandboxExecutionError(f"Import from '{node.module}' not allowed")
        except SyntaxError as e:
            raise SandboxExecutionError(f"Syntax error in code: {e}")

    def execute(self, code: str, function_name: str = "execute", **kwargs) -> Any:
        """
        Execute Python code in sandbox.

        Args:
            code: Python code to execute
            function_name: Name of function to call (default: 'execute')
            **kwargs: Arguments to pass to the function

        Returns:
            Function return value

        Raises:
            SandboxExecutionError: If execution fails
            SandboxTimeoutError: If execution times out
        """
        # Validate code first
        self._validate_code(code)

        # Compile with RestrictedPython
        try:
            byte_code = compile_restricted(code, filename="<sandbox>", mode="exec")

            # RestrictedPython 6.0+ returns code object directly
            # (older versions returned CompileResult with .code and .errors)
            if not isinstance(byte_code, type(lambda: None).__code__.__class__):
                # Handle older API if needed
                if hasattr(byte_code, "errors") and byte_code.errors:
                    raise SandboxExecutionError(
                        f"Compilation errors: {'; '.join(byte_code.errors)}"
                    )
                if hasattr(byte_code, "code"):
                    byte_code = byte_code.code
        except SyntaxError as e:
            raise SandboxExecutionError(f"Syntax error: {e}")

        # Create safe namespace
        safe_ns = self._create_safe_globals()

        # Set resource limits
        self._set_resource_limits()

        try:
            # Execute code with SEPARATE namespaces to prevent namespace pollution
            # This prevents malicious code from modifying the global namespace
            local_ns = {}
            exec(byte_code, safe_ns, local_ns)  # ← FIX: Separate local namespace

            # Find and call the function in LOCAL namespace only
            if function_name not in local_ns:
                raise SandboxExecutionError(f"Function '{function_name}' not found in code")

            func = local_ns[function_name]
            if not callable(func):
                raise SandboxExecutionError(f"'{function_name}' is not callable")

            # Additional security: verify function doesn't access dangerous globals
            if hasattr(func, '__globals__'):
                # Check if function tries to access builtins
                func_globals = func.__globals__
                if '__builtins__' in func_globals:
                    # Ensure builtins are restricted
                    if func_globals['__builtins__'] != safe_ns.get('__builtins__'):
                        raise SandboxExecutionError("Function has unrestricted builtins access")

            # Call function with arguments
            result = func(**kwargs)

            return result

        except SandboxTimeoutError:
            raise  # Re-raise timeout
        except SandboxExecutionError:
            raise  # Re-raise sandbox errors
        except Exception as e:
            raise SandboxExecutionError(f"Execution error: {type(e).__name__}: {e}")
        finally:
            # Cancel alarm
            try:
                signal.alarm(0)
            except (ValueError, AttributeError):
                pass  # signal.alarm not available on all platforms

    def validate_only(self, code: str) -> dict[str, Any]:
        """
        Validate code without executing.

        Args:
            code: Python code to validate

        Returns:
            Dict with validation results
        """
        try:
            self._validate_code(code)

            # Try compiling
            compile_result = compile_restricted(code, "<sandbox>", "exec")

            # Check for compilation errors (older RestrictedPython API)
            if hasattr(compile_result, "errors") and compile_result.errors:
                return {"valid": False, "errors": compile_result.errors}

            return {"valid": True, "errors": []}

        except SandboxExecutionError as e:
            return {"valid": False, "errors": [str(e)]}


# Global sandbox instance
_default_sandbox = PythonSandbox()


def execute_sandboxed(code: str, function_name: str = "execute", **kwargs) -> Any:
    """
    Execute code in sandbox (convenience function).

    Args:
        code: Python code
        function_name: Function to call
        **kwargs: Function arguments

    Returns:
        Function result
    """
    return _default_sandbox.execute(code, function_name, **kwargs)


def validate_code(code: str) -> dict[str, Any]:
    """
    Validate code (convenience function).

    Args:
        code: Python code to validate

    Returns:
        Validation results
    """
    return _default_sandbox.validate_only(code)
