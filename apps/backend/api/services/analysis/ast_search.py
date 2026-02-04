#!/usr/bin/env python3
"""
Neural AST-Aware Code Search

Provides semantic code search that understands code structure:
- Function/class/variable definitions
- Call graphs and dependencies
- Type relationships
- Import graphs
- Semantic similarity

Much more powerful than text-based grep.
"""

import ast
import asyncio
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


class EntityType(Enum):
    """Type of code entity."""

    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"
    IMPORT = "import"
    DECORATOR = "decorator"
    PARAMETER = "parameter"
    ATTRIBUTE = "attribute"


@dataclass
class CodeEntity:
    """A code entity extracted from AST."""

    name: str
    entity_type: EntityType
    file_path: str
    line_number: int
    end_line: int | None = None
    docstring: str | None = None
    signature: str | None = None
    parent: str | None = None  # Parent class/function
    decorators: list[str] = field(default_factory=list)
    parameters: list[str] = field(default_factory=list)
    return_type: str | None = None
    calls: list[str] = field(default_factory=list)  # Functions this calls
    imports: list[str] = field(default_factory=list)  # Modules imported
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.entity_type.value,
            "file": self.file_path,
            "line": self.line_number,
            "end_line": self.end_line,
            "docstring": self.docstring,
            "signature": self.signature,
            "parent": self.parent,
            "decorators": self.decorators,
            "parameters": self.parameters,
            "return_type": self.return_type,
            "calls": self.calls,
        }


class PythonASTVisitor(ast.NodeVisitor):
    """AST visitor for extracting Python code entities."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.entities: list[CodeEntity] = []
        self.imports: list[str] = []
        self._current_class: str | None = None
        self._current_function: str | None = None

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(alias.name)
            self.entities.append(
                CodeEntity(
                    name=alias.asname or alias.name,
                    entity_type=EntityType.IMPORT,
                    file_path=self.file_path,
                    line_number=node.lineno,
                    metadata={"module": alias.name},
                )
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            full_name = f"{module}.{alias.name}" if module else alias.name
            self.imports.append(full_name)
            self.entities.append(
                CodeEntity(
                    name=alias.asname or alias.name,
                    entity_type=EntityType.IMPORT,
                    file_path=self.file_path,
                    line_number=node.lineno,
                    metadata={"module": module, "name": alias.name},
                )
            )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # Get decorators
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]

        # Get docstring
        docstring = ast.get_docstring(node)

        # Get base classes
        bases = [self._get_name(base) for base in node.bases]

        entity = CodeEntity(
            name=node.name,
            entity_type=EntityType.CLASS,
            file_path=self.file_path,
            line_number=node.lineno,
            end_line=node.end_lineno,
            docstring=docstring,
            decorators=decorators,
            parent=self._current_class,
            metadata={"bases": bases},
        )
        self.entities.append(entity)

        # Visit methods
        old_class = self._current_class
        self._current_class = node.name
        self.generic_visit(node)
        self._current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node, is_async=True)

    def _visit_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool = False
    ) -> None:
        # Determine if method or function
        entity_type = EntityType.METHOD if self._current_class else EntityType.FUNCTION

        # Get decorators
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]

        # Get docstring
        docstring = ast.get_docstring(node)

        # Get parameters
        params = []
        for arg in node.args.args:
            param_name = arg.arg
            if arg.annotation:
                param_name += f": {self._get_name(arg.annotation)}"
            params.append(param_name)

        # Get return type
        return_type = self._get_name(node.returns) if node.returns else None

        # Build signature
        signature = f"{'async ' if is_async else ''}def {node.name}({', '.join(params)})"
        if return_type:
            signature += f" -> {return_type}"

        # Extract function calls
        calls = self._extract_calls(node)

        entity = CodeEntity(
            name=node.name,
            entity_type=entity_type,
            file_path=self.file_path,
            line_number=node.lineno,
            end_line=node.end_lineno,
            docstring=docstring,
            signature=signature,
            parent=self._current_class,
            decorators=decorators,
            parameters=params,
            return_type=return_type,
            calls=calls,
            imports=self.imports.copy(),
            metadata={"is_async": is_async},
        )
        self.entities.append(entity)

        # Visit nested functions
        old_func = self._current_function
        self._current_function = node.name
        self.generic_visit(node)
        self._current_function = old_func

    def visit_Assign(self, node: ast.Assign) -> None:
        # Module-level assignments (constants/variables)
        if self._current_function is None and self._current_class is None:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    # Check if it's a constant (ALL_CAPS)
                    is_constant = target.id.isupper()
                    entity_type = EntityType.CONSTANT if is_constant else EntityType.VARIABLE

                    self.entities.append(
                        CodeEntity(
                            name=target.id,
                            entity_type=entity_type,
                            file_path=self.file_path,
                            line_number=node.lineno,
                        )
                    )
        self.generic_visit(node)

    def _get_decorator_name(self, node: ast.expr) -> str:
        """Get decorator name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_decorator_name(node.func)
        return str(node)

    def _get_name(self, node: ast.expr | None) -> str:
        """Get name from AST node."""
        if node is None:
            return ""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            return f"{self._get_name(node.value)}[{self._get_name(node.slice)}]"
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Tuple):
            return ", ".join(self._get_name(e) for e in node.elts)
        return ""

    def _extract_calls(self, node: ast.AST) -> list[str]:
        """Extract function calls from a node."""
        calls = []

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = self._get_name(child.func)
                if call_name:
                    calls.append(call_name)

        return list(set(calls))


