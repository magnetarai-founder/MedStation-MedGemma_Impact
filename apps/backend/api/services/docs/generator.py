#!/usr/bin/env python3
"""
Documentation Generator

Intelligent auto-documentation system that:
1. Generates docstrings for undocumented code
2. Keeps documentation in sync with code changes
3. Detects stale documentation
4. Generates project-level documentation (README, API docs)
5. Supports multiple docstring styles
"""

import ast
import asyncio
import difflib
import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from api.services.ollama_client import get_ollama_client
from api.utils.structured_logging import get_logger

logger = get_logger(__name__)


class DocstringStyle(Enum):
    """Supported docstring styles."""

    GOOGLE = "google"  # Google style (default)
    NUMPY = "numpy"  # NumPy/SciPy style
    SPHINX = "sphinx"  # Sphinx/reStructuredText style


@dataclass
class DocumentationStatus:
    """Status of documentation for a file or entity."""

    file_path: str
    missing: list[str] = field(default_factory=list)  # Entities without docs
    stale: list[str] = field(default_factory=list)  # Entities with stale docs
    ok: list[str] = field(default_factory=list)  # Entities with good docs
    total_entities: int = 0
    coverage_percent: float = 0.0
    last_checked: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "missing": self.missing,
            "stale": self.stale,
            "ok": self.ok,
            "total_entities": self.total_entities,
            "coverage_percent": self.coverage_percent,
            "last_checked": self.last_checked,
        }


@dataclass
class CodeSignature:
    """Signature of code entity for change detection."""

    name: str
    entity_type: str  # "function", "class", "method"
    parameters: list[str]
    return_type: str | None
    decorators: list[str]
    body_hash: str  # Hash of function body
    docstring_hash: str | None  # Hash of current docstring

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CodeSignature):
            return False
        return (
            self.parameters == other.parameters
            and self.return_type == other.return_type
            and self.decorators == other.decorators
        )

    def has_changed(self, other: "CodeSignature") -> bool:
        """Check if code signature has changed significantly."""
        return (
            self.parameters != other.parameters
            or self.return_type != other.return_type
            or self.body_hash != other.body_hash
        )


@dataclass
class DocstringDiff:
    """Diff preview for docstring changes."""

    entity_name: str
    file_path: str
    old_docstring: str | None
    new_docstring: str
    diff_lines: list[str]
    action: str  # "add", "update", "none"

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_name": self.entity_name,
            "file_path": self.file_path,
            "old_docstring": self.old_docstring,
            "new_docstring": self.new_docstring,
            "diff": "\n".join(self.diff_lines),
            "action": self.action,
        }


