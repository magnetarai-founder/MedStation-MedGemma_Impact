# Multi-Language Analyzer - Advanced Examples

Real-world usage examples for the multi-language code analysis system.

## Example 1: Code Navigation Service

Build a code navigation service that works across all languages:

```python
from api.services.languages import get_unified_analyzer, Language
from pathlib import Path

class CodeNavigator:
    """Cross-language code navigation."""

    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.analyzer = get_unified_analyzer()
        self.index = {}
        self.call_graph = {}

    async def build_index(self):
        """Build navigation index for workspace."""
        results = self.analyzer.analyze_directory(self.workspace_root)

        for file_path, result in results.items():
            # Index entities by name
            for entity in result.entities:
                if entity.name not in self.index:
                    self.index[entity.name] = []

                self.index[entity.name].append({
                    "file": file_path,
                    "line": entity.line_number,
                    "type": entity.entity_type,
                    "language": result.language.value,
                    "signature": entity.signature,
                })

            # Build call graph
            for func_name, node in result.call_graph.items():
                if func_name not in self.call_graph:
                    self.call_graph[func_name] = []

                for called_func in node.calls:
                    self.call_graph[func_name].append({
                        "callee": called_func,
                        "file": file_path,
                        "line": node.line_number,
                    })

    def goto_definition(self, symbol: str) -> list[dict]:
        """Find definition of a symbol."""
        return self.index.get(symbol, [])

    def find_references(self, symbol: str) -> list[dict]:
        """Find all references to a symbol."""
        references = []

        # Find in call graph
        for caller, calls in self.call_graph.items():
            for call in calls:
                if call["callee"] == symbol:
                    references.append({
                        "caller": caller,
                        "file": call["file"],
                        "line": call["line"],
                    })

        return references

    def find_implementations(self, interface: str) -> list[dict]:
        """Find all implementations of an interface."""
        implementations = []

        for symbols in self.index.values():
            for symbol in symbols:
                entity_file = symbol["file"]
                result = self.analyzer.parse_file(entity_file)

                for entity in result.entities:
                    if interface in entity.implements:
                        implementations.append({
                            "name": entity.name,
                            "file": entity_file,
                            "line": entity.line_number,
                            "language": result.language.value,
                        })

        return implementations

# Usage
navigator = CodeNavigator("/path/to/workspace")
await navigator.build_index()

# Go to definition
definitions = navigator.goto_definition("UserService")
for d in definitions:
    print(f"{d['type']} in {d['file']}:{d['line']} ({d['language']})")

# Find references
references = navigator.find_references("createUser")
for ref in references:
    print(f"Called by {ref['caller']} in {ref['file']}:{ref['line']}")

# Find implementations
impls = navigator.find_implementations("Repository")
for impl in impls:
    print(f"{impl['name']} implements Repository ({impl['language']})")
```

## Example 2: Dependency Graph Visualization

Visualize dependencies across languages:

```python
from api.services.languages import get_unified_analyzer
import json

class DependencyGraphBuilder:
    """Build dependency graph for visualization."""

    def __init__(self, workspace_root: str):
        self.analyzer = get_unified_analyzer()
        self.workspace_root = workspace_root

    def build_graph(self) -> dict:
        """Build dependency graph."""
        results = self.analyzer.analyze_directory(self.workspace_root)

        nodes = []
        edges = []

        # Create nodes for each file
        for file_path, result in results.items():
            nodes.append({
                "id": file_path,
                "label": Path(file_path).name,
                "language": result.language.value,
                "entities": len(result.entities),
                "type": "file",
            })

            # Add entity nodes
            for entity in result.entities:
                entity_id = f"{file_path}:{entity.name}"
                nodes.append({
                    "id": entity_id,
                    "label": entity.name,
                    "type": entity.entity_type,
                    "language": result.language.value,
                    "parent": file_path,
                })

            # Add dependency edges
            for dep in result.dependencies:
                edges.append({
                    "source": file_path,
                    "target": dep.module,
                    "type": "import",
                })

            # Add call graph edges
            for func_name, node in result.call_graph.items():
                func_id = f"{file_path}:{func_name}"
                for called in node.calls:
                    edges.append({
                        "source": func_id,
                        "target": called,
                        "type": "calls",
                    })

        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_files": len(results),
                "languages": list(set(n["language"] for n in nodes if "language" in n)),
            },
        }

    def export_graphviz(self) -> str:
        """Export as Graphviz DOT format."""
        graph = self.build_graph()

        dot = ["digraph Dependencies {"]
        dot.append("  rankdir=LR;")
        dot.append("  node [shape=box];")

        # Add nodes
        for node in graph["nodes"]:
            if node["type"] == "file":
                dot.append(f'  "{node["id"]}" [label="{node["label"]}", color=blue];')

        # Add edges
        for edge in graph["edges"]:
            if edge["type"] == "import":
                dot.append(f'  "{edge["source"]}" -> "{edge["target"]}";')

        dot.append("}")
        return "\n".join(dot)

# Usage
builder = DependencyGraphBuilder("/path/to/workspace")
graph = builder.build_graph()

# Save as JSON for D3.js visualization
with open("dependency-graph.json", "w") as f:
    json.dump(graph, f, indent=2)

# Or export as Graphviz
with open("dependencies.dot", "w") as f:
    f.write(builder.export_graphviz())
```

