#!/usr/bin/env python3
"""
Multi-Language Code Analyzers

Production-quality code analysis system supporting:
- TypeScript/JavaScript - AST parsing, type extraction
- Go - struct/interface extraction, package analysis
- Rust - trait/impl analysis, lifetime detection
- Java - class hierarchy, annotation processing
- Python - Full AST analysis (delegated to ast_search module)

Each analyzer provides:
- parse_file() - Parse source file into AST
- extract_entities() - Extract symbols (classes, functions, etc.)
- find_dependencies() - Analyze imports and module dependencies
- get_call_graph() - Build function call relationships

Uses tree-sitter for robust parsing with regex fallback for portability.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from api.utils.structured_logging import get_logger

logger = get_logger(__name__)


# ===== Language Types =====


class Language(str, Enum):
    """Supported programming languages."""

    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    TSX = "tsx"
    JSX = "jsx"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    C = "c"
    CPP = "cpp"
    CSHARP = "csharp"
    PHP = "php"
    RUBY = "ruby"
    SWIFT = "swift"
    KOTLIN = "kotlin"
    UNKNOWN = "unknown"

    @classmethod
    def from_extension(cls, extension: str) -> "Language":
        """Detect language from file extension."""
        ext_map = {
            ".py": cls.PYTHON,
            ".ts": cls.TYPESCRIPT,
            ".tsx": cls.TSX,
            ".js": cls.JAVASCRIPT,
            ".jsx": cls.JSX,
            ".go": cls.GO,
            ".rs": cls.RUST,
            ".java": cls.JAVA,
            ".c": cls.C,
            ".h": cls.C,
            ".cpp": cls.CPP,
            ".cc": cls.CPP,
            ".cxx": cls.CPP,
            ".hpp": cls.CPP,
            ".cs": cls.CSHARP,
            ".php": cls.PHP,
            ".rb": cls.RUBY,
            ".swift": cls.SWIFT,
            ".kt": cls.KOTLIN,
        }
        return ext_map.get(extension.lower(), cls.UNKNOWN)

    def is_typescript_family(self) -> bool:
        """Check if language is TypeScript/JavaScript."""
        return self in (
            Language.TYPESCRIPT,
            Language.JAVASCRIPT,
            Language.TSX,
            Language.JSX,
        )


# ===== Unified Code Entity =====


@dataclass
class CodeEntity:
    """
    Unified code entity across all languages.

    Normalized representation that works for classes, functions, methods,
    interfaces, structs, traits, etc. across all supported languages.
    """

    name: str
    entity_type: str  # function, class, method, interface, struct, trait, etc.
    language: Language
    file_path: str
    line_number: int
    end_line: Optional[int] = None
    docstring: Optional[str] = None
    signature: Optional[str] = None
    parent: Optional[str] = None  # Parent class/module/namespace
    modifiers: list[str] = field(default_factory=list)  # public, static, async, etc.
    decorators: list[str] = field(default_factory=list)  # @decorator, #[derive(...)]
    parameters: list[dict[str, Any]] = field(
        default_factory=list
    )  # [{name, type, default}, ...]
    return_type: Optional[str] = None
    type_parameters: list[str] = field(default_factory=list)  # Generic types
    implements: list[str] = field(default_factory=list)  # Interfaces/traits
    extends: list[str] = field(default_factory=list)  # Base classes
    annotations: list[str] = field(default_factory=list)  # @Annotation (Java)
    attributes: list[str] = field(default_factory=list)  # Class fields/properties
    methods: list[str] = field(default_factory=list)  # Method names (for classes)
    calls: list[str] = field(default_factory=list)  # Functions this calls
    imports: list[str] = field(default_factory=list)  # Module imports
    exports: list[str] = field(default_factory=list)  # Exported symbols
    metadata: dict[str, Any] = field(default_factory=dict)  # Language-specific data

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "type": self.entity_type,
            "language": self.language.value,
            "file": self.file_path,
            "line": self.line_number,
            "end_line": self.end_line,
            "docstring": self.docstring,
            "signature": self.signature,
            "parent": self.parent,
            "modifiers": self.modifiers,
            "decorators": self.decorators,
            "parameters": self.parameters,
            "return_type": self.return_type,
            "type_parameters": self.type_parameters,
            "implements": self.implements,
            "extends": self.extends,
            "annotations": self.annotations,
            "attributes": self.attributes,
            "methods": self.methods,
            "calls": self.calls,
            "imports": self.imports,
            "exports": self.exports,
            "metadata": self.metadata,
        }


@dataclass
class DependencyInfo:
    """Dependency/import information."""

    module: str
    symbols: list[str] = field(default_factory=list)  # Specific imported symbols
    alias: Optional[str] = None
    is_relative: bool = False
    line_number: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)  # Language-specific data


@dataclass
class CallGraphNode:
    """Node in function call graph."""

    function: str
    file_path: str
    line_number: int
    calls: list[str] = field(default_factory=list)  # Functions it calls
    called_by: list[str] = field(default_factory=list)  # Functions that call it


@dataclass
class ParseResult:
    """Result of parsing a source file."""

    language: Language
    file_path: str
    entities: list[CodeEntity] = field(default_factory=list)
    dependencies: list[DependencyInfo] = field(default_factory=list)
    call_graph: dict[str, CallGraphNode] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# ===== Abstract Base Analyzer =====


class LanguageAnalyzer(ABC):
    """
    Abstract base class for language-specific analyzers.

    Each language analyzer must implement:
    - parse_file() - Parse source file into entities
    - extract_entities() - Extract symbols from source
    - find_dependencies() - Analyze imports/dependencies
    - get_call_graph() - Build function call graph
    """

    def __init__(self, language: Language):
        """Initialize analyzer for specific language."""
        self.language = language
        self._tree_sitter_available = self._check_tree_sitter()

    def _check_tree_sitter(self) -> bool:
        """Check if tree-sitter is available for this language."""
        try:
            import tree_sitter  # noqa: F401

            return True
        except ImportError:
            logger.debug(
                f"tree-sitter not available for {self.language}, using regex fallback"
            )
            return False

    @abstractmethod
    def parse_file(self, file_path: str | Path) -> ParseResult:
        """
        Parse a source file and extract all information.

        Args:
            file_path: Path to source file

        Returns:
            ParseResult with entities, dependencies, and call graph
        """
        pass

    @abstractmethod
    def extract_entities(self, source_code: str, file_path: str) -> list[CodeEntity]:
        """
        Extract code entities from source code.

        Args:
            source_code: Source code content
            file_path: File path for entity references

        Returns:
            List of extracted entities
        """
        pass

    @abstractmethod
    def find_dependencies(
        self, source_code: str, file_path: str
    ) -> list[DependencyInfo]:
        """
        Find all dependencies/imports in source code.

        Args:
            source_code: Source code content
            file_path: File path for context

        Returns:
            List of dependencies
        """
        pass

    @abstractmethod
    def get_call_graph(
        self, source_code: str, file_path: str
    ) -> dict[str, CallGraphNode]:
        """
        Build call graph for source code.

        Args:
            source_code: Source code content
            file_path: File path for context

        Returns:
            Dict mapping function names to call graph nodes
        """
        pass

    def _extract_docstring(self, lines: list[str], start_idx: int) -> Optional[str]:
        """
        Extract docstring/comment block starting at given line.

        Works for:
        - Python: '''docstring''' or \"\"\"docstring\"\"\"
        - JSDoc: /** comment */
        - Go: // comment or /* comment */
        - Rust: /// comment or //! comment
        - Java: /** javadoc */
        """
        if start_idx >= len(lines):
            return None

        doc_lines = []
        i = start_idx

        # Multi-line comment patterns
        if "/**" in lines[i] or '"""' in lines[i] or "'''" in lines[i]:
            # JSDoc or Python docstring
            if "/**" in lines[i]:
                end_marker = "*/"
            elif '"""' in lines[i]:
                end_marker = '"""'
            else:
                end_marker = "'''"

            while i < len(lines):
                line = lines[i].strip()
                doc_lines.append(line)
                if end_marker in line and i > start_idx:
                    break
                i += 1

        # Single-line comment patterns
        elif any(
            lines[i].strip().startswith(prefix) for prefix in ["//", "///", "//!", "#"]
        ):
            while i < len(lines):
                line = lines[i].strip()
                if not any(line.startswith(prefix) for prefix in ["//", "///", "//!", "#"]):
                    break
                doc_lines.append(line)
                i += 1

        if doc_lines:
            # Clean up comment markers
            cleaned = []
            for line in doc_lines:
                line = re.sub(r"^[\/\*#]+\s*", "", line)
                line = re.sub(r"\s*[\*\/]+$", "", line)
                cleaned.append(line.strip())
            return "\n".join(cleaned).strip()

        return None


