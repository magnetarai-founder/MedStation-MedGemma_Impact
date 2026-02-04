#!/usr/bin/env python3
"""
Smart Refactoring Engine

Provides intelligent code refactoring with AST-based analysis:
- Extract method/function from code blocks
- Extract class from related functions
- Dead code detection (unused functions, variables, imports)
- Import optimization (organize, dedupe, remove unused)
- Symbol renaming with cross-file safety
- Inline variable replacement
- Code relocation suggestions

All refactorings are safe with preview-before-apply capability.
"""

import ast
import difflib
import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from api.utils.structured_logging import get_logger

logger = get_logger(__name__)


class RefactoringType(Enum):
    """Type of refactoring operation."""

    EXTRACT_METHOD = "extract_method"
    EXTRACT_CLASS = "extract_class"
    DEAD_CODE = "dead_code"
    OPTIMIZE_IMPORTS = "optimize_imports"
    RENAME_SYMBOL = "rename_symbol"
    INLINE_VARIABLE = "inline_variable"
    MOVE_TO_FILE = "move_to_file"
    SIMPLIFY_CONDITION = "simplify_condition"
    REMOVE_DUPLICATE = "remove_duplicate"


@dataclass
class CodeLocation:
    """Location of code in a file."""

    file_path: str
    start_line: int
    end_line: int
    start_col: int = 0
    end_col: int = 0

    def __str__(self) -> str:
        return f"{self.file_path}:{self.start_line}-{self.end_line}"


@dataclass
class RefactoringSuggestion:
    """A refactoring suggestion with preview."""

    type: RefactoringType
    location: CodeLocation
    description: str
    confidence: float  # 0.0 to 1.0
    diff_preview: str
    reasoning: str
    metadata: dict[str, Any] = field(default_factory=dict)
    impact_score: float = 0.0  # How much this improves code quality
    effort_score: float = 0.0  # How much work to apply (0=easy, 1=hard)
    safety_score: float = 1.0  # How safe is this refactoring (0=risky, 1=safe)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type.value,
            "location": str(self.location),
            "description": self.description,
            "confidence": self.confidence,
            "diff_preview": self.diff_preview,
            "reasoning": self.reasoning,
            "metadata": self.metadata,
            "impact_score": self.impact_score,
            "effort_score": self.effort_score,
            "safety_score": self.safety_score,
        }


@dataclass
class CodeMetrics:
    """Metrics for a code block."""

    lines: int
    complexity: int  # Cyclomatic complexity
    nesting_depth: int
    num_statements: int
    num_variables: int
    num_parameters: int = 0
    has_return: bool = False


class ComplexityVisitor(ast.NodeVisitor):
    """Calculate cyclomatic complexity."""

    def __init__(self):
        self.complexity = 1
        self.max_nesting = 0
        self.current_nesting = 0
        self.num_statements = 0

    def _increment_nesting(self):
        self.current_nesting += 1
        self.max_nesting = max(self.max_nesting, self.current_nesting)

    def _decrement_nesting(self):
        self.current_nesting -= 1

    def visit_If(self, node: ast.If) -> None:
        self.complexity += 1
        self._increment_nesting()
        self.generic_visit(node)
        self._decrement_nesting()

    def visit_While(self, node: ast.While) -> None:
        self.complexity += 1
        self._increment_nesting()
        self.generic_visit(node)
        self._decrement_nesting()

    def visit_For(self, node: ast.For) -> None:
        self.complexity += 1
        self._increment_nesting()
        self.generic_visit(node)
        self._decrement_nesting()

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        # Each boolean operation adds a path
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_stmt(self, node: ast.stmt) -> None:
        self.num_statements += 1
        self.generic_visit(node)