## Example 3: Code Metrics Dashboard

Generate code metrics across languages:

```python
from api.services.languages import get_unified_analyzer
from collections import defaultdict

class CodeMetrics:
    """Calculate code metrics across languages."""

    def __init__(self, workspace_root: str):
        self.analyzer = get_unified_analyzer()
        self.workspace_root = workspace_root

    def calculate_metrics(self) -> dict:
        """Calculate comprehensive metrics."""
        results = self.analyzer.analyze_directory(self.workspace_root)

        metrics = {
            "files": defaultdict(int),
            "entities": defaultdict(lambda: defaultdict(int)),
            "complexity": defaultdict(list),
            "dependencies": defaultdict(int),
            "largest_files": [],
        }

        for file_path, result in results.items():
            lang = result.language.value

            # File count by language
            metrics["files"][lang] += 1

            # Entity counts by type and language
            for entity in result.entities:
                metrics["entities"][lang][entity.entity_type] += 1

                # Complexity (rough estimate based on call graph)
                if entity.name in result.call_graph:
                    calls = len(result.call_graph[entity.name].calls)
                    metrics["complexity"][lang].append(calls)

            # Dependency counts
            metrics["dependencies"][lang] += len(result.dependencies)

            # Track largest files
            metrics["largest_files"].append({
                "file": file_path,
                "language": lang,
                "entities": len(result.entities),
                "dependencies": len(result.dependencies),
            })

        # Sort largest files
        metrics["largest_files"].sort(key=lambda x: x["entities"], reverse=True)
        metrics["largest_files"] = metrics["largest_files"][:10]

        # Calculate averages
        metrics["averages"] = {}
        for lang, complexities in metrics["complexity"].items():
            if complexities:
                metrics["averages"][lang] = {
                    "avg_complexity": sum(complexities) / len(complexities),
                    "max_complexity": max(complexities),
                }

        return dict(metrics)

    def generate_report(self) -> str:
        """Generate human-readable report."""
        metrics = self.calculate_metrics()

        lines = ["# Code Metrics Report\n"]

        # Files by language
        lines.append("## Files by Language")
        for lang, count in sorted(metrics["files"].items(), key=lambda x: x[1], reverse=True):
            lines.append(f"- {lang}: {count} files")

        # Entities by language
        lines.append("\n## Entities by Language")
        for lang, entities in metrics["entities"].items():
            lines.append(f"\n### {lang}")
            for entity_type, count in sorted(entities.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"- {entity_type}: {count}")

        # Complexity
        lines.append("\n## Average Complexity")
        for lang, stats in metrics["averages"].items():
            lines.append(
                f"- {lang}: avg={stats['avg_complexity']:.1f}, "
                f"max={stats['max_complexity']}"
            )

        # Largest files
        lines.append("\n## Largest Files (by entity count)")
        for file_info in metrics["largest_files"]:
            lines.append(
                f"- {file_info['file']}: {file_info['entities']} entities "
                f"({file_info['language']})"
            )

        return "\n".join(lines)

# Usage
metrics = CodeMetrics("/path/to/workspace")
report = metrics.generate_report()
print(report)

# Save report
with open("code-metrics.md", "w") as f:
    f.write(report)
```

## Example 4: API Documentation Generator

Generate API documentation from code:

```python
from api.services.languages import get_unified_analyzer, Language
from pathlib import Path

class APIDocGenerator:
    """Generate API documentation from code."""

    def __init__(self):
        self.analyzer = get_unified_analyzer()

    def generate_for_file(self, file_path: str) -> str:
        """Generate documentation for a file."""
        result = self.analyzer.parse_file(file_path)

        doc_lines = [f"# {Path(file_path).name}\n"]
        doc_lines.append(f"**Language:** {result.language.value}\n")

        # Group entities by type
        by_type = defaultdict(list)
        for entity in result.entities:
            by_type[entity.entity_type].append(entity)

        # Document classes/interfaces
        for entity_type in ["class", "interface", "struct"]:
            if entity_type in by_type:
                doc_lines.append(f"\n## {entity_type.title()}es\n")

                for entity in by_type[entity_type]:
                    doc_lines.append(f"### `{entity.name}`\n")

                    if entity.docstring:
                        doc_lines.append(f"{entity.docstring}\n")

                    if entity.signature:
                        doc_lines.append(f"```{result.language.value}")
                        doc_lines.append(entity.signature)
                        doc_lines.append("```\n")

                    if entity.extends:
                        doc_lines.append(f"**Extends:** {', '.join(entity.extends)}\n")

                    if entity.implements:
                        doc_lines.append(f"**Implements:** {', '.join(entity.implements)}\n")

                    if entity.methods:
                        doc_lines.append("**Methods:**")
                        for method in entity.methods:
                            doc_lines.append(f"- `{method}`")
                        doc_lines.append("")

        # Document functions
        if "function" in by_type or "method" in by_type:
            doc_lines.append("\n## Functions\n")

            all_functions = by_type.get("function", []) + by_type.get("method", [])
            for entity in all_functions:
                doc_lines.append(f"### `{entity.name}`\n")

                if entity.docstring:
                    doc_lines.append(f"{entity.docstring}\n")

                if entity.signature:
                    doc_lines.append(f"```{result.language.value}")
                    doc_lines.append(entity.signature)
                    doc_lines.append("```\n")

                if entity.parameters:
                    doc_lines.append("**Parameters:**")
                    for param in entity.parameters:
                        param_doc = f"- `{param['name']}`"
                        if param.get("type"):
                            param_doc += f": `{param['type']}`"
                        if param.get("default"):
                            param_doc += f" = `{param['default']}`"
                        doc_lines.append(param_doc)
                    doc_lines.append("")

                if entity.return_type:
                    doc_lines.append(f"**Returns:** `{entity.return_type}`\n")

        return "\n".join(doc_lines)

    def generate_for_directory(self, directory: str) -> dict[str, str]:
        """Generate documentation for all files in directory."""
        results = self.analyzer.analyze_directory(directory)

        docs = {}
        for file_path in results.keys():
            docs[file_path] = self.generate_for_file(file_path)

        return docs

# Usage
generator = APIDocGenerator()

# Single file
doc = generator.generate_for_file("src/UserService.ts")
print(doc)

# Entire directory
docs = generator.generate_for_directory("src/")
for file_path, doc_content in docs.items():
    output_path = f"docs/{Path(file_path).stem}.md"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(doc_content)
```

## Example 5: Code Migration Assistant

Assist with code migration between languages:

```python
from api.services.languages import get_unified_analyzer, Language

class MigrationAssistant:
    """Assist with code migration between languages."""

    def __init__(self):
        self.analyzer = get_unified_analyzer()

    def analyze_for_migration(self, source_file: str, target_language: Language):
        """Analyze source file for migration to target language."""
        result = self.analyzer.parse_file(source_file)

        migration_plan = {
            "source_language": result.language.value,
            "target_language": target_language.value,
            "entities": [],
            "challenges": [],
            "suggestions": [],
        }

        for entity in result.entities:
            entity_plan = {
                "name": entity.name,
                "type": entity.entity_type,
                "complexity": self._estimate_complexity(entity),
            }

            # Language-specific migration notes
            if result.language == Language.TYPESCRIPT and target_language == Language.GO:
                entity_plan["notes"] = self._typescript_to_go_notes(entity)
            elif result.language == Language.PYTHON and target_language == Language.RUST:
                entity_plan["notes"] = self._python_to_rust_notes(entity)

            migration_plan["entities"].append(entity_plan)

        # Identify challenges
        if result.language == Language.JAVASCRIPT and target_language == Language.RUST:
            migration_plan["challenges"].append("Dynamic typing -> Static typing")
            migration_plan["challenges"].append("Prototype-based -> Trait-based")

        return migration_plan

    def _estimate_complexity(self, entity) -> str:
        """Estimate migration complexity."""
        if entity.entity_type in ["function", "method"]:
            param_count = len(entity.parameters)
            if param_count > 5:
                return "high"
            elif param_count > 2:
                return "medium"
        return "low"

    def _typescript_to_go_notes(self, entity) -> list[str]:
        """TypeScript to Go migration notes."""
        notes = []

        if entity.entity_type == "interface":
            notes.append("Convert to Go interface with method signatures")

        if entity.entity_type == "class":
            notes.append("Convert to struct + methods with receiver")

        if entity.type_parameters:
            notes.append("Go 1.18+ generics available, but consider alternatives")

        return notes

    def _python_to_rust_notes(self, entity) -> list[str]:
        """Python to Rust migration notes."""
        notes = []

        if entity.entity_type == "class":
            notes.append("Convert to struct + impl block")

        if "async" in entity.modifiers:
            notes.append("Use async/await with tokio runtime")

        notes.append("Add explicit error handling with Result<T, E>")
        notes.append("Consider ownership and borrowing rules")

        return notes