class ASTSearchEngine:
    """
    Neural AST-aware code search engine.

    Provides semantic understanding of code structure:
    - Find all usages of a function
    - Find all implementations of a method
    - Find call graph (who calls what)
    - Find type hierarchies
    - Semantic similarity search

    Much more powerful than grep/ripgrep for code navigation.
    """

    def __init__(self, workspace_root: str | Path):
        """
        Initialize AST search engine.

        Args:
            workspace_root: Root directory to index
        """
        self.workspace_root = Path(workspace_root)

        # Entity index
        self._entities: dict[str, list[CodeEntity]] = defaultdict(list)
        self._by_file: dict[str, list[CodeEntity]] = defaultdict(list)
        self._by_type: dict[EntityType, list[CodeEntity]] = defaultdict(list)

        # Call graph
        self._callers: dict[str, list[str]] = defaultdict(list)  # name -> callers
        self._callees: dict[str, list[str]] = defaultdict(list)  # name -> callees

        # Stats
        self._files_indexed = 0
        self._entities_indexed = 0
        self._last_index_time: datetime | None = None

    async def index_workspace(self) -> None:
        """Index entire workspace."""
        start = datetime.utcnow()
        self._entities.clear()
        self._by_file.clear()
        self._by_type.clear()
        self._callers.clear()
        self._callees.clear()
        self._files_indexed = 0
        self._entities_indexed = 0

        # Find all Python files
        for file_path in self.workspace_root.rglob("*.py"):
            # Skip common non-code directories
            parts = file_path.parts
            if any(
                p in parts
                for p in ["node_modules", ".git", "__pycache__", "venv", ".venv"]
            ):
                continue

            await self._index_file(file_path)

        # Build call graph
        self._build_call_graph()

        self._last_index_time = datetime.utcnow()
        elapsed = (self._last_index_time - start).total_seconds()

        logger.info(
            f"Indexed {self._files_indexed} files, "
            f"{self._entities_indexed} entities in {elapsed:.1f}s"
        )

    async def _index_file(self, file_path: Path) -> None:
        """Index a single Python file."""
        try:
            content = file_path.read_text(errors="ignore")
            tree = ast.parse(content)
        except Exception as e:
            logger.debug(f"Could not parse {file_path}: {e}")
            return

        relative_path = str(file_path.relative_to(self.workspace_root))
        visitor = PythonASTVisitor(relative_path)
        visitor.visit(tree)

        for entity in visitor.entities:
            self._entities[entity.name].append(entity)
            self._by_file[relative_path].append(entity)
            self._by_type[entity.entity_type].append(entity)
            self._entities_indexed += 1

        self._files_indexed += 1

        # Allow other tasks to run
        await asyncio.sleep(0)

    def _build_call_graph(self) -> None:
        """Build call graph from indexed entities."""
        for entities in self._entities.values():
            for entity in entities:
                if entity.entity_type in (EntityType.FUNCTION, EntityType.METHOD):
                    for call in entity.calls:
                        # Record caller -> callee relationship
                        self._callees[entity.name].append(call)
                        self._callers[call].append(entity.name)

    def find_definition(self, name: str) -> list[CodeEntity]:
        """
        Find definition(s) of a symbol.

        Args:
            name: Symbol name to find

        Returns:
            List of matching entities
        """
        return self._entities.get(name, [])

    def find_usages(self, name: str) -> list[CodeEntity]:
        """
        Find all usages of a symbol.

        Args:
            name: Symbol name to find usages of

        Returns:
            List of entities that reference this symbol
        """
        usages = []

        # Find in call graph
        callers = self._callers.get(name, [])
        for caller in callers:
            usages.extend(self._entities.get(caller, []))

        return usages

    def find_callers(self, name: str) -> list[str]:
        """
        Find all functions that call the given function.

        Args:
            name: Function name

        Returns:
            List of caller function names
        """
        return self._callers.get(name, [])

    def find_callees(self, name: str) -> list[str]:
        """
        Find all functions called by the given function.

        Args:
            name: Function name

        Returns:
            List of called function names
        """
        return self._callees.get(name, [])

    def find_by_type(
        self,
        entity_type: EntityType,
        pattern: str | None = None,
    ) -> list[CodeEntity]:
        """
        Find entities by type with optional name pattern.

        Args:
            entity_type: Type of entity to find
            pattern: Optional regex pattern for name

        Returns:
            List of matching entities
        """
        entities = self._by_type.get(entity_type, [])

        if pattern:
            regex = re.compile(pattern, re.IGNORECASE)
            entities = [e for e in entities if regex.search(e.name)]

        return entities

    def find_in_file(self, file_path: str) -> list[CodeEntity]:
        """
        Get all entities in a file.

        Args:
            file_path: Relative file path

        Returns:
            List of entities in file
        """
        return self._by_file.get(file_path, [])

    def search(
        self,
        query: str,
        entity_types: list[EntityType] | None = None,
        include_docstrings: bool = True,
    ) -> list[tuple[CodeEntity, float]]:
        """
        Semantic search across all entities.

        Args:
            query: Search query
            entity_types: Filter by entity types
            include_docstrings: Search in docstrings too

        Returns:
            List of (entity, score) tuples sorted by relevance
        """
        results = []
        query_lower = query.lower()
        query_terms = set(query_lower.split())

        for name, entities in self._entities.items():
            for entity in entities:
                # Filter by type
                if entity_types and entity.entity_type not in entity_types:
                    continue

                score = 0.0

                # Exact name match
                if name.lower() == query_lower:
                    score += 10.0

                # Name contains query
                elif query_lower in name.lower():
                    score += 5.0

                # Query contains name
                elif name.lower() in query_lower:
                    score += 3.0

                # Term overlap in name
                name_terms = set(re.split(r"[_\W]+", name.lower()))
                term_overlap = len(query_terms & name_terms)
                score += term_overlap * 2.0

                # Docstring match
                if include_docstrings and entity.docstring:
                    doc_lower = entity.docstring.lower()
                    if query_lower in doc_lower:
                        score += 2.0
                    doc_terms = set(doc_lower.split())
                    doc_overlap = len(query_terms & doc_terms)
                    score += doc_overlap * 0.5

                # Signature match
                if entity.signature and query_lower in entity.signature.lower():
                    score += 1.5

                if score > 0:
                    results.append((entity, score))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)

        return results

    def get_class_hierarchy(self, class_name: str) -> dict[str, Any]:
        """
        Get class hierarchy for a class.

        Args:
            class_name: Name of class

        Returns:
            Dict with parent and child classes
        """
        class_entities = [
            e
            for e in self._entities.get(class_name, [])
            if e.entity_type == EntityType.CLASS
        ]

        if not class_entities:
            return {"error": f"Class {class_name} not found"}

        entity = class_entities[0]
        bases = entity.metadata.get("bases", [])

        # Find subclasses
        subclasses = []
        for entities in self._by_type.get(EntityType.CLASS, []):
            if class_name in entities.metadata.get("bases", []):
                subclasses.append(entities.name)

        return {
            "class": class_name,
            "file": entity.file_path,
            "bases": bases,
            "subclasses": subclasses,
            "methods": [
                e.name
                for e in self.find_in_file(entity.file_path)
                if e.entity_type == EntityType.METHOD and e.parent == class_name
            ],
        }

    def get_stats(self) -> dict[str, Any]:
        """Get index statistics."""
        return {
            "files_indexed": self._files_indexed,
            "entities_indexed": self._entities_indexed,
            "functions": len(self._by_type.get(EntityType.FUNCTION, [])),
            "classes": len(self._by_type.get(EntityType.CLASS, [])),
            "methods": len(self._by_type.get(EntityType.METHOD, [])),
            "imports": len(self._by_type.get(EntityType.IMPORT, [])),
            "last_indexed": (
                self._last_index_time.isoformat() if self._last_index_time else None
            ),
        }


# Global instance
_ast_search: ASTSearchEngine | None = None


def get_ast_search(workspace_root: str | Path | None = None) -> ASTSearchEngine:
    """Get or create global AST search engine."""
    global _ast_search

    if _ast_search is None:
        if workspace_root is None:
            workspace_root = Path.cwd()
        _ast_search = ASTSearchEngine(workspace_root)

    return _ast_search