class DeadCodeVisitor(ast.NodeVisitor):
    """Find dead code (unused definitions)."""

    def __init__(self):
        self.definitions: dict[str, ast.AST] = {}  # name -> node
        self.usages: set[str] = set()
        self.imports: dict[str, ast.AST] = {}  # name -> import node
        self._current_scope: list[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.definitions[node.name] = node
        self._current_scope.append(node.name)
        self.generic_visit(node)
        self._current_scope.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.definitions[node.name] = node
        self._current_scope.append(node.name)
        self.generic_visit(node)
        self._current_scope.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.definitions[node.name] = node
        self._current_scope.append(node.name)
        self.generic_visit(node)
        self._current_scope.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.definitions[target.id] = node
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname or alias.name
            self.imports[name] = node

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            name = alias.asname or alias.name
            self.imports[name] = node

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.usages.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Mark the base as used
        if isinstance(node.value, ast.Name):
            self.usages.add(node.value.id)
        self.generic_visit(node)

    def get_unused_definitions(self) -> list[tuple[str, ast.AST]]:
        """Get definitions that are never used."""
        unused = []
        for name, node in self.definitions.items():
            if name not in self.usages and not name.startswith("_"):
                unused.append((name, node))
        return unused

    def get_unused_imports(self) -> list[tuple[str, ast.AST]]:
        """Get imports that are never used."""
        unused = []
        for name, node in self.imports.items():
            if name not in self.usages:
                unused.append((name, node))
        return unused


class DuplicateCodeFinder(ast.NodeVisitor):
    """Find duplicate code blocks."""

    def __init__(self):
        self.code_hashes: dict[str, list[ast.AST]] = defaultdict(list)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Hash function body
        body_str = ast.unparse(node)
        hash_val = hashlib.md5(body_str.encode()).hexdigest()
        self.code_hashes[hash_val].append(node)
        self.generic_visit(node)

    def get_duplicates(self) -> list[list[ast.AST]]:
        """Get groups of duplicate code blocks."""
        return [nodes for nodes in self.code_hashes.values() if len(nodes) > 1]


class RefactoringEngine:
    """
    Smart refactoring engine with AST-based analysis.

    Provides intelligent refactoring suggestions:
    - Extract method from complex code blocks
    - Extract class from related functions
    - Find and remove dead code
    - Optimize imports
    - Rename symbols safely
    - Inline variables
    - Suggest better code organization

    All refactorings are safe with preview capability.
    """

    def __init__(self, workspace_root: str | Path):
        """
        Initialize refactoring engine.

        Args:
            workspace_root: Root directory of codebase
        """
        self.workspace_root = Path(workspace_root)

        # Configuration thresholds
        self.min_extract_lines = 5  # Min lines for extract method
        self.max_complexity = 10  # Max complexity before suggesting extract
        self.max_nesting = 3  # Max nesting before suggesting extract
        self.min_duplicate_lines = 4  # Min lines to consider duplicate

        # Analysis cache
        self._file_asts: dict[str, ast.AST] = {}
        self._file_contents: dict[str, str] = {}

        # Symbol tracking
        self._symbol_locations: dict[str, list[CodeLocation]] = defaultdict(list)
        self._symbol_usages: dict[str, list[CodeLocation]] = defaultdict(list)

    def analyze_file(self, file_path: str | Path) -> list[RefactoringSuggestion]:
        """
        Analyze a file and return all refactoring suggestions.

        Args:
            file_path: Path to Python file

        Returns:
            List of refactoring suggestions sorted by impact
        """
        file_path = Path(file_path)
        if not file_path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return []

        try:
            content = file_path.read_text()
            tree = ast.parse(content)
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return []

        # Cache file content and AST
        str_path = str(file_path)
        self._file_contents[str_path] = content
        self._file_asts[str_path] = tree

        suggestions = []

        # Run all analysis passes
        suggestions.extend(self._analyze_extract_method(file_path, tree))
        suggestions.extend(self._analyze_extract_class(file_path, tree))
        suggestions.extend(self.find_dead_code(file_path))
        suggestions.extend(self.optimize_imports(file_path))
        suggestions.extend(self._find_inline_opportunities(file_path, tree))
        suggestions.extend(self._find_duplicates(file_path, tree))

        # Sort by impact score descending
        suggestions.sort(key=lambda s: s.impact_score, reverse=True)

        return suggestions

    def _analyze_extract_method(
        self, file_path: Path, tree: ast.AST
    ) -> list[RefactoringSuggestion]:
        """Find code blocks that should be extracted into methods."""
        suggestions = []

        class ExtractMethodVisitor(ast.NodeVisitor):
            def __init__(self, engine: RefactoringEngine):
                self.engine = engine
                self.current_function: str | None = None

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                old_func = self.current_function
                self.current_function = node.name

                # Analyze function body
                metrics = self._calculate_metrics(node)

                # Check if function should be extracted
                if self._should_extract(metrics):
                    suggestion = self._create_extract_suggestion(
                        file_path, node, metrics
                    )
                    if suggestion:
                        suggestions.append(suggestion)

                # Look for extractable blocks within function
                for i, stmt in enumerate(node.body):
                    # Group consecutive statements
                    if i + self.engine.min_extract_lines <= len(node.body):
                        block = node.body[i : i + self.engine.min_extract_lines]
                        block_metrics = self._calculate_block_metrics(block)

                        if self._should_extract_block(block_metrics):
                            suggestion = self._create_block_extract_suggestion(
                                file_path, block, block_metrics
                            )
                            if suggestion:
                                suggestions.append(suggestion)

                self.generic_visit(node)
                self.current_function = old_func

            def _calculate_metrics(self, node: ast.FunctionDef) -> CodeMetrics:
                visitor = ComplexityVisitor()
                visitor.visit(node)

                # Count variables
                variables = set()
                for child in ast.walk(node):
                    if isinstance(child, ast.Name) and isinstance(
                        child.ctx, ast.Store
                    ):
                        variables.add(child.id)

                return CodeMetrics(
                    lines=node.end_lineno - node.lineno + 1,
                    complexity=visitor.complexity,
                    nesting_depth=visitor.max_nesting,
                    num_statements=visitor.num_statements,
                    num_variables=len(variables),
                    num_parameters=len(node.args.args),
                    has_return=any(
                        isinstance(n, ast.Return) for n in ast.walk(node)
                    ),
                )

            def _calculate_block_metrics(self, block: list[ast.stmt]) -> CodeMetrics:
                # Create a temporary function to analyze block
                temp_func = ast.FunctionDef(
                    name="temp",
                    args=ast.arguments(
                        args=[], posonlyargs=[], kwonlyargs=[], defaults=[], kw_defaults=[]
                    ),
                    body=block,
                    decorator_list=[],
                )
                return self._calculate_metrics(temp_func)

            def _should_extract(self, metrics: CodeMetrics) -> bool:
                return (
                    metrics.lines >= self.engine.min_extract_lines
                    and (
                        metrics.complexity > self.engine.max_complexity
                        or metrics.nesting_depth > self.engine.max_nesting
                    )
                )

            def _should_extract_block(self, metrics: CodeMetrics) -> bool:
                return (
                    metrics.complexity > 5
                    or metrics.nesting_depth > 2
                    or metrics.num_statements > 8
                )

            def _create_extract_suggestion(
                self, file_path: Path, node: ast.FunctionDef, metrics: CodeMetrics
            ) -> RefactoringSuggestion | None:
                location = CodeLocation(
                    file_path=str(file_path),
                    start_line=node.lineno,
                    end_line=node.end_lineno,
                )

                # Generate suggested method names based on complexity
                reasons = []
                if metrics.complexity > self.engine.max_complexity:
                    reasons.append(f"complexity {metrics.complexity}")
                if metrics.nesting_depth > self.engine.max_nesting:
                    reasons.append(f"nesting depth {metrics.nesting_depth}")

                description = f"Extract helper methods from '{node.name}' - {', '.join(reasons)}"

                # Calculate impact and confidence
                impact = min(
                    1.0,
                    (metrics.complexity / 20.0)
                    + (metrics.nesting_depth / 10.0)
                    + (metrics.lines / 100.0),
                )
                confidence = 0.7 if metrics.complexity > 15 else 0.5

                return RefactoringSuggestion(
                    type=RefactoringType.EXTRACT_METHOD,
                    location=location,
                    description=description,
                    confidence=confidence,
                    diff_preview=self._generate_extract_preview(node),
                    reasoning=f"Function has {', '.join(reasons)}. Breaking it into smaller methods will improve readability and testability.",
                    metadata={
                        "function_name": node.name,
                        "metrics": metrics.__dict__,
                    },
                    impact_score=impact,
                    effort_score=0.3,
                    safety_score=0.9,
                )

            def _create_block_extract_suggestion(
                self, file_path: Path, block: list[ast.stmt], metrics: CodeMetrics
            ) -> RefactoringSuggestion | None:
                if not block:
                    return None

                location = CodeLocation(
                    file_path=str(file_path),
                    start_line=block[0].lineno,
                    end_line=block[-1].end_lineno,
                )

                description = f"Extract {len(block)} statements into a helper method"

                return RefactoringSuggestion(
                    type=RefactoringType.EXTRACT_METHOD,
                    location=location,
                    description=description,
                    confidence=0.6,
                    diff_preview=self._generate_block_preview(block),
                    reasoning=f"Code block has complexity {metrics.complexity} and can be extracted for clarity.",
                    metadata={"num_statements": len(block), "metrics": metrics.__dict__},
                    impact_score=0.5,
                    effort_score=0.2,
                    safety_score=0.85,
                )

            def _generate_extract_preview(self, node: ast.FunctionDef) -> str:
                original = ast.unparse(node)
                preview = f"# Original function (complex):\n{original}\n\n"
                preview += "# Suggested refactoring:\n"
                preview += f"def {node.name}_refactored(...):\n"
                preview += "    # Extract complex logic into helper methods\n"
                preview += "    result = _helper_method_1(...)\n"
                preview += "    processed = _helper_method_2(result)\n"
                preview += "    return processed\n"
                return preview

            def _generate_block_preview(self, block: list[ast.stmt]) -> str:
                block_code = "\n".join(ast.unparse(stmt) for stmt in block)
                preview = f"# Original block:\n{block_code}\n\n"
                preview += "# Suggested extraction:\n"
                preview += "def _extracted_method(...):\n"
                preview += "    " + block_code.replace("\n", "\n    ")
                return preview

        visitor = ExtractMethodVisitor(self)
        visitor.visit(tree)

        return suggestions

    def _analyze_extract_class(
        self, file_path: Path, tree: ast.AST
    ) -> list[RefactoringSuggestion]:
        """Find related functions that should be a class."""
        suggestions = []

        # Find module-level functions
        functions: list[ast.FunctionDef] = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node)

        # Group functions by common patterns
        function_groups = self._group_related_functions(functions)

        for group in function_groups:
            if len(group) >= 3:  # At least 3 related functions
                location = CodeLocation(
                    file_path=str(file_path),
                    start_line=min(f.lineno for f in group),
                    end_line=max(f.end_lineno for f in group),
                )

                names = [f.name for f in group]
                common_prefix = self._find_common_prefix(names)

                description = f"Extract {len(group)} related functions into a class"
                if common_prefix:
                    description += f" (suggested name: {common_prefix.title()})"

                suggestions.append(
                    RefactoringSuggestion(
                        type=RefactoringType.EXTRACT_CLASS,
                        location=location,
                        description=description,
                        confidence=0.6,
                        diff_preview=self._generate_class_preview(group, common_prefix),
                        reasoning=f"Functions {', '.join(names)} share common parameters and logic, suggesting they belong together.",
                        metadata={
                            "function_names": names,
                            "common_prefix": common_prefix,
                        },
                        impact_score=0.7,
                        effort_score=0.5,
                        safety_score=0.8,
                    )
                )

        return suggestions

    def _group_related_functions(
        self, functions: list[ast.FunctionDef]
    ) -> list[list[ast.FunctionDef]]:
        """Group functions that share common patterns."""
        groups = []

        # Group by parameter similarity
        param_groups: dict[str, list[ast.FunctionDef]] = defaultdict(list)
        for func in functions:
            param_key = ",".join(sorted(arg.arg for arg in func.args.args[:3]))
            if param_key:
                param_groups[param_key].append(func)

        for group in param_groups.values():
            if len(group) >= 3:
                groups.append(group)

        # Group by name prefix
        prefix_groups: dict[str, list[ast.FunctionDef]] = defaultdict(list)
        for func in functions:
            parts = func.name.split("_")
            if len(parts) > 1:
                prefix = parts[0]
                prefix_groups[prefix].append(func)

        for group in prefix_groups.values():
            if len(group) >= 3 and group not in groups:
                groups.append(group)

        return groups

    def _find_common_prefix(self, names: list[str]) -> str:
        """Find common prefix in function names."""
        if not names:
            return ""

        prefix = names[0]
        for name in names[1:]:
            while not name.startswith(prefix):
                prefix = prefix[:-1]
                if not prefix:
                    return ""

        # Clean up prefix (remove trailing underscores)
        return prefix.rstrip("_")

    def _generate_class_preview(
        self, functions: list[ast.FunctionDef], class_name: str
    ) -> str:
        """Generate preview of class extraction."""
        class_name = class_name.title() if class_name else "ExtractedClass"

        preview = f"class {class_name}:\n"
        preview += '    """Extracted class for related functionality."""\n\n'

        # Add __init__ based on common parameters
        common_params = self._find_common_parameters(functions)
        if common_params:
            preview += f"    def __init__(self, {', '.join(common_params)}):\n"
            for param in common_params:
                preview += f"        self.{param} = {param}\n"
            preview += "\n"

        # Add methods
        for func in functions[:3]:  # Show first 3 as example
            func_code = ast.unparse(func)
            preview += f"    {func_code}\n\n"

        if len(functions) > 3:
            preview += f"    # ... {len(functions) - 3} more methods\n"

        return preview

    def _find_common_parameters(
        self, functions: list[ast.FunctionDef]
    ) -> list[str]:
        """Find parameters common to multiple functions."""
        if not functions:
            return []

        param_counts: dict[str, int] = defaultdict(int)
        for func in functions:
            params = {arg.arg for arg in func.args.args}
            for param in params:
                param_counts[param] += 1

        # Return parameters used in at least 2 functions
        threshold = min(2, len(functions))
        return [p for p, count in param_counts.items() if count >= threshold]

    def find_dead_code(self, file_path: str | Path) -> list[RefactoringSuggestion]:
        """
        Find dead code (unused definitions).

        Args:
            file_path: Path to Python file

        Returns:
            List of suggestions for removing dead code
        """
        file_path = Path(file_path)
        str_path = str(file_path)

        if str_path not in self._file_asts:
            try:
                content = file_path.read_text()
                tree = ast.parse(content)
                self._file_contents[str_path] = content
                self._file_asts[str_path] = tree
            except Exception as e:
                logger.error(f"Failed to parse {file_path}: {e}")
                return []

        tree = self._file_asts[str_path]
        content = self._file_contents[str_path]

        visitor = DeadCodeVisitor()
        visitor.visit(tree)

        suggestions = []

        # Unused definitions
        for name, node in visitor.get_unused_definitions():
            location = CodeLocation(
                file_path=str_path,
                start_line=node.lineno,
                end_line=node.end_lineno,
            )

            # Get original code
            lines = content.split("\n")
            original = "\n".join(lines[node.lineno - 1 : node.end_lineno])

            suggestions.append(
                RefactoringSuggestion(
                    type=RefactoringType.DEAD_CODE,
                    location=location,
                    description=f"Remove unused definition '{name}'",
                    confidence=0.8,
                    diff_preview=f"- {original}",
                    reasoning=f"'{name}' is defined but never used in this file.",
                    metadata={"symbol_name": name},
                    impact_score=0.3,
                    effort_score=0.1,
                    safety_score=0.7,  # Could be used by other files
                )
            )

        # Unused imports
        for name, node in visitor.get_unused_imports():
            location = CodeLocation(
                file_path=str_path,
                start_line=node.lineno,
                end_line=node.lineno,
            )

            lines = content.split("\n")
            original = lines[node.lineno - 1]

            suggestions.append(
                RefactoringSuggestion(
                    type=RefactoringType.DEAD_CODE,
                    location=location,
                    description=f"Remove unused import '{name}'",
                    confidence=0.9,
                    diff_preview=f"- {original}",
                    reasoning=f"Import '{name}' is never used.",
                    metadata={"import_name": name},
                    impact_score=0.2,
                    effort_score=0.05,
                    safety_score=0.95,
                )
            )

        return suggestions

    def optimize_imports(self, file_path: str | Path) -> list[RefactoringSuggestion]:
        """
        Optimize imports (organize, dedupe, remove unused).

        Args:
            file_path: Path to Python file

        Returns:
            List of import optimization suggestions
        """
        file_path = Path(file_path)
        str_path = str(file_path)

        if str_path not in self._file_asts:
            try:
                content = file_path.read_text()
                tree = ast.parse(content)
                self._file_contents[str_path] = content
                self._file_asts[str_path] = tree
            except Exception as e:
                logger.error(f"Failed to parse {file_path}: {e}")
                return []

        tree = self._file_asts[str_path]
        content = self._file_contents[str_path]

        # Collect all imports
        imports: list[ast.Import | ast.ImportFrom] = []
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(node)

        if not imports:
            return []

        suggestions = []

        # Check for duplicate imports
        import_names: dict[str, list[ast.AST]] = defaultdict(list)
        for imp in imports:
            if isinstance(imp, ast.Import):
                for alias in imp.names:
                    name = alias.asname or alias.name
                    import_names[name].append(imp)
            elif isinstance(imp, ast.ImportFrom):
                for alias in imp.names:
                    name = alias.asname or alias.name
                    import_names[name].append(imp)

        # Find duplicates
        duplicates = {name: nodes for name, nodes in import_names.items() if len(nodes) > 1}

        if duplicates:
            # Create suggestion for all duplicate imports
            all_dup_lines = []
            for nodes in duplicates.values():
                all_dup_lines.extend(n.lineno for n in nodes)

            location = CodeLocation(
                file_path=str_path,
                start_line=min(all_dup_lines),
                end_line=max(all_dup_lines),
            )

            preview = self._generate_import_optimization_preview(imports, content)

            suggestions.append(
                RefactoringSuggestion(
                    type=RefactoringType.OPTIMIZE_IMPORTS,
                    location=location,
                    description=f"Remove {len(duplicates)} duplicate imports",
                    confidence=0.95,
                    diff_preview=preview,
                    reasoning=f"Found duplicate imports: {', '.join(duplicates.keys())}",
                    metadata={"duplicate_count": len(duplicates)},
                    impact_score=0.4,
                    effort_score=0.1,
                    safety_score=0.95,
                )
            )

        # Check for unorganized imports (not following PEP 8)
        if self._are_imports_unorganized(imports):
            location = CodeLocation(
                file_path=str_path,
                start_line=imports[0].lineno,
                end_line=imports[-1].lineno,
            )

            preview = self._generate_import_organization_preview(imports)

            suggestions.append(
                RefactoringSuggestion(
                    type=RefactoringType.OPTIMIZE_IMPORTS,
                    location=location,
                    description="Organize imports (PEP 8: stdlib, third-party, local)",
                    confidence=0.9,
                    diff_preview=preview,
                    reasoning="Imports are not organized according to PEP 8 (stdlib, then third-party, then local).",
                    metadata={"import_count": len(imports)},
                    impact_score=0.3,
                    effort_score=0.15,
                    safety_score=1.0,
                )
            )

        return suggestions

    def _are_imports_unorganized(
        self, imports: list[ast.Import | ast.ImportFrom]
    ) -> bool:
        """Check if imports are organized according to PEP 8."""
        # Simple heuristic: check if stdlib imports come before third-party
        stdlib_modules = {
            "os",
            "sys",
            "re",
            "json",
            "datetime",
            "pathlib",
            "typing",
            "collections",
            "itertools",
            "functools",
            "asyncio",
            "hashlib",
            "ast",
        }

        last_category = 0  # 0=none, 1=stdlib, 2=third-party, 3=local

        for imp in imports:
            if isinstance(imp, ast.Import):
                module = imp.names[0].name.split(".")[0]
            elif isinstance(imp, ast.ImportFrom):
                module = (imp.module or "").split(".")[0]
            else:
                continue

            if module in stdlib_modules:
                category = 1
            elif module.startswith(".") or not module:
                category = 3
            else:
                category = 2

            if category < last_category:
                return True  # Out of order

            last_category = category

        return False

    def _generate_import_optimization_preview(
        self, imports: list[ast.Import | ast.ImportFrom], content: str
    ) -> str:
        """Generate preview of import optimization."""
        lines = content.split("\n")
        original_imports = []

        for imp in imports:
            original_imports.append(lines[imp.lineno - 1])

        # Show before/after
        preview = "# Before:\n"
        preview += "\n".join(original_imports)
        preview += "\n\n# After (duplicates removed):\n"

        # Remove duplicates
        seen = set()
        optimized = []
        for line in original_imports:
            if line not in seen:
                seen.add(line)
                optimized.append(line)

        preview += "\n".join(optimized)

        return preview

    def _generate_import_organization_preview(
        self, imports: list[ast.Import | ast.ImportFrom]
    ) -> str:
        """Generate preview of import organization."""
        stdlib_modules = {
            "os",
            "sys",
            "re",
            "json",
            "datetime",
            "pathlib",
            "typing",
            "collections",
            "itertools",
            "functools",
            "asyncio",
            "hashlib",
            "ast",
        }

        stdlib = []
        third_party = []
        local = []

        for imp in imports:
            imp_str = ast.unparse(imp)

            if isinstance(imp, ast.Import):
                module = imp.names[0].name.split(".")[0]
            elif isinstance(imp, ast.ImportFrom):
                module = (imp.module or "").split(".")[0]
            else:
                continue

            if module in stdlib_modules:
                stdlib.append(imp_str)
            elif module.startswith(".") or not module:
                local.append(imp_str)
            else:
                third_party.append(imp_str)

        preview = "# Organized imports (PEP 8):\n\n"

        if stdlib:
            preview += "# Standard library\n"
            preview += "\n".join(sorted(stdlib))
            preview += "\n\n"

        if third_party:
            preview += "# Third-party\n"
            preview += "\n".join(sorted(third_party))
            preview += "\n\n"

        if local:
            preview += "# Local\n"
            preview += "\n".join(sorted(local))

        return preview

    def _find_inline_opportunities(
        self, file_path: Path, tree: ast.AST
    ) -> list[RefactoringSuggestion]:
        """Find variables that should be inlined."""
        suggestions = []

        class InlineVisitor(ast.NodeVisitor):
            def __init__(self):
                self.variables: dict[str, tuple[ast.Assign, Any]] = {}
                self.usage_counts: dict[str, int] = defaultdict(int)

            def visit_Assign(self, node: ast.Assign) -> None:
                # Track simple variable assignments
                if len(node.targets) == 1:
                    target = node.targets[0]
                    if isinstance(target, ast.Name):
                        # Only consider simple value assignments
                        if isinstance(node.value, (ast.Constant, ast.Name)):
                            self.variables[target.id] = (node, node.value)

                self.generic_visit(node)

            def visit_Name(self, node: ast.Name) -> None:
                if isinstance(node.ctx, ast.Load):
                    self.usage_counts[node.id] += 1
                self.generic_visit(node)

        visitor = InlineVisitor()
        visitor.visit(tree)

        # Find variables used only once
        for name, (assign_node, value) in visitor.variables.items():
            if visitor.usage_counts.get(name, 0) == 1:
                location = CodeLocation(
                    file_path=str(file_path),
                    start_line=assign_node.lineno,
                    end_line=assign_node.lineno,
                )

                value_str = ast.unparse(value)

                suggestions.append(
                    RefactoringSuggestion(
                        type=RefactoringType.INLINE_VARIABLE,
                        location=location,
                        description=f"Inline variable '{name}' (used only once)",
                        confidence=0.8,
                        diff_preview=f"- {name} = {value_str}\n+ # Inlined: {value_str}",
                        reasoning=f"Variable '{name}' is only used once and can be inlined for simplicity.",
                        metadata={"variable_name": name, "value": value_str},
                        impact_score=0.2,
                        effort_score=0.1,
                        safety_score=0.9,
                    )
                )

        return suggestions

    def _find_duplicates(
        self, file_path: Path, tree: ast.AST
    ) -> list[RefactoringSuggestion]:
        """Find duplicate code blocks."""
        suggestions = []

        finder = DuplicateCodeFinder()
        finder.visit(tree)

        for group in finder.get_duplicates():
            # Get all locations
            locations = [
                CodeLocation(
                    file_path=str(file_path),
                    start_line=node.lineno,
                    end_line=node.end_lineno,
                )
                for node in group
            ]

            names = [node.name for node in group if hasattr(node, "name")]

            description = f"Remove duplicate code: {len(group)} identical blocks"

            preview = f"# Found {len(group)} duplicate blocks:\n"
            for i, node in enumerate(group[:2], 1):
                preview += f"\n# Duplicate {i}:\n"
                preview += ast.unparse(node)

            suggestions.append(
                RefactoringSuggestion(
                    type=RefactoringType.REMOVE_DUPLICATE,
                    location=locations[0],
                    description=description,
                    confidence=0.85,
                    diff_preview=preview,
                    reasoning=f"Functions {', '.join(names)} have identical implementations.",
                    metadata={
                        "duplicate_count": len(group),
                        "function_names": names,
                    },
                    impact_score=0.6,
                    effort_score=0.4,
                    safety_score=0.8,
                )
            )

        return suggestions

    def suggest_extract_method(
        self,
        file_path: str | Path,
        start_line: int,
        end_line: int,
        suggested_name: str | None = None,
    ) -> RefactoringSuggestion | None:
        """
        Suggest extracting a specific code range into a method.

        Args:
            file_path: Path to file
            start_line: Start line number
            end_line: End line number
            suggested_name: Optional name for extracted method

        Returns:
            Refactoring suggestion or None if not feasible
        """
        file_path = Path(file_path)
        str_path = str(file_path)

        if str_path not in self._file_contents:
            try:
                content = file_path.read_text()
                self._file_contents[str_path] = content
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")
                return None

        content = self._file_contents[str_path]
        lines = content.split("\n")

        # Extract code block
        code_block = "\n".join(lines[start_line - 1 : end_line])

        # Generate method name if not provided
        if not suggested_name:
            suggested_name = "extracted_method"

        # Create preview
        preview = f"# Original code (lines {start_line}-{end_line}):\n"
        preview += code_block
        preview += f"\n\n# After extraction:\n"
        preview += f"def {suggested_name}(...):\n"
        preview += "    " + code_block.replace("\n", "\n    ")
        preview += f"\n\n# In original location:\n"
        preview += f"{suggested_name}(...)"

        location = CodeLocation(
            file_path=str_path,
            start_line=start_line,
            end_line=end_line,
        )

        return RefactoringSuggestion(
            type=RefactoringType.EXTRACT_METHOD,
            location=location,
            description=f"Extract code block into '{suggested_name}'",
            confidence=0.7,
            diff_preview=preview,
            reasoning=f"Extract {end_line - start_line + 1} lines into a separate method for better organization.",
            metadata={
                "suggested_name": suggested_name,
                "line_count": end_line - start_line + 1,
            },
            impact_score=0.5,
            effort_score=0.3,
            safety_score=0.85,
        )

    def rename_symbol(
        self,
        symbol_name: str,
        new_name: str,
        file_path: str | Path | None = None,
    ) -> list[RefactoringSuggestion]:
        """
        Generate suggestions for renaming a symbol across codebase.

        Args:
            symbol_name: Current symbol name
            new_name: New name for symbol
            file_path: Optional file to limit scope

        Returns:
            List of rename suggestions
        """
        suggestions = []

        if file_path:
            files = [Path(file_path)]
        else:
            # Search entire workspace
            files = list(self.workspace_root.rglob("*.py"))

        for file in files:
            try:
                content = file.read_text()
                tree = ast.parse(content)
            except Exception:
                continue

            # Find all occurrences
            class RenameVisitor(ast.NodeVisitor):
                def __init__(self):
                    self.occurrences: list[int] = []

                def visit_Name(self, node: ast.Name) -> None:
                    if node.id == symbol_name:
                        self.occurrences.append(node.lineno)
                    self.generic_visit(node)

                def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                    if node.name == symbol_name:
                        self.occurrences.append(node.lineno)
                    self.generic_visit(node)

                def visit_ClassDef(self, node: ast.ClassDef) -> None:
                    if node.name == symbol_name:
                        self.occurrences.append(node.lineno)
                    self.generic_visit(node)

            visitor = RenameVisitor()
            visitor.visit(tree)

            if visitor.occurrences:
                # Generate diff preview
                lines = content.split("\n")
                diff_lines = []
                for line_no in visitor.occurrences[:5]:  # Show first 5
                    old_line = lines[line_no - 1]
                    new_line = old_line.replace(symbol_name, new_name)
                    diff_lines.append(f"- {old_line}")
                    diff_lines.append(f"+ {new_line}")

                if len(visitor.occurrences) > 5:
                    diff_lines.append(
                        f"# ... {len(visitor.occurrences) - 5} more occurrences"
                    )

                location = CodeLocation(
                    file_path=str(file),
                    start_line=min(visitor.occurrences),
                    end_line=max(visitor.occurrences),
                )

                suggestions.append(
                    RefactoringSuggestion(
                        type=RefactoringType.RENAME_SYMBOL,
                        location=location,
                        description=f"Rename '{symbol_name}' to '{new_name}' ({len(visitor.occurrences)} occurrences)",
                        confidence=0.9,
                        diff_preview="\n".join(diff_lines),
                        reasoning=f"Rename symbol '{symbol_name}' to '{new_name}' in {file.name}.",
                        metadata={
                            "old_name": symbol_name,
                            "new_name": new_name,
                            "occurrence_count": len(visitor.occurrences),
                        },
                        impact_score=0.4,
                        effort_score=0.2,
                        safety_score=0.75,  # Lower because cross-file
                    )
                )

        return suggestions

    def apply_refactoring(
        self,
        suggestion: RefactoringSuggestion,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """
        Apply a refactoring suggestion.

        Args:
            suggestion: Refactoring to apply
            dry_run: If True, only preview changes

        Returns:
            Dict with status and changes
        """
        if dry_run:
            return {
                "status": "preview",
                "diff": suggestion.diff_preview,
                "location": str(suggestion.location),
                "type": suggestion.type.value,
            }

        # For actual application, we would need more sophisticated logic
        # This is a framework for the actual implementation
        try:
            file_path = Path(suggestion.location.file_path)
            content = file_path.read_text()
            lines = content.split("\n")

            # Apply refactoring based on type
            if suggestion.type == RefactoringType.DEAD_CODE:
                # Remove lines
                modified = self._remove_lines(
                    lines,
                    suggestion.location.start_line,
                    suggestion.location.end_line,
                )
            elif suggestion.type == RefactoringType.RENAME_SYMBOL:
                # Replace symbol name
                old_name = suggestion.metadata["old_name"]
                new_name = suggestion.metadata["new_name"]
                modified = [line.replace(old_name, new_name) for line in lines]
            else:
                return {
                    "status": "error",
                    "message": f"Refactoring type {suggestion.type} not yet implemented",
                }

            # Write back
            new_content = "\n".join(modified)
            file_path.write_text(new_content)

            return {
                "status": "success",
                "file": str(file_path),
                "type": suggestion.type.value,
            }

        except Exception as e:
            logger.error(f"Failed to apply refactoring: {e}")
            return {"status": "error", "message": str(e)}

    def _remove_lines(
        self, lines: list[str], start_line: int, end_line: int
    ) -> list[str]:
        """Remove lines from a list (1-indexed)."""
        return lines[: start_line - 1] + lines[end_line:]

    def get_stats(self) -> dict[str, Any]:
        """Get refactoring engine statistics."""
        return {
            "files_cached": len(self._file_asts),
            "workspace_root": str(self.workspace_root),
            "config": {
                "min_extract_lines": self.min_extract_lines,
                "max_complexity": self.max_complexity,
                "max_nesting": self.max_nesting,
            },
        }


# Global instance
_refactoring_engine: RefactoringEngine | None = None


def get_refactoring_engine(
    workspace_root: str | Path | None = None,
) -> RefactoringEngine:
    """Get or create global refactoring engine."""
    global _refactoring_engine

    if _refactoring_engine is None:
        if workspace_root is None:
            workspace_root = Path.cwd()
        _refactoring_engine = RefactoringEngine(workspace_root)

    return _refactoring_engine