# ===== TypeScript/JavaScript Analyzer =====


class TypeScriptAnalyzer(LanguageAnalyzer):
    """
    Analyzer for TypeScript and JavaScript.

    Extracts:
    - Functions, classes, interfaces, types
    - JSDoc comments
    - Import/export statements
    - Type annotations (TypeScript)
    - Async/await patterns
    - React components (TSX/JSX)
    """

    def __init__(self, language: Language = Language.TYPESCRIPT):
        """Initialize TypeScript analyzer."""
        super().__init__(language)

    def parse_file(self, file_path: str | Path) -> ParseResult:
        """Parse TypeScript/JavaScript file."""
        file_path = Path(file_path)
        try:
            source_code = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            return ParseResult(
                language=self.language,
                file_path=str(file_path),
                errors=[f"Failed to read file: {e}"],
            )

        entities = self.extract_entities(source_code, str(file_path))
        dependencies = self.find_dependencies(source_code, str(file_path))
        call_graph = self.get_call_graph(source_code, str(file_path))

        return ParseResult(
            language=self.language,
            file_path=str(file_path),
            entities=entities,
            dependencies=dependencies,
            call_graph=call_graph,
        )

    def extract_entities(self, source_code: str, file_path: str) -> list[CodeEntity]:
        """Extract entities from TypeScript/JavaScript source."""
        entities = []
        lines = source_code.split("\n")

        # Extract interfaces
        interface_pattern = re.compile(
            r"^\s*(?:export\s+)?(?:interface|type)\s+(\w+)(?:<([^>]+)>)?(?:\s+extends\s+([\w\s,]+))?\s*\{",
            re.MULTILINE,
        )
        for match in interface_pattern.finditer(source_code):
            line_num = source_code[: match.start()].count("\n") + 1
            name = match.group(1)
            type_params = match.group(2)
            extends = match.group(3)

            entity = CodeEntity(
                name=name,
                entity_type="interface" if "interface" in match.group(0) else "type",
                language=self.language,
                file_path=file_path,
                line_number=line_num,
                type_parameters=type_params.split(",") if type_params else [],
                extends=extends.split(",") if extends else [],
                metadata={"exported": "export" in match.group(0)},
            )
            entities.append(entity)

        # Extract classes
        class_pattern = re.compile(
            r"^\s*(?:export\s+)?(?:abstract\s+)?class\s+(\w+)(?:<([^>]+)>)?(?:\s+extends\s+([\w.]+))?(?:\s+implements\s+([\w\s,]+))?\s*\{",
            re.MULTILINE,
        )
        for match in class_pattern.finditer(source_code):
            line_num = source_code[: match.start()].count("\n") + 1
            name = match.group(1)
            type_params = match.group(2)
            extends = match.group(3)
            implements = match.group(4)

            # Find class body and extract methods
            methods = self._extract_class_methods(source_code, match.end(), lines)

            entity = CodeEntity(
                name=name,
                entity_type="class",
                language=self.language,
                file_path=file_path,
                line_number=line_num,
                type_parameters=type_params.split(",") if type_params else [],
                extends=[extends] if extends else [],
                implements=implements.split(",") if implements else [],
                methods=methods,
                modifiers=self._extract_modifiers(match.group(0)),
                metadata={"exported": "export" in match.group(0)},
            )
            entities.append(entity)

        # Extract functions
        func_pattern = re.compile(
            r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*(?:<([^>]+)>)?\s*\(([^)]*)\)\s*(?::\s*([^{;]+))?\s*[{;]",
            re.MULTILINE,
        )
        for match in func_pattern.finditer(source_code):
            line_num = source_code[: match.start()].count("\n") + 1
            name = match.group(1)
            type_params = match.group(2)
            params = match.group(3)
            return_type = match.group(4)

            entity = CodeEntity(
                name=name,
                entity_type="function",
                language=self.language,
                file_path=file_path,
                line_number=line_num,
                signature=match.group(0).strip(),
                type_parameters=type_params.split(",") if type_params else [],
                parameters=self._parse_parameters(params),
                return_type=return_type.strip() if return_type else None,
                modifiers=["async"] if "async" in match.group(0) else [],
                metadata={"exported": "export" in match.group(0)},
            )
            entities.append(entity)

        # Extract arrow functions (const/let/var name = (...) => ...)
        arrow_pattern = re.compile(
            r"^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*(?::\s*([^=]+))?\s*=\s*(?:async\s+)?\([^)]*\)\s*(?::\s*([^=]+))?\s*=>",
            re.MULTILINE,
        )
        for match in arrow_pattern.finditer(source_code):
            line_num = source_code[: match.start()].count("\n") + 1
            name = match.group(1)
            type_annotation = match.group(2)
            return_type = match.group(3)

            entity = CodeEntity(
                name=name,
                entity_type="function",
                language=self.language,
                file_path=file_path,
                line_number=line_num,
                signature=match.group(0).strip(),
                return_type=return_type.strip() if return_type else None,
                modifiers=["async"] if "async" in match.group(0) else [],
                metadata={
                    "exported": "export" in match.group(0),
                    "arrow_function": True,
                },
            )
            entities.append(entity)

        return entities

    def find_dependencies(
        self, source_code: str, file_path: str
    ) -> list[DependencyInfo]:
        """Find TypeScript/JavaScript imports."""
        dependencies = []

        # import { x, y } from 'module'
        named_import_pattern = re.compile(
            r"import\s+\{([^}]+)\}\s+from\s+['\"]([^'\"]+)['\"]"
        )
        for match in named_import_pattern.finditer(source_code):
            symbols = [s.strip() for s in match.group(1).split(",")]
            module = match.group(2)
            line_num = source_code[: match.start()].count("\n") + 1

            dependencies.append(
                DependencyInfo(
                    module=module,
                    symbols=symbols,
                    is_relative=module.startswith("."),
                    line_number=line_num,
                )
            )

        # import module from 'module'
        default_import_pattern = re.compile(
            r"import\s+(\w+)\s+from\s+['\"]([^'\"]+)['\"]"
        )
        for match in default_import_pattern.finditer(source_code):
            symbol = match.group(1)
            module = match.group(2)
            line_num = source_code[: match.start()].count("\n") + 1

            dependencies.append(
                DependencyInfo(
                    module=module,
                    symbols=[symbol],
                    is_relative=module.startswith("."),
                    line_number=line_num,
                )
            )

        # import * as name from 'module'
        namespace_import_pattern = re.compile(
            r"import\s+\*\s+as\s+(\w+)\s+from\s+['\"]([^'\"]+)['\"]"
        )
        for match in namespace_import_pattern.finditer(source_code):
            alias = match.group(1)
            module = match.group(2)
            line_num = source_code[: match.start()].count("\n") + 1

            dependencies.append(
                DependencyInfo(
                    module=module,
                    alias=alias,
                    is_relative=module.startswith("."),
                    line_number=line_num,
                )
            )

        # require() calls
        require_pattern = re.compile(r"require\(['\"]([^'\"]+)['\"]\)")
        for match in require_pattern.finditer(source_code):
            module = match.group(1)
            line_num = source_code[: match.start()].count("\n") + 1

            dependencies.append(
                DependencyInfo(
                    module=module,
                    is_relative=module.startswith("."),
                    line_number=line_num,
                )
            )

        return dependencies

    def get_call_graph(
        self, source_code: str, file_path: str
    ) -> dict[str, CallGraphNode]:
        """Build call graph for TypeScript/JavaScript."""
        call_graph = {}

        # Extract function calls
        call_pattern = re.compile(r"(\w+)\s*\(")
        functions = self._extract_function_names(source_code)

        for func_name in functions:
            # Find all calls within this function
            func_pattern = re.compile(
                rf"function\s+{func_name}\s*\([^)]*\)\s*{{([^}}]*}})",
                re.MULTILINE | re.DOTALL,
            )
            match = func_pattern.search(source_code)

            if match:
                func_body = match.group(1)
                calls = [
                    m.group(1)
                    for m in call_pattern.finditer(func_body)
                    if m.group(1) != func_name
                ]

                line_num = source_code[: match.start()].count("\n") + 1
                call_graph[func_name] = CallGraphNode(
                    function=func_name,
                    file_path=file_path,
                    line_number=line_num,
                    calls=list(set(calls)),
                )

        return call_graph

    def _extract_class_methods(
        self, source_code: str, start_pos: int, lines: list[str]
    ) -> list[str]:
        """Extract method names from class body."""
        methods = []

        # Find class body
        brace_count = 1
        end_pos = start_pos

        for i in range(start_pos, len(source_code)):
            if source_code[i] == "{":
                brace_count += 1
            elif source_code[i] == "}":
                brace_count -= 1
                if brace_count == 0:
                    end_pos = i
                    break

        class_body = source_code[start_pos:end_pos]

        # Extract method names
        method_pattern = re.compile(
            r"^\s*(?:public|private|protected|static|async)?\s*(\w+)\s*\(",
            re.MULTILINE,
        )
        for match in method_pattern.finditer(class_body):
            methods.append(match.group(1))

        return methods

    def _extract_function_names(self, source_code: str) -> list[str]:
        """Extract all function names from source."""
        names = []

        # Regular functions
        func_pattern = re.compile(r"function\s+(\w+)\s*\(")
        names.extend([m.group(1) for m in func_pattern.finditer(source_code)])

        # Arrow functions
        arrow_pattern = re.compile(r"(?:const|let|var)\s+(\w+)\s*=.*=>")
        names.extend([m.group(1) for m in arrow_pattern.finditer(source_code)])

        return list(set(names))

    def _parse_parameters(self, params_str: str) -> list[dict[str, Any]]:
        """Parse function parameters."""
        if not params_str.strip():
            return []

        parameters = []
        for param in params_str.split(","):
            param = param.strip()
            if not param:
                continue

            # Parse name: type = default
            match = re.match(r"(\w+)(?:\?)?(?:\s*:\s*([^=]+))?(?:\s*=\s*(.+))?", param)
            if match:
                parameters.append(
                    {
                        "name": match.group(1),
                        "type": match.group(2).strip() if match.group(2) else None,
                        "default": match.group(3).strip() if match.group(3) else None,
                        "optional": "?" in param,
                    }
                )

        return parameters

    def _extract_modifiers(self, declaration: str) -> list[str]:
        """Extract modifiers from declaration."""
        modifiers = []
        for mod in ["export", "async", "abstract", "static", "public", "private"]:
            if mod in declaration:
                modifiers.append(mod)
        return modifiers


# ===== Go Analyzer =====


class GoAnalyzer(LanguageAnalyzer):
    """
    Analyzer for Go language.

    Extracts:
    - Packages, structs, interfaces
    - Functions and methods
    - Type definitions
    - Import statements
    - Receiver types
    """

    def __init__(self):
        """Initialize Go analyzer."""
        super().__init__(Language.GO)

    def parse_file(self, file_path: str | Path) -> ParseResult:
        """Parse Go source file."""
        file_path = Path(file_path)
        try:
            source_code = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            return ParseResult(
                language=self.language,
                file_path=str(file_path),
                errors=[f"Failed to read file: {e}"],
            )

        entities = self.extract_entities(source_code, str(file_path))
        dependencies = self.find_dependencies(source_code, str(file_path))
        call_graph = self.get_call_graph(source_code, str(file_path))

        # Extract package name
        package_match = re.search(r"^\s*package\s+(\w+)", source_code, re.MULTILINE)
        package_name = package_match.group(1) if package_match else "main"

        return ParseResult(
            language=self.language,
            file_path=str(file_path),
            entities=entities,
            dependencies=dependencies,
            call_graph=call_graph,
            metadata={"package": package_name},
        )

    def extract_entities(self, source_code: str, file_path: str) -> list[CodeEntity]:
        """Extract entities from Go source."""
        entities = []

        # Extract structs
        struct_pattern = re.compile(
            r"type\s+(\w+)\s+struct\s*\{([^}]*)\}", re.MULTILINE | re.DOTALL
        )
        for match in struct_pattern.finditer(source_code):
            line_num = source_code[: match.start()].count("\n") + 1
            name = match.group(1)
            body = match.group(2)

            # Extract fields
            field_pattern = re.compile(r"^\s*(\w+)\s+([^\n]+)", re.MULTILINE)
            fields = [m.group(1) for m in field_pattern.finditer(body)]

            entity = CodeEntity(
                name=name,
                entity_type="struct",
                language=self.language,
                file_path=file_path,
                line_number=line_num,
                attributes=fields,
            )
            entities.append(entity)

        # Extract interfaces
        interface_pattern = re.compile(
            r"type\s+(\w+)\s+interface\s*\{([^}]*)\}", re.MULTILINE | re.DOTALL
        )
        for match in interface_pattern.finditer(source_code):
            line_num = source_code[: match.start()].count("\n") + 1
            name = match.group(1)
            body = match.group(2)

            # Extract method signatures
            method_pattern = re.compile(r"^\s*(\w+)\s*\([^)]*\)", re.MULTILINE)
            methods = [m.group(1) for m in method_pattern.finditer(body)]

            entity = CodeEntity(
                name=name,
                entity_type="interface",
                language=self.language,
                file_path=file_path,
                line_number=line_num,
                methods=methods,
            )
            entities.append(entity)

        # Extract functions
        func_pattern = re.compile(
            r"func\s+(?:\((\w+)\s+\*?(\w+)\)\s+)?(\w+)\s*\(([^)]*)\)\s*(?:\(([^)]*)\)|(\w+))?\s*\{",
            re.MULTILINE,
        )
        for match in func_pattern.finditer(source_code):
            line_num = source_code[: match.start()].count("\n") + 1
            receiver_name = match.group(1)
            receiver_type = match.group(2)
            func_name = match.group(3)
            params = match.group(4)
            return_type = match.group(5) or match.group(6)

            entity_type = "method" if receiver_type else "function"

            entity = CodeEntity(
                name=func_name,
                entity_type=entity_type,
                language=self.language,
                file_path=file_path,
                line_number=line_num,
                signature=match.group(0).strip(),
                parent=receiver_type,
                parameters=self._parse_go_parameters(params),
                return_type=return_type,
                metadata={"receiver": receiver_name} if receiver_name else {},
            )
            entities.append(entity)

        # Extract type aliases
        type_pattern = re.compile(r"type\s+(\w+)\s+(\w+)", re.MULTILINE)
        for match in type_pattern.finditer(source_code):
            if "struct" not in match.group(0) and "interface" not in match.group(0):
                line_num = source_code[: match.start()].count("\n") + 1
                name = match.group(1)
                base_type = match.group(2)

                entity = CodeEntity(
                    name=name,
                    entity_type="type",
                    language=self.language,
                    file_path=file_path,
                    line_number=line_num,
                    metadata={"base_type": base_type},
                )
                entities.append(entity)

        return entities

    def find_dependencies(
        self, source_code: str, file_path: str
    ) -> list[DependencyInfo]:
        """Find Go imports."""
        dependencies = []

        # Single import
        single_import_pattern = re.compile(r'import\s+"([^"]+)"')
        for match in single_import_pattern.finditer(source_code):
            line_num = source_code[: match.start()].count("\n") + 1
            dependencies.append(
                DependencyInfo(module=match.group(1), line_number=line_num)
            )

        # Import block
        import_block_pattern = re.compile(
            r"import\s*\(\s*([^)]+)\)", re.MULTILINE | re.DOTALL
        )
        for match in import_block_pattern.finditer(source_code):
            block = match.group(1)
            for line in block.split("\n"):
                import_match = re.search(r'"([^"]+)"', line)
                if import_match:
                    line_num = source_code[: match.start()].count("\n") + 1
                    dependencies.append(
                        DependencyInfo(module=import_match.group(1), line_number=line_num)
                    )

        return dependencies

    def get_call_graph(
        self, source_code: str, file_path: str
    ) -> dict[str, CallGraphNode]:
        """Build call graph for Go."""
        call_graph = {}

        # Extract function bodies and their calls
        func_pattern = re.compile(
            r"func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\([^)]*\)[^{]*\{",
            re.MULTILINE,
        )

        for match in func_pattern.finditer(source_code):
            func_name = match.group(1)
            line_num = source_code[: match.start()].count("\n") + 1

            # Find function body
            start = match.end()
            brace_count = 1
            end = start

            for i in range(start, len(source_code)):
                if source_code[i] == "{":
                    brace_count += 1
                elif source_code[i] == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        end = i
                        break

            func_body = source_code[start:end]

            # Extract function calls
            call_pattern = re.compile(r"(\w+)\s*\(")
            calls = list(
                set(
                    m.group(1)
                    for m in call_pattern.finditer(func_body)
                    if m.group(1) != func_name
                )
            )

            call_graph[func_name] = CallGraphNode(
                function=func_name,
                file_path=file_path,
                line_number=line_num,
                calls=calls,
            )

        return call_graph

    def _parse_go_parameters(self, params_str: str) -> list[dict[str, Any]]:
        """Parse Go function parameters."""
        if not params_str.strip():
            return []

        parameters = []
        # Go params: name type, name type
        for param in params_str.split(","):
            param = param.strip()
            if not param:
                continue

            parts = param.split()
            if len(parts) >= 2:
                parameters.append({"name": parts[0], "type": " ".join(parts[1:])})
            elif len(parts) == 1:
                # Type only
                parameters.append({"name": "", "type": parts[0]})

        return parameters


# ===== Rust Analyzer =====


class RustAnalyzer(LanguageAnalyzer):
    """
    Analyzer for Rust language.

    Extracts:
    - Structs, enums, traits
    - impl blocks and methods
    - Functions
    - Lifetimes and generics
    - Attributes and derive macros
    - Visibility modifiers
    """

    def __init__(self):
        """Initialize Rust analyzer."""
        super().__init__(Language.RUST)

    def parse_file(self, file_path: str | Path) -> ParseResult:
        """Parse Rust source file."""
        file_path = Path(file_path)
        try:
            source_code = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            return ParseResult(
                language=self.language,
                file_path=str(file_path),
                errors=[f"Failed to read file: {e}"],
            )

        entities = self.extract_entities(source_code, str(file_path))
        dependencies = self.find_dependencies(source_code, str(file_path))
        call_graph = self.get_call_graph(source_code, str(file_path))

        return ParseResult(
            language=self.language,
            file_path=str(file_path),
            entities=entities,
            dependencies=dependencies,
            call_graph=call_graph,
        )

    def extract_entities(self, source_code: str, file_path: str) -> list[CodeEntity]:
        """Extract entities from Rust source."""
        entities = []

        # Extract structs
        struct_pattern = re.compile(
            r"(?:#\[([^\]]+)\]\s*)*(?:pub\s+)?struct\s+(\w+)(?:<([^>]+)>)?\s*(?:\{([^}]*)\}|;)",
            re.MULTILINE | re.DOTALL,
        )
        for match in struct_pattern.finditer(source_code):
            line_num = source_code[: match.start()].count("\n") + 1
            attributes = match.group(1)
            name = match.group(2)
            generics = match.group(3)
            body = match.group(4)

            # Extract fields if present
            fields = []
            if body:
                field_pattern = re.compile(r"(?:pub\s+)?(\w+)\s*:\s*([^,\n]+)")
                fields = [m.group(1) for m in field_pattern.finditer(body)]

            entity = CodeEntity(
                name=name,
                entity_type="struct",
                language=self.language,
                file_path=file_path,
                line_number=line_num,
                type_parameters=generics.split(",") if generics else [],
                attributes=fields,
                decorators=self._parse_rust_attributes(attributes),
                modifiers=["pub"] if "pub" in match.group(0) else [],
            )
            entities.append(entity)

        # Extract enums
        enum_pattern = re.compile(
            r"(?:#\[([^\]]+)\]\s*)*(?:pub\s+)?enum\s+(\w+)(?:<([^>]+)>)?\s*\{([^}]*)\}",
            re.MULTILINE | re.DOTALL,
        )
        for match in enum_pattern.finditer(source_code):
            line_num = source_code[: match.start()].count("\n") + 1
            attributes = match.group(1)
            name = match.group(2)
            generics = match.group(3)
            body = match.group(4)

            # Extract variants
            variant_pattern = re.compile(r"(\w+)(?:\([^)]*\)|\{[^}]*\})?")
            variants = [m.group(1) for m in variant_pattern.finditer(body)]

            entity = CodeEntity(
                name=name,
                entity_type="enum",
                language=self.language,
                file_path=file_path,
                line_number=line_num,
                type_parameters=generics.split(",") if generics else [],
                decorators=self._parse_rust_attributes(attributes),
                modifiers=["pub"] if "pub" in match.group(0) else [],
                metadata={"variants": variants},
            )
            entities.append(entity)

        # Extract traits
        trait_pattern = re.compile(
            r"(?:pub\s+)?trait\s+(\w+)(?:<([^>]+)>)?\s*(?::\s*([^{]+))?\s*\{([^}]*)\}",
            re.MULTILINE | re.DOTALL,
        )
        for match in trait_pattern.finditer(source_code):
            line_num = source_code[: match.start()].count("\n") + 1
            name = match.group(1)
            generics = match.group(2)
            bounds = match.group(3)
            body = match.group(4)

            # Extract method signatures
            method_pattern = re.compile(r"fn\s+(\w+)")
            methods = [m.group(1) for m in method_pattern.finditer(body)]

            entity = CodeEntity(
                name=name,
                entity_type="trait",
                language=self.language,
                file_path=file_path,
                line_number=line_num,
                type_parameters=generics.split(",") if generics else [],
                methods=methods,
                modifiers=["pub"] if "pub" in match.group(0) else [],
                metadata={"bounds": bounds.strip() if bounds else None},
            )
            entities.append(entity)

        # Extract impl blocks
        impl_pattern = re.compile(
            r"impl(?:<([^>]+)>)?\s+(?:(\w+)\s+for\s+)?(\w+)(?:<([^>]+)>)?\s*(?:where\s+([^{]+))?\s*\{",
            re.MULTILINE,
        )
        for match in impl_pattern.finditer(source_code):
            line_num = source_code[: match.start()].count("\n") + 1
            impl_generics = match.group(1)
            trait_name = match.group(2)
            type_name = match.group(3)
            type_generics = match.group(4)
            where_clause = match.group(5)

            entity = CodeEntity(
                name=f"impl {type_name}",
                entity_type="impl",
                language=self.language,
                file_path=file_path,
                line_number=line_num,
                parent=type_name,
                implements=[trait_name] if trait_name else [],
                type_parameters=impl_generics.split(",") if impl_generics else [],
                metadata={
                    "where_clause": where_clause.strip() if where_clause else None
                },
            )
            entities.append(entity)

        # Extract functions
        func_pattern = re.compile(
            r"(?:pub\s+)?(?:async\s+)?(?:unsafe\s+)?fn\s+(\w+)(?:<([^>]+)>)?\s*\(([^)]*)\)\s*(?:->\s*([^{;]+))?\s*[{;]",
            re.MULTILINE,
        )
        for match in func_pattern.finditer(source_code):
            line_num = source_code[: match.start()].count("\n") + 1
            name = match.group(1)
            generics = match.group(2)
            params = match.group(3)
            return_type = match.group(4)

            modifiers = []
            if "pub" in match.group(0):
                modifiers.append("pub")
            if "async" in match.group(0):
                modifiers.append("async")
            if "unsafe" in match.group(0):
                modifiers.append("unsafe")

            entity = CodeEntity(
                name=name,
                entity_type="function",
                language=self.language,
                file_path=file_path,
                line_number=line_num,
                signature=match.group(0).strip(),
                type_parameters=generics.split(",") if generics else [],
                parameters=self._parse_rust_parameters(params),
                return_type=return_type.strip() if return_type else None,
                modifiers=modifiers,
            )
            entities.append(entity)

        return entities

    def find_dependencies(
        self, source_code: str, file_path: str
    ) -> list[DependencyInfo]:
        """Find Rust use statements."""
        dependencies = []

        # use module::item
        use_pattern = re.compile(r"use\s+([\w:]+)(?:\s+as\s+(\w+))?;")
        for match in use_pattern.finditer(source_code):
            line_num = source_code[: match.start()].count("\n") + 1
            module = match.group(1)
            alias = match.group(2)

            dependencies.append(
                DependencyInfo(
                    module=module, alias=alias, line_number=line_num
                )
            )

        # use module::{item1, item2}
        use_group_pattern = re.compile(r"use\s+([\w:]+)::\{([^}]+)\};")
        for match in use_group_pattern.finditer(source_code):
            line_num = source_code[: match.start()].count("\n") + 1
            module = match.group(1)
            symbols = [s.strip() for s in match.group(2).split(",")]

            dependencies.append(
                DependencyInfo(
                    module=module, symbols=symbols, line_number=line_num
                )
            )

        return dependencies

    def get_call_graph(
        self, source_code: str, file_path: str
    ) -> dict[str, CallGraphNode]:
        """Build call graph for Rust."""
        call_graph = {}

        # Extract function bodies
        func_pattern = re.compile(
            r"fn\s+(\w+)(?:<[^>]+>)?\s*\([^)]*\)(?:\s*->\s*[^{]+)?\s*\{",
            re.MULTILINE,
        )

        for match in func_pattern.finditer(source_code):
            func_name = match.group(1)
            line_num = source_code[: match.start()].count("\n") + 1

            # Find function body
            start = match.end()
            brace_count = 1
            end = start

            for i in range(start, len(source_code)):
                if source_code[i] == "{":
                    brace_count += 1
                elif source_code[i] == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        end = i
                        break

            func_body = source_code[start:end]

            # Extract function calls
            call_pattern = re.compile(r"(\w+)(?:::\w+)*\s*\(")
            calls = list(
                set(
                    m.group(1)
                    for m in call_pattern.finditer(func_body)
                    if m.group(1) != func_name
                )
            )

            call_graph[func_name] = CallGraphNode(
                function=func_name,
                file_path=file_path,
                line_number=line_num,
                calls=calls,
            )

        return call_graph

    def _parse_rust_attributes(self, attrs: Optional[str]) -> list[str]:
        """Parse Rust attributes like #[derive(Debug, Clone)]."""
        if not attrs:
            return []

        # Extract attribute content
        result = []
        attr_pattern = re.compile(r"(\w+)(?:\([^)]+\))?")
        for match in attr_pattern.finditer(attrs):
            result.append(match.group(0))

        return result

    def _parse_rust_parameters(self, params_str: str) -> list[dict[str, Any]]:
        """Parse Rust function parameters."""
        if not params_str.strip():
            return []

        parameters = []
        # Rust params: name: type, &self, &mut self
        for param in params_str.split(","):
            param = param.strip()
            if not param:
                continue

            if param in ["&self", "&mut self", "self", "mut self"]:
                parameters.append({"name": "self", "type": param})
            else:
                match = re.match(r"(mut\s+)?(\w+)\s*:\s*(.+)", param)
                if match:
                    parameters.append(
                        {
                            "name": match.group(2),
                            "type": match.group(3).strip(),
                            "mutable": bool(match.group(1)),
                        }
                    )

        return parameters


# ===== Java Analyzer =====


class JavaAnalyzer(LanguageAnalyzer):
    """
    Analyzer for Java language.

    Extracts:
    - Classes, interfaces, enums
    - Methods and fields
    - Annotations
    - Package and import statements
    - Class hierarchy (extends/implements)
    - Visibility modifiers
    """

    def __init__(self):
        """Initialize Java analyzer."""
        super().__init__(Language.JAVA)

    def parse_file(self, file_path: str | Path) -> ParseResult:
        """Parse Java source file."""
        file_path = Path(file_path)
        try:
            source_code = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            return ParseResult(
                language=self.language,
                file_path=str(file_path),
                errors=[f"Failed to read file: {e}"],
            )

        entities = self.extract_entities(source_code, str(file_path))
        dependencies = self.find_dependencies(source_code, str(file_path))
        call_graph = self.get_call_graph(source_code, str(file_path))

        # Extract package name
        package_match = re.search(r"^\s*package\s+([\w.]+)\s*;", source_code, re.MULTILINE)
        package_name = package_match.group(1) if package_match else None

        return ParseResult(
            language=self.language,
            file_path=str(file_path),
            entities=entities,
            dependencies=dependencies,
            call_graph=call_graph,
            metadata={"package": package_name},
        )

    def extract_entities(self, source_code: str, file_path: str) -> list[CodeEntity]:
        """Extract entities from Java source."""
        entities = []

        # Extract classes
        class_pattern = re.compile(
            r"(?:(?:@\w+(?:\([^)]*\))?)\s*)*(?:(public|private|protected)\s+)?(?:(static|final|abstract)\s+)*class\s+(\w+)(?:<([^>]+)>)?(?:\s+extends\s+([\w.<>]+))?(?:\s+implements\s+([\w\s,.<>]+))?\s*\{",
            re.MULTILINE,
        )
        for match in class_pattern.finditer(source_code):
            line_num = source_code[: match.start()].count("\n") + 1
            visibility = match.group(1)
            modifier = match.group(2)
            name = match.group(3)
            generics = match.group(4)
            extends = match.group(5)
            implements = match.group(6)

            # Extract annotations before class
            annotations = self._extract_annotations_before(source_code, match.start())

            # Extract class body for methods and fields
            methods, fields = self._extract_class_members(
                source_code, match.end()
            )

            modifiers = []
            if visibility:
                modifiers.append(visibility)
            if modifier:
                modifiers.extend(modifier.split())

            entity = CodeEntity(
                name=name,
                entity_type="class",
                language=self.language,
                file_path=file_path,
                line_number=line_num,
                type_parameters=generics.split(",") if generics else [],
                extends=[extends] if extends else [],
                implements=implements.split(",") if implements else [],
                annotations=annotations,
                methods=methods,
                attributes=fields,
                modifiers=modifiers,
            )
            entities.append(entity)

        # Extract interfaces
        interface_pattern = re.compile(
            r"(?:(?:@\w+(?:\([^)]*\))?)\s*)*(?:(public|private|protected)\s+)?interface\s+(\w+)(?:<([^>]+)>)?(?:\s+extends\s+([\w\s,.<>]+))?\s*\{",
            re.MULTILINE,
        )
        for match in interface_pattern.finditer(source_code):
            line_num = source_code[: match.start()].count("\n") + 1
            visibility = match.group(1)
            name = match.group(2)
            generics = match.group(3)
            extends = match.group(4)

            annotations = self._extract_annotations_before(source_code, match.start())
            methods, _ = self._extract_class_members(source_code, match.end())

            entity = CodeEntity(
                name=name,
                entity_type="interface",
                language=self.language,
                file_path=file_path,
                line_number=line_num,
                type_parameters=generics.split(",") if generics else [],
                extends=extends.split(",") if extends else [],
                annotations=annotations,
                methods=methods,
                modifiers=[visibility] if visibility else [],
            )
            entities.append(entity)

        # Extract enums
        enum_pattern = re.compile(
            r"(?:(public|private|protected)\s+)?enum\s+(\w+)(?:\s+implements\s+([\w\s,.<>]+))?\s*\{",
            re.MULTILINE,
        )
        for match in enum_pattern.finditer(source_code):
            line_num = source_code[: match.start()].count("\n") + 1
            visibility = match.group(1)
            name = match.group(2)
            implements = match.group(3)

            entity = CodeEntity(
                name=name,
                entity_type="enum",
                language=self.language,
                file_path=file_path,
                line_number=line_num,
                implements=implements.split(",") if implements else [],
                modifiers=[visibility] if visibility else [],
            )
            entities.append(entity)

        # Extract standalone methods (rare, but possible in some contexts)
        method_pattern = re.compile(
            r"(?:(public|private|protected)\s+)?(?:(static|final|abstract|synchronized)\s+)*(?:<([^>]+)>\s+)?(\w+)\s+(\w+)\s*\(([^)]*)\)(?:\s+throws\s+([\w\s,]+))?\s*[{;]",
            re.MULTILINE,
        )
        for match in method_pattern.finditer(source_code):
            # Skip if inside a class (crude check)
            preceding = source_code[max(0, match.start() - 200) : match.start()]
            if "class " in preceding or "interface " in preceding:
                continue

            line_num = source_code[: match.start()].count("\n") + 1
            visibility = match.group(1)
            modifier = match.group(2)
            generics = match.group(3)
            return_type = match.group(4)
            name = match.group(5)
            params = match.group(6)
            throws = match.group(7)

            modifiers = []
            if visibility:
                modifiers.append(visibility)
            if modifier:
                modifiers.extend(modifier.split())

            entity = CodeEntity(
                name=name,
                entity_type="method",
                language=self.language,
                file_path=file_path,
                line_number=line_num,
                signature=match.group(0).strip(),
                type_parameters=generics.split(",") if generics else [],
                parameters=self._parse_java_parameters(params),
                return_type=return_type,
                modifiers=modifiers,
                metadata={"throws": throws.split(",") if throws else []},
            )
            entities.append(entity)

        return entities

    def find_dependencies(
        self, source_code: str, file_path: str
    ) -> list[DependencyInfo]:
        """Find Java imports."""
        dependencies = []

        # import package.Class
        import_pattern = re.compile(r"import\s+(?:static\s+)?([\w.]+)(?:\.\*)?;")
        for match in import_pattern.finditer(source_code):
            line_num = source_code[: match.start()].count("\n") + 1
            module = match.group(1)

            dependencies.append(
                DependencyInfo(
                    module=module,
                    line_number=line_num,
                    metadata={"static": "static" in match.group(0)},
                )
            )

        return dependencies

    def get_call_graph(
        self, source_code: str, file_path: str
    ) -> dict[str, CallGraphNode]:
        """Build call graph for Java."""
        call_graph = {}

        # Extract method bodies
        method_pattern = re.compile(
            r"(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\([^)]*\)\s*\{",
            re.MULTILINE,
        )

        for match in method_pattern.finditer(source_code):
            method_name = match.group(1)
            line_num = source_code[: match.start()].count("\n") + 1

            # Find method body
            start = match.end()
            brace_count = 1
            end = start

            for i in range(start, len(source_code)):
                if source_code[i] == "{":
                    brace_count += 1
                elif source_code[i] == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        end = i
                        break

            method_body = source_code[start:end]

            # Extract method calls
            call_pattern = re.compile(r"(\w+)\s*\(")
            calls = list(
                set(
                    m.group(1)
                    for m in call_pattern.finditer(method_body)
                    if m.group(1) != method_name
                )
            )

            call_graph[method_name] = CallGraphNode(
                function=method_name,
                file_path=file_path,
                line_number=line_num,
                calls=calls,
            )

        return call_graph

    def _extract_annotations_before(self, source_code: str, pos: int) -> list[str]:
        """Extract annotations before a position."""
        # Look back for annotations
        preceding = source_code[max(0, pos - 500) : pos]
        annotation_pattern = re.compile(r"@(\w+)(?:\([^)]*\))?")
        annotations = [m.group(0) for m in annotation_pattern.finditer(preceding)]
        return annotations

    def _extract_class_members(
        self, source_code: str, start_pos: int
    ) -> tuple[list[str], list[str]]:
        """Extract methods and fields from class body."""
        methods = []
        fields = []

        # Find class body
        brace_count = 1
        end_pos = start_pos

        for i in range(start_pos, len(source_code)):
            if source_code[i] == "{":
                brace_count += 1
            elif source_code[i] == "}":
                brace_count -= 1
                if brace_count == 0:
                    end_pos = i
                    break

        class_body = source_code[start_pos:end_pos]

        # Extract methods
        method_pattern = re.compile(
            r"(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\([^)]*\)\s*\{",
            re.MULTILINE,
        )
        methods = [m.group(1) for m in method_pattern.finditer(class_body)]

        # Extract fields
        field_pattern = re.compile(
            r"(?:public|private|protected)?\s*(?:static|final)?\s*\w+\s+(\w+)\s*[;=]",
            re.MULTILINE,
        )
        for match in field_pattern.finditer(class_body):
            # Skip if it looks like a method call
            if "(" not in class_body[match.start() : match.end() + 20]:
                fields.append(match.group(1))

        return methods, fields

    def _parse_java_parameters(self, params_str: str) -> list[dict[str, Any]]:
        """Parse Java method parameters."""
        if not params_str.strip():
            return []

        parameters = []
        # Java params: Type name, final Type name, Type... name
        for param in params_str.split(","):
            param = param.strip()
            if not param:
                continue

            # Remove final, annotations
            param = re.sub(r"@\w+(?:\([^)]*\))?\s*", "", param)
            param = re.sub(r"\bfinal\b\s*", "", param)

            parts = param.split()
            if len(parts) >= 2:
                param_type = " ".join(parts[:-1])
                param_name = parts[-1]
                parameters.append(
                    {
                        "name": param_name,
                        "type": param_type,
                        "varargs": "..." in param_type,
                    }
                )

        return parameters


# ===== Language Registry =====


class LanguageRegistry:
    """
    Registry for dynamic language analyzer loading.

    Allows registration and retrieval of language analyzers.
    Supports lazy initialization and caching.
    """

    def __init__(self):
        """Initialize language registry."""
        self._analyzers: dict[Language, LanguageAnalyzer] = {}
        self._factories: dict[Language, type[LanguageAnalyzer]] = {
            Language.TYPESCRIPT: TypeScriptAnalyzer,
            Language.JAVASCRIPT: TypeScriptAnalyzer,
            Language.TSX: TypeScriptAnalyzer,
            Language.JSX: TypeScriptAnalyzer,
            Language.GO: GoAnalyzer,
            Language.RUST: RustAnalyzer,
            Language.JAVA: JavaAnalyzer,
        }

    def register(
        self, language: Language, analyzer_class: type[LanguageAnalyzer]
    ) -> None:
        """
        Register a language analyzer.

        Args:
            language: Language to register
            analyzer_class: Analyzer class for this language
        """
        self._factories[language] = analyzer_class

        # Clear cached instance if exists
        if language in self._analyzers:
            del self._analyzers[language]

        logger.debug(f"Registered analyzer for {language.value}")

    def get_analyzer(self, language: Language) -> Optional[LanguageAnalyzer]:
        """
        Get analyzer for a language.

        Args:
            language: Language to get analyzer for

        Returns:
            Language analyzer instance or None if not supported
        """
        # Return cached instance
        if language in self._analyzers:
            return self._analyzers[language]

        # Create new instance
        if language in self._factories:
            factory = self._factories[language]
            analyzer = factory() if language != Language.TYPESCRIPT else factory(language)
            self._analyzers[language] = analyzer
            return analyzer

        logger.warning(f"No analyzer registered for {language.value}")
        return None

    def supports(self, language: Language) -> bool:
        """
        Check if language is supported.

        Args:
            language: Language to check

        Returns:
            True if language has registered analyzer
        """
        return language in self._factories

    def supported_languages(self) -> list[Language]:
        """Get list of supported languages."""
        return list(self._factories.keys())


# Global registry instance
_registry = LanguageRegistry()


# ===== Unified Analyzer =====


class UnifiedAnalyzer:
    """
    Unified analyzer that delegates to appropriate language analyzer.

    Provides a single interface for analyzing code across all languages.
    Automatically detects language and routes to correct analyzer.
    """

    def __init__(self, registry: Optional[LanguageRegistry] = None):
        """
        Initialize unified analyzer.

        Args:
            registry: Optional custom registry (uses global by default)
        """
        self.registry = registry or _registry

    def parse_file(self, file_path: str | Path) -> ParseResult:
        """
        Parse a file automatically detecting language.

        Args:
            file_path: Path to source file

        Returns:
            ParseResult with entities and dependencies
        """
        file_path = Path(file_path)
        language = detect_language(file_path)

        if language == Language.UNKNOWN:
            return ParseResult(
                language=language,
                file_path=str(file_path),
                errors=[f"Unknown language for file: {file_path}"],
            )

        analyzer = self.registry.get_analyzer(language)
        if not analyzer:
            return ParseResult(
                language=language,
                file_path=str(file_path),
                errors=[f"No analyzer available for {language.value}"],
            )

        return analyzer.parse_file(file_path)

    def analyze_directory(
        self, directory: str | Path, recursive: bool = True
    ) -> dict[str, ParseResult]:
        """
        Analyze all supported files in a directory.

        Args:
            directory: Directory to analyze
            recursive: Whether to recurse into subdirectories

        Returns:
            Dict mapping file paths to parse results
        """
        directory = Path(directory)
        results = {}

        # Collect all supported files
        pattern = "**/*" if recursive else "*"
        for file_path in directory.glob(pattern):
            if not file_path.is_file():
                continue

            language = detect_language(file_path)
            if language == Language.UNKNOWN or not self.registry.supports(language):
                continue

            try:
                result = self.parse_file(file_path)
                results[str(file_path)] = result
            except Exception as e:
                logger.error(f"Failed to analyze {file_path}: {e}")
                results[str(file_path)] = ParseResult(
                    language=language,
                    file_path=str(file_path),
                    errors=[str(e)],
                )

        return results

    def get_cross_language_dependencies(
        self, results: dict[str, ParseResult]
    ) -> dict[str, list[str]]:
        """
        Analyze cross-language dependencies.

        Args:
            results: Parse results from analyze_directory

        Returns:
            Dict mapping files to their dependencies
        """
        dependency_graph = {}

        for file_path, result in results.items():
            deps = []
            for dep in result.dependencies:
                # Try to resolve to actual file
                resolved = self._resolve_import(dep.module, file_path, results)
                if resolved:
                    deps.append(resolved)

            dependency_graph[file_path] = deps

        return dependency_graph

    def _resolve_import(
        self, module: str, from_file: str, results: dict[str, ParseResult]
    ) -> Optional[str]:
        """
        Attempt to resolve an import to a file path.

        This is a simple heuristic-based resolver. Production systems
        would need language-specific resolution logic.
        """
        from_path = Path(from_file).parent

        # Try relative import
        if module.startswith("."):
            # Convert import path to file path
            parts = module.lstrip(".").split(".")
            potential_files = [
                from_path / f"{'/'.join(parts)}.{ext}"
                for ext in ["ts", "js", "go", "rs", "java", "py"]
            ]

            for potential in potential_files:
                if str(potential) in results:
                    return str(potential)

        return None


# ===== Utility Functions =====


def detect_language(file_path: str | Path) -> Language:
    """
    Detect programming language from file path.

    Args:
        file_path: Path to source file

    Returns:
        Detected language
    """
    file_path = Path(file_path)
    extension = file_path.suffix

    # Try extension-based detection
    language = Language.from_extension(extension)
    if language != Language.UNKNOWN:
        return language

    # Try content-based detection for ambiguous cases
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        return detect_language_from_content(content)
    except Exception:
        return Language.UNKNOWN


def detect_language_from_content(content: str) -> Language:
    """
    Detect language from file content using heuristics.

    Args:
        content: Source code content

    Returns:
        Detected language
    """
    # Check for language-specific patterns
    if re.search(r"^\s*package\s+\w+\s*;", content, re.MULTILINE):
        # Could be Go or Java
        if "import (" in content or "func " in content:
            return Language.GO
        if "class " in content or "interface " in content:
            return Language.JAVA

    if re.search(r"^\s*use\s+[\w:]+;", content, re.MULTILINE):
        return Language.RUST

    if re.search(r"^\s*interface\s+\w+", content, re.MULTILINE) or "export " in content:
        return Language.TYPESCRIPT

    if re.search(r"^\s*def\s+\w+\s*\(", content, re.MULTILINE):
        return Language.PYTHON

    return Language.UNKNOWN


def get_analyzer(language: Language) -> Optional[LanguageAnalyzer]:
    """
    Get analyzer for a language (convenience function).

    Args:
        language: Language to get analyzer for

    Returns:
        Language analyzer instance or None
    """
    return _registry.get_analyzer(language)


def get_unified_analyzer() -> UnifiedAnalyzer:
    """Get global unified analyzer instance."""
    return UnifiedAnalyzer(_registry)