# Usage
assistant = MigrationAssistant()

# Analyze TypeScript for Go migration
plan = assistant.analyze_for_migration("UserService.ts", Language.GO)

print(f"Migrating from {plan['source_language']} to {plan['target_language']}")
print(f"\nEntities to migrate: {len(plan['entities'])}")
for entity in plan['entities']:
    print(f"- {entity['type']} {entity['name']} (complexity: {entity['complexity']})")
    if entity.get('notes'):
        for note in entity['notes']:
            print(f"  • {note}")

print(f"\nChallenges:")
for challenge in plan['challenges']:
    print(f"- {challenge}")
```

## Example 6: Test Coverage Analyzer

Analyze test coverage across languages:

```python
from api.services.languages import get_unified_analyzer
from pathlib import Path

class TestCoverageAnalyzer:
    """Analyze test coverage across languages."""

    def __init__(self, workspace_root: str):
        self.analyzer = get_unified_analyzer()
        self.workspace_root = Path(workspace_root)

    def analyze_coverage(self) -> dict:
        """Analyze test coverage."""
        results = self.analyzer.analyze_directory(self.workspace_root)

        # Separate test files from source files
        test_files = {}
        source_files = {}

        for file_path, result in results.items():
            path = Path(file_path)
            is_test = self._is_test_file(path, result.language)

            if is_test:
                test_files[file_path] = result
            else:
                source_files[file_path] = result

        # Build coverage map
        coverage = {
            "total_source_files": len(source_files),
            "total_test_files": len(test_files),
            "by_language": {},
            "untested_entities": [],
        }

        for file_path, result in source_files.items():
            lang = result.language.value

            if lang not in coverage["by_language"]:
                coverage["by_language"][lang] = {
                    "source_files": 0,
                    "test_files": 0,
                    "source_entities": 0,
                    "tested_entities": 0,
                }

            coverage["by_language"][lang]["source_files"] += 1
            coverage["by_language"][lang]["source_entities"] += len(result.entities)

            # Check if entities are tested
            for entity in result.entities:
                if not self._has_test(entity, test_files):
                    coverage["untested_entities"].append({
                        "file": file_path,
                        "entity": entity.name,
                        "type": entity.entity_type,
                    })

        # Count test files per language
        for file_path, result in test_files.items():
            lang = result.language.value
            if lang in coverage["by_language"]:
                coverage["by_language"][lang]["test_files"] += 1

        return coverage

    def _is_test_file(self, path: Path, language: Language) -> bool:
        """Check if file is a test file."""
        name = path.name.lower()
        stem = path.stem.lower()

        # Common test patterns
        if language == Language.GO:
            return name.endswith("_test.go")
        elif language.is_typescript_family():
            return "test" in stem or "spec" in stem
        elif language == Language.RUST:
            return "test" in name or path.parts[-2] == "tests"
        elif language == Language.JAVA:
            return "test" in name.lower()

        return False

    def _has_test(self, entity, test_files: dict) -> bool:
        """Check if entity has a test."""
        entity_name = entity.name.lower()

        for test_file, result in test_files.items():
            for test_entity in result.entities:
                test_name = test_entity.name.lower()

                # Common test naming patterns
                if (
                    entity_name in test_name
                    or f"test_{entity_name}" == test_name
                    or f"test{entity_name}" == test_name
                    or f"{entity_name}_test" == test_name
                ):
                    return True

        return False

    def generate_report(self) -> str:
        """Generate coverage report."""
        coverage = self.analyze_coverage()

        lines = ["# Test Coverage Report\n"]

        lines.append(f"Total source files: {coverage['total_source_files']}")
        lines.append(f"Total test files: {coverage['total_test_files']}")
        lines.append("")

        for lang, stats in coverage["by_language"].items():
            lines.append(f"## {lang.title()}")
            lines.append(f"- Source files: {stats['source_files']}")
            lines.append(f"- Test files: {stats['test_files']}")
            lines.append(f"- Source entities: {stats['source_entities']}")

            test_ratio = (
                (stats['test_files'] / stats['source_files'] * 100)
                if stats['source_files'] > 0
                else 0
            )
            lines.append(f"- Test ratio: {test_ratio:.1f}%\n")

        if coverage["untested_entities"]:
            lines.append("\n## Untested Entities")
            for item in coverage["untested_entities"][:20]:  # Top 20
                lines.append(f"- `{item['entity']}` ({item['type']}) in {item['file']}")

        return "\n".join(lines)

# Usage
analyzer = TestCoverageAnalyzer("/path/to/workspace")
report = analyzer.generate_report()
print(report)
```

These examples demonstrate the versatility and power of the multi-language analysis system for building advanced code intelligence features.