class DocstringExtractor(ast.NodeVisitor):
    """Extract entities and their docstrings from Python code."""

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.source_lines = source_code.splitlines()
        self.entities: dict[str, dict[str, Any]] = {}
        self._current_class: str | None = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition."""
        docstring = ast.get_docstring(node)
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]
        bases = [self._get_name(base) for base in node.bases]

        self.entities[node.name] = {
            "type": "class",
            "name": node.name,
            "docstring": docstring,
            "line_number": node.lineno,
            "end_line": node.end_lineno,
            "decorators": decorators,
            "bases": bases,
            "signature": self._extract_signature(node),
            "body_hash": self._hash_body(node),
        }

        # Visit methods
        old_class = self._current_class
        self._current_class = node.name
        self.generic_visit(node)
        self._current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition."""
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition."""
        self._visit_function(node, is_async=True)

    def _visit_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool = False
    ) -> None:
        """Process function/method node."""
        docstring = ast.get_docstring(node)
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]

        # Get parameters with type hints
        params = []
        for arg in node.args.args:
            param_str = arg.arg
            if arg.annotation:
                param_str += f": {self._get_name(arg.annotation)}"
            params.append(param_str)

        # Get return type
        return_type = self._get_name(node.returns) if node.returns else None

        # Build full name (include class for methods)
        full_name = (
            f"{self._current_class}.{node.name}" if self._current_class else node.name
        )
        entity_type = "method" if self._current_class else "function"

        self.entities[full_name] = {
            "type": entity_type,
            "name": node.name,
            "full_name": full_name,
            "docstring": docstring,
            "line_number": node.lineno,
            "end_line": node.end_lineno,
            "decorators": decorators,
            "parameters": params,
            "return_type": return_type,
            "is_async": is_async,
            "parent_class": self._current_class,
            "signature": self._extract_signature(node),
            "body_hash": self._hash_body(node),
        }

        self.generic_visit(node)

    def _get_decorator_name(self, node: ast.expr) -> str:
        """Extract decorator name."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_decorator_name(node.func)
        return str(node)

    def _get_name(self, node: ast.expr | None) -> str:
        """Extract name from AST node."""
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

    def _extract_signature(self, node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        """Extract function/class signature from source."""
        try:
            start_line = node.lineno - 1
            # Find where the actual definition starts (skip decorators)
            for i, line in enumerate(self.source_lines[start_line:], start=start_line):
                if line.strip().startswith(("def ", "async def ", "class ")):
                    # Find the end of signature (look for ':')
                    signature_lines = []
                    for sig_line in self.source_lines[i:]:
                        signature_lines.append(sig_line)
                        if ":" in sig_line:
                            break
                    return "".join(signature_lines).strip()
        except Exception:
            pass
        return ""

    def _hash_body(self, node: ast.AST) -> str:
        """Hash the body of a function/class for change detection."""
        try:
            # Get body content (exclude docstring)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                body_nodes = node.body
                # Skip docstring if present
                if (
                    body_nodes
                    and isinstance(body_nodes[0], ast.Expr)
                    and isinstance(body_nodes[0].value, ast.Constant)
                ):
                    body_nodes = body_nodes[1:]

                # Create normalized representation
                body_repr = ast.dump(ast.Module(body=body_nodes, type_ignores=[]))
                return hashlib.sha256(body_repr.encode()).hexdigest()[:16]
        except Exception:
            pass
        return ""


class DocGenerator:
    """
    Intelligent documentation generator.

    Features:
    - Generate docstrings for undocumented code
    - Detect stale documentation
    - Update docstrings when code changes
    - Generate README from project structure
    - Generate API documentation
    - Support multiple docstring styles
    """

    def __init__(self, workspace_root: str | Path, model: str | None = None):
        """
        Initialize documentation generator.

        Args:
            workspace_root: Root directory of the project
            model: LLM model to use (defaults to Ollama default)
        """
        self.workspace_root = Path(workspace_root)
        self.model = model
        self.ollama_client = get_ollama_client()

        # Cache for code signatures (for change detection)
        self._signature_cache: dict[str, dict[str, CodeSignature]] = {}

    async def generate_docstring(
        self,
        file_path: str | Path,
        entity_name: str,
        style: DocstringStyle = DocstringStyle.GOOGLE,
        context: str | None = None,
    ) -> str:
        """
        Generate docstring for a specific entity.

        Args:
            file_path: Path to Python file
            entity_name: Name of function/class/method
            style: Docstring style to use
            context: Additional context for generation

        Returns:
            Generated docstring text

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If entity not found in file
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Parse file
        source_code = file_path.read_text()
        extractor = DocstringExtractor(source_code)
        tree = ast.parse(source_code)
        extractor.visit(tree)

        # Find entity
        entity = extractor.entities.get(entity_name)
        if not entity:
            raise ValueError(f"Entity '{entity_name}' not found in {file_path}")

        # Build prompt for LLM
        prompt = self._build_docstring_prompt(entity, style, context, source_code)

        # Generate using LLM
        try:
            response = await self.ollama_client.generate(
                prompt=prompt,
                model=self.model,
                temperature=0.3,  # Lower temperature for more consistent output
            )

            # Extract and clean docstring
            docstring = self._extract_docstring_from_response(response, style)
            return docstring

        except Exception as e:
            logger.error(f"Failed to generate docstring: {e}")
            # Fallback to basic template
            return self._generate_basic_docstring(entity, style)

    async def check_sync(
        self, file_path: str | Path, entity_name: str
    ) -> tuple[bool, str | None]:
        """
        Check if docstring is in sync with code.

        Args:
            file_path: Path to Python file
            entity_name: Name of function/class/method

        Returns:
            Tuple of (is_synced, reason_if_not_synced)
        """
        file_path = Path(file_path)
        source_code = file_path.read_text()
        extractor = DocstringExtractor(source_code)
        tree = ast.parse(source_code)
        extractor.visit(tree)

        entity = extractor.entities.get(entity_name)
        if not entity:
            return False, f"Entity '{entity_name}' not found"

        # Create current signature
        current_sig = CodeSignature(
            name=entity["name"],
            entity_type=entity["type"],
            parameters=entity.get("parameters", []),
            return_type=entity.get("return_type"),
            decorators=entity.get("decorators", []),
            body_hash=entity.get("body_hash", ""),
            docstring_hash=self._hash_string(entity.get("docstring") or ""),
        )

        # Check cached signature
        cache_key = str(file_path)
        if cache_key in self._signature_cache:
            cached_sig = self._signature_cache[cache_key].get(entity_name)
            if cached_sig:
                if current_sig.has_changed(cached_sig):
                    reasons = []
                    if current_sig.parameters != cached_sig.parameters:
                        reasons.append("parameters changed")
                    if current_sig.return_type != cached_sig.return_type:
                        reasons.append("return type changed")
                    if current_sig.body_hash != cached_sig.body_hash:
                        reasons.append("implementation changed")
                    return False, "; ".join(reasons)

        # Update cache
        if cache_key not in self._signature_cache:
            self._signature_cache[cache_key] = {}
        self._signature_cache[cache_key][entity_name] = current_sig

        # No cached version or no changes detected
        if not entity.get("docstring"):
            return False, "no docstring present"

        return True, None

    async def update_docstring(
        self,
        file_path: str | Path,
        entity_name: str,
        style: DocstringStyle = DocstringStyle.GOOGLE,
        preview: bool = True,
    ) -> DocstringDiff | None:
        """
        Update docstring for an entity.

        Args:
            file_path: Path to Python file
            entity_name: Name of function/class/method
            style: Docstring style to use
            preview: If True, return diff without applying

        Returns:
            DocstringDiff object if preview=True, None otherwise
        """
        file_path = Path(file_path)
        source_code = file_path.read_text()
        extractor = DocstringExtractor(source_code)
        tree = ast.parse(source_code)
        extractor.visit(tree)

        entity = extractor.entities.get(entity_name)
        if not entity:
            logger.warning(f"Entity '{entity_name}' not found in {file_path}")
            return None

        # Generate new docstring
        new_docstring = await self.generate_docstring(file_path, entity_name, style)
        old_docstring = entity.get("docstring")

        # Determine action
        action = "update" if old_docstring else "add"

        # Create diff
        old_lines = (old_docstring or "").splitlines() if old_docstring else []
        new_lines = new_docstring.splitlines()
        diff_lines = list(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=f"{file_path} (old)",
                tofile=f"{file_path} (new)",
                lineterm="",
            )
        )

        diff_obj = DocstringDiff(
            entity_name=entity_name,
            file_path=str(file_path),
            old_docstring=old_docstring,
            new_docstring=new_docstring,
            diff_lines=diff_lines,
            action=action,
        )

        if preview:
            return diff_obj

        # Apply the change
        await self._apply_docstring_change(file_path, entity, new_docstring, style)
        return None

    async def scan_documentation_health(
        self, include_patterns: list[str] | None = None, exclude_patterns: list[str] | None = None
    ) -> list[DocumentationStatus]:
        """
        Scan entire workspace for documentation health.

        Args:
            include_patterns: Glob patterns for files to include
            exclude_patterns: Glob patterns for files to exclude

        Returns:
            List of DocumentationStatus for each file
        """
        if include_patterns is None:
            include_patterns = ["**/*.py"]

        if exclude_patterns is None:
            exclude_patterns = [
                "**/venv/**",
                "**/.venv/**",
                "**/node_modules/**",
                "**/__pycache__/**",
                "**/.git/**",
                "**/tests/**",
                "**/test_*.py",
            ]

        results = []

        # Find all Python files
        for pattern in include_patterns:
            for file_path in self.workspace_root.glob(pattern):
                # Check exclusions
                if any(file_path.match(excl) for excl in exclude_patterns):
                    continue

                if not file_path.is_file():
                    continue

                try:
                    status = await self._check_file_documentation(file_path)
                    results.append(status)
                except Exception as e:
                    logger.warning(f"Failed to check {file_path}: {e}")

        return results

    async def generate_readme(
        self,
        output_path: str | Path | None = None,
        include_api_overview: bool = True,
        include_structure: bool = True,
    ) -> str:
        """
        Generate README.md from codebase structure.

        Args:
            output_path: Where to write README (if None, returns content)
            include_api_overview: Include API endpoints overview
            include_structure: Include project structure

        Returns:
            Generated README content
        """
        readme_parts = []

        # Header
        project_name = self.workspace_root.name
        readme_parts.append(f"# {project_name}\n")
        readme_parts.append(f"*Auto-generated documentation - {datetime.utcnow().strftime('%Y-%m-%d')}*\n")

        # Project structure
        if include_structure:
            readme_parts.append("\n## Project Structure\n")
            structure = await self._analyze_project_structure()
            readme_parts.append("```")
            readme_parts.append(structure)
            readme_parts.append("```\n")

        # API overview
        if include_api_overview:
            readme_parts.append("\n## API Overview\n")
            api_endpoints = await self._extract_api_endpoints()
            if api_endpoints:
                for endpoint in api_endpoints:
                    readme_parts.append(f"- **{endpoint['method']}** `{endpoint['path']}` - {endpoint['description']}")
            else:
                readme_parts.append("*No API endpoints found*")

        # Module overview
        readme_parts.append("\n## Modules\n")
        modules = await self._analyze_modules()
        for module in modules:
            readme_parts.append(f"\n### {module['name']}\n")
            if module.get("docstring"):
                readme_parts.append(f"{module['docstring']}\n")
            readme_parts.append(f"- **Functions**: {module['function_count']}")
            readme_parts.append(f"- **Classes**: {module['class_count']}")

        readme_content = "\n".join(readme_parts)

        # Write to file if requested
        if output_path:
            output_path = Path(output_path)
            output_path.write_text(readme_content)
            logger.info(f"Generated README at {output_path}")

        return readme_content

    async def generate_api_docs(
        self, output_dir: str | Path, format: str = "markdown"
    ) -> list[Path]:
        """
        Generate API documentation from endpoints.

        Args:
            output_dir: Directory to write documentation
            format: Output format ("markdown" or "html")

        Returns:
            List of generated file paths
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        generated_files = []

        # Extract API endpoints
        endpoints = await self._extract_api_endpoints()

        if not endpoints:
            logger.warning("No API endpoints found")
            return generated_files

        # Group by module
        by_module: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for endpoint in endpoints:
            by_module[endpoint["module"]].append(endpoint)

        # Generate documentation for each module
        for module_name, module_endpoints in by_module.items():
            doc_content = self._generate_module_api_doc(module_name, module_endpoints, format)

            # Write to file
            filename = f"{module_name.replace('.', '_')}_api.{format if format == 'markdown' else 'html'}"
            file_path = output_dir / filename
            file_path.write_text(doc_content)
            generated_files.append(file_path)

            logger.info(f"Generated API docs for {module_name} at {file_path}")

        # Generate index
        index_content = self._generate_api_index(by_module, format)
        index_path = output_dir / f"index.{format if format == 'markdown' else 'html'}"
        index_path.write_text(index_content)
        generated_files.append(index_path)

        return generated_files

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _build_docstring_prompt(
        self,
        entity: dict[str, Any],
        style: DocstringStyle,
        context: str | None,
        source_code: str,
    ) -> str:
        """Build prompt for LLM to generate docstring."""
        entity_type = entity["type"]
        entity_name = entity["name"]
        signature = entity.get("signature", "")

        # Build style guide
        style_guide = self._get_style_guide(style)

        # Build context
        context_parts = []
        if context:
            context_parts.append(f"Context: {context}")

        if entity.get("parameters"):
            context_parts.append(f"Parameters: {', '.join(entity['parameters'])}")

        if entity.get("return_type"):
            context_parts.append(f"Returns: {entity['return_type']}")

        # Extract function body for context
        body_preview = ""
        try:
            start_line = entity.get("line_number", 0)
            end_line = entity.get("end_line", start_line)
            if start_line and end_line:
                lines = source_code.splitlines()[start_line - 1 : end_line]
                body_preview = "\n".join(lines[:20])  # First 20 lines
        except Exception:
            pass

        prompt = f"""Generate a {style.value} style docstring for this Python {entity_type}.

{entity_type.capitalize()}: {entity_name}
Signature: {signature}

{chr(10).join(context_parts)}

Code Preview:
```python
{body_preview}
```

Style Guide:
{style_guide}

Generate ONLY the docstring text (without triple quotes). The docstring should:
1. Clearly describe what the {entity_type} does
2. Document all parameters with types and descriptions
3. Document return value (if applicable)
4. Include any important notes or warnings
5. Be concise but complete

Docstring:"""

        return prompt

    def _get_style_guide(self, style: DocstringStyle) -> str:
        """Get docstring style guide."""
        if style == DocstringStyle.GOOGLE:
            return """Google Style:
    Brief description.

    Longer description if needed.

    Args:
        param_name (type): Description.
        another_param (type): Description.

    Returns:
        type: Description.

    Raises:
        ErrorType: Description.

    Example:
        >>> example_usage()
"""

        elif style == DocstringStyle.NUMPY:
            return """NumPy Style:
    Brief description.

    Longer description if needed.

    Parameters
    ----------
    param_name : type
        Description.
    another_param : type
        Description.

    Returns
    -------
    type
        Description.

    Raises
    ------
    ErrorType
        Description.

    Examples
    --------
    >>> example_usage()
"""

        elif style == DocstringStyle.SPHINX:
            return """Sphinx Style:
    Brief description.

    Longer description if needed.

    :param param_name: Description.
    :type param_name: type
    :param another_param: Description.
    :type another_param: type
    :return: Description.
    :rtype: type
    :raises ErrorType: Description.

    Example::

        example_usage()
"""

        return ""

    def _extract_docstring_from_response(self, response: str, style: DocstringStyle) -> str:
        """Extract and clean docstring from LLM response."""
        # Remove any code blocks
        response = re.sub(r"```[a-z]*\n?", "", response)
        response = response.strip()

        # Remove any "Docstring:" prefix
        response = re.sub(r"^Docstring:\s*", "", response, flags=re.IGNORECASE)

        # Clean up
        lines = response.splitlines()
        # Remove empty leading/trailing lines
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()

        return "\n".join(lines)

    def _generate_basic_docstring(self, entity: dict[str, Any], style: DocstringStyle) -> str:
        """Generate basic docstring as fallback."""
        entity_type = entity["type"]
        entity_name = entity["name"]

        if style == DocstringStyle.GOOGLE:
            parts = [f"{entity_name.replace('_', ' ').title()}."]

            if entity.get("parameters"):
                parts.append("\nArgs:")
                for param in entity["parameters"]:
                    parts.append(f"    {param}: Description.")

            if entity.get("return_type"):
                parts.append(f"\nReturns:")
                parts.append(f"    {entity['return_type']}: Description.")

            return "\n".join(parts)

        # Similar for other styles...
        return f"{entity_name.replace('_', ' ').title()}."

    def _hash_string(self, s: str) -> str:
        """Hash a string."""
        return hashlib.sha256(s.encode()).hexdigest()[:16]

    async def _check_file_documentation(self, file_path: Path) -> DocumentationStatus:
        """Check documentation status for a file."""
        try:
            source_code = file_path.read_text()
            extractor = DocstringExtractor(source_code)
            tree = ast.parse(source_code)
            extractor.visit(tree)

            missing = []
            stale = []
            ok = []

            for entity_name, entity in extractor.entities.items():
                # Skip private entities (starting with _)
                if entity["name"].startswith("_") and not entity["name"].startswith("__"):
                    continue

                # Check if documented
                if not entity.get("docstring"):
                    missing.append(entity_name)
                else:
                    # Check if stale
                    is_synced, _ = await self.check_sync(file_path, entity_name)
                    if not is_synced:
                        stale.append(entity_name)
                    else:
                        ok.append(entity_name)

            total = len(missing) + len(stale) + len(ok)
            coverage = (len(ok) / total * 100) if total > 0 else 0.0

            return DocumentationStatus(
                file_path=str(file_path.relative_to(self.workspace_root)),
                missing=missing,
                stale=stale,
                ok=ok,
                total_entities=total,
                coverage_percent=round(coverage, 2),
            )

        except Exception as e:
            logger.error(f"Error checking {file_path}: {e}")
            return DocumentationStatus(
                file_path=str(file_path.relative_to(self.workspace_root)),
                total_entities=0,
            )

    async def _apply_docstring_change(
        self,
        file_path: Path,
        entity: dict[str, Any],
        new_docstring: str,
        style: DocstringStyle,
    ) -> None:
        """Apply docstring change to file."""
        source_code = file_path.read_text()
        source_lines = source_code.splitlines(keepends=True)

        # Find insertion point
        line_number = entity["line_number"]
        entity_type = entity["type"]

        # Find the line after the def/class line
        def_line_idx = line_number - 1
        for i in range(def_line_idx, len(source_lines)):
            if ":" in source_lines[i]:
                insert_line = i + 1
                break
        else:
            logger.error(f"Could not find insertion point in {file_path}")
            return

        # Get indentation
        indent = self._get_indent(source_lines[def_line_idx])
        doc_indent = indent + "    "

        # Format docstring
        formatted_docstring = self._format_docstring(new_docstring, doc_indent)

        # Remove old docstring if exists
        if entity.get("docstring"):
            # Find and remove old docstring
            in_docstring = False
            quote_style = None
            lines_to_remove = []

            for i in range(insert_line, len(source_lines)):
                line = source_lines[i]
                stripped = line.strip()

                if not in_docstring:
                    if stripped.startswith('"""') or stripped.startswith("'''"):
                        in_docstring = True
                        quote_style = stripped[:3]
                        lines_to_remove.append(i)
                        if stripped.count(quote_style) >= 2:  # Single-line docstring
                            break
                else:
                    lines_to_remove.append(i)
                    if quote_style in line:
                        break

            # Remove in reverse to preserve indices
            for i in reversed(lines_to_remove):
                source_lines.pop(i)

        # Insert new docstring
        source_lines.insert(insert_line, formatted_docstring)

        # Write back
        file_path.write_text("".join(source_lines))
        logger.info(f"Updated docstring for {entity['name']} in {file_path}")

    def _get_indent(self, line: str) -> str:
        """Get indentation from a line."""
        return line[: len(line) - len(line.lstrip())]

    def _format_docstring(self, docstring: str, indent: str) -> str:
        """Format docstring with proper indentation."""
        lines = docstring.splitlines()
        formatted_lines = [f'{indent}"""\n']

        for line in lines:
            if line.strip():
                formatted_lines.append(f"{indent}{line}\n")
            else:
                formatted_lines.append("\n")

        formatted_lines.append(f'{indent}"""\n')
        return "".join(formatted_lines)

    async def _analyze_project_structure(self) -> str:
        """Analyze and format project structure."""
        structure_lines = []

        def build_tree(path: Path, prefix: str = "", is_last: bool = True) -> None:
            # Skip common directories
            if path.name in {
                "__pycache__",
                ".git",
                "node_modules",
                ".venv",
                "venv",
            }:
                return

            connector = "└── " if is_last else "├── "
            structure_lines.append(f"{prefix}{connector}{path.name}")

            if path.is_dir():
                children = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
                # Limit depth and breadth
                children = children[:20]  # Max 20 items per directory

                extension = "    " if is_last else "│   "
                for i, child in enumerate(children):
                    is_last_child = i == len(children) - 1
                    build_tree(child, prefix + extension, is_last_child)

        structure_lines.append(self.workspace_root.name)
        children = sorted(self.workspace_root.iterdir(), key=lambda x: (not x.is_dir(), x.name))
        for i, child in enumerate(children[:20]):
            build_tree(child, "", i == len(children) - 1)

        return "\n".join(structure_lines)

    async def _extract_api_endpoints(self) -> list[dict[str, Any]]:
        """Extract API endpoints from code."""
        endpoints = []

        # Look for FastAPI/Flask route decorators
        for py_file in self.workspace_root.rglob("*.py"):
            if "__pycache__" in str(py_file) or "venv" in str(py_file):
                continue

            try:
                source_code = py_file.read_text()
                tree = ast.parse(source_code)

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Check decorators for routes
                        for decorator in node.decorator_list:
                            endpoint_info = self._extract_endpoint_info(decorator, node, py_file)
                            if endpoint_info:
                                endpoints.append(endpoint_info)

            except Exception as e:
                logger.debug(f"Could not parse {py_file}: {e}")

        return endpoints

    def _extract_endpoint_info(
        self, decorator: ast.expr, func: ast.FunctionDef, file_path: Path
    ) -> dict[str, Any] | None:
        """Extract endpoint information from decorator."""
        # Handle @app.get("/path"), @router.post("/path"), etc.
        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
            method = decorator.func.attr.upper()
            if method in {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"}:
                # Extract path
                path = "/"
                if decorator.args and isinstance(decorator.args[0], ast.Constant):
                    path = decorator.args[0].value

                # Get docstring
                docstring = ast.get_docstring(func) or "No description"

                return {
                    "method": method,
                    "path": path,
                    "function": func.name,
                    "description": docstring.split("\n")[0],  # First line
                    "module": str(file_path.relative_to(self.workspace_root)),
                    "file": str(file_path),
                }

        return None

    async def _analyze_modules(self) -> list[dict[str, Any]]:
        """Analyze Python modules in project."""
        modules = []

        for py_file in self.workspace_root.rglob("*.py"):
            if "__pycache__" in str(py_file) or "venv" in str(py_file):
                continue

            try:
                source_code = py_file.read_text()
                extractor = DocstringExtractor(source_code)
                tree = ast.parse(source_code)
                extractor.visit(tree)

                # Count entities
                function_count = sum(
                    1 for e in extractor.entities.values() if e["type"] == "function"
                )
                class_count = sum(1 for e in extractor.entities.values() if e["type"] == "class")

                # Get module docstring
                module_docstring = ast.get_docstring(tree)

                modules.append(
                    {
                        "name": str(py_file.relative_to(self.workspace_root)),
                        "docstring": module_docstring,
                        "function_count": function_count,
                        "class_count": class_count,
                    }
                )

            except Exception as e:
                logger.debug(f"Could not analyze {py_file}: {e}")

        return modules

    def _generate_module_api_doc(
        self, module_name: str, endpoints: list[dict[str, Any]], format: str
    ) -> str:
        """Generate API documentation for a module."""
        if format == "markdown":
            lines = [
                f"# {module_name} API\n",
                f"*Auto-generated - {datetime.utcnow().strftime('%Y-%m-%d')}*\n",
                "\n## Endpoints\n",
            ]

            for endpoint in endpoints:
                lines.append(f"\n### {endpoint['method']} {endpoint['path']}\n")
                lines.append(f"**Function**: `{endpoint['function']}`\n")
                lines.append(f"{endpoint['description']}\n")
                lines.append(f"**File**: `{endpoint['module']}`\n")

            return "\n".join(lines)

        # HTML format
        return f"<html><body><h1>{module_name} API</h1></body></html>"

    def _generate_api_index(
        self, modules: dict[str, list[dict[str, Any]]], format: str
    ) -> str:
        """Generate index of all API documentation."""
        if format == "markdown":
            lines = [
                "# API Documentation Index\n",
                f"*Auto-generated - {datetime.utcnow().strftime('%Y-%m-%d')}*\n",
                "\n## Modules\n",
            ]

            for module_name, endpoints in modules.items():
                lines.append(f"\n### [{module_name}]({module_name.replace('.', '_')}_api.md)")
                lines.append(f"\n**Endpoints**: {len(endpoints)}\n")

            return "\n".join(lines)

        return "<html><body><h1>API Index</h1></body></html>"


# Global instance
_doc_generator: DocGenerator | None = None


def get_doc_generator(workspace_root: str | Path | None = None) -> DocGenerator:
    """Get or create global documentation generator."""
    global _doc_generator

    if _doc_generator is None:
        if workspace_root is None:
            workspace_root = Path.cwd()
        _doc_generator = DocGenerator(workspace_root)

    return _doc_generator
