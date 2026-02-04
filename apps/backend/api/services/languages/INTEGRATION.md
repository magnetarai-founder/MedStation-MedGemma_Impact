# Multi-Language Analyzer Integration Guide

Guide for integrating the multi-language analysis system with MagnetarCode services.

## Integration Points

### 1. AST Search Engine (Python)

The language analyzer system complements the existing Python AST search engine:

```python
from api.services.analysis import get_ast_search
from api.services.languages import get_unified_analyzer, Language

# For Python files - use the specialized AST search
ast_search = get_ast_search("/path/to/workspace")
await ast_search.index_workspace()

python_entities = ast_search.find_definition("User")
call_graph = ast_search.find_callers("process_data")

# For other languages - use the unified analyzer
unified = get_unified_analyzer()

# TypeScript analysis
ts_result = unified.parse_file("src/UserService.ts")
for entity in ts_result.entities:
    print(f"{entity.entity_type}: {entity.name}")

# Go analysis
go_result = unified.parse_file("internal/service.go")
for dep in go_result.dependencies:
    print(f"import: {dep.module}")
```

### 2. Background Analyzer

Integrate with the background analysis system for comprehensive code quality checks:

```python
from api.services.analysis import get_background_analyzer, AnalysisType
from api.services.languages import get_unified_analyzer
from pathlib import Path

async def analyze_codebase(workspace_root: str):
    """Analyze entire codebase across all languages."""
    unified = get_unified_analyzer()
    bg_analyzer = get_background_analyzer(workspace_root)

    # Analyze all files
    results = unified.analyze_directory(workspace_root, recursive=True)

    # Process results by language
    by_language = {}
    for file_path, result in results.items():
        lang = result.language.value
        if lang not in by_language:
            by_language[lang] = []
        by_language[lang].append(result)

    # Generate statistics
    stats = {
        "total_files": len(results),
        "by_language": {
            lang: {
                "files": len(files),
                "entities": sum(len(f.entities) for f in files),
                "dependencies": sum(len(f.dependencies) for f in files),
            }
            for lang, files in by_language.items()
        },
    }

    return stats, results
```

### 3. Code Editor Service

Enhance the code editor with language-aware features:

```python
from api.services.languages import detect_language, get_analyzer
from pathlib import Path

class LanguageAwareCodeEditor:
    """Code editor with multi-language support."""

    def __init__(self):
        self.unified_analyzer = get_unified_analyzer()

    async def get_symbols(self, file_path: str) -> list[dict]:
        """Get symbol outline for a file."""
        result = self.unified_analyzer.parse_file(file_path)

        symbols = []
        for entity in result.entities:
            symbols.append({
                "name": entity.name,
                "kind": entity.entity_type,
                "line": entity.line_number,
                "endLine": entity.end_line,
                "signature": entity.signature,
                "children": entity.methods if entity.methods else [],
            })

        return symbols

    async def find_references(self, file_path: str, symbol_name: str) -> list[dict]:
        """Find all references to a symbol."""
        # Parse file
        result = self.unified_analyzer.parse_file(file_path)

        # Find in call graph
        references = []
        for func_name, node in result.call_graph.items():
            if symbol_name in node.calls:
                references.append({
                    "file": file_path,
                    "line": node.line_number,
                    "function": func_name,
                })

        return references

    async def get_completions(self, file_path: str, line: int) -> list[dict]:
        """Get code completions based on context."""
        language = detect_language(Path(file_path))
        result = self.unified_analyzer.parse_file(file_path)

        # Extract available symbols
        completions = []
        for entity in result.entities:
            completions.append({
                "label": entity.name,
                "kind": entity.entity_type,
                "detail": entity.signature or entity.entity_type,
                "documentation": entity.docstring,
            })

        return completions
```

### 4. Context Engine Integration

Provide language-aware context for RAG and embeddings:

```python
from api.services.context_engine import ContextEngine
from api.services.languages import get_unified_analyzer

class MultiLanguageContextEngine:
    """Context engine with multi-language analysis."""

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.analyzer = get_unified_analyzer()
        self.context_engine = ContextEngine(workspace_root)

    async def build_context(self, query: str) -> str:
        """Build context using language-aware analysis."""
        # Analyze entire codebase
        results = self.analyzer.analyze_directory(self.workspace_root)

        # Find relevant entities
        relevant = []
        query_lower = query.lower()

        for file_path, result in results.items():
            for entity in result.entities:
                # Simple relevance scoring
                if query_lower in entity.name.lower():
                    relevant.append({
                        "entity": entity,
                        "file": file_path,
                        "language": result.language.value,
                    })

        # Build context string
        context_parts = []
        for item in relevant[:10]:  # Top 10
            entity = item["entity"]
            context_parts.append(
                f"[{item['language']}] {entity.entity_type} {entity.name}\n"
                f"File: {item['file']}:{entity.line_number}\n"
                f"Signature: {entity.signature or 'N/A'}\n"
            )

        return "\n".join(context_parts)

    async def get_entity_embeddings(self, file_path: str):
        """Generate embeddings for code entities."""
        result = self.analyzer.parse_file(file_path)

        embeddings = []
        for entity in result.entities:
            # Create text representation
            text = f"{entity.entity_type} {entity.name}"
            if entity.signature:
                text += f" {entity.signature}"
            if entity.docstring:
                text += f"\n{entity.docstring}"

            # Generate embedding (using existing context engine)
            embedding = await self.context_engine.embed_text(text)

            embeddings.append({
                "entity": entity.name,
                "type": entity.entity_type,
                "embedding": embedding,
                "metadata": entity.to_dict(),
            })

        return embeddings
```

### 5. Semantic Search Integration

Enhance semantic search with language-aware features:

```python
from api.services.semantic_search import SemanticSearchEngine
from api.services.languages import get_unified_analyzer, Language

class MultiLanguageSemanticSearch:
    """Semantic search across multiple languages."""

    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.analyzer = get_unified_analyzer()
        self.search_engine = SemanticSearchEngine()

    async def index_codebase(self):
        """Index entire codebase for semantic search."""
        results = self.analyzer.analyze_directory(self.workspace_root)

        for file_path, result in results.items():
            for entity in result.entities:
                # Create searchable document
                doc = {
                    "id": f"{file_path}:{entity.line_number}",
                    "name": entity.name,
                    "type": entity.entity_type,
                    "language": result.language.value,
                    "file": file_path,
                    "line": entity.line_number,
                    "signature": entity.signature,
                    "docstring": entity.docstring,
                    "content": self._build_entity_text(entity),
                }

                await self.search_engine.index_document(doc)

    def _build_entity_text(self, entity) -> str:
        """Build searchable text from entity."""
        parts = [
            f"{entity.entity_type} {entity.name}",
        ]

        if entity.signature:
            parts.append(entity.signature)

        if entity.docstring:
            parts.append(entity.docstring)

        if entity.parameters:
            params = ", ".join(p.get("name", "") for p in entity.parameters)
            parts.append(f"parameters: {params}")

        return "\n".join(parts)

    async def search(self, query: str, language: Language | None = None):
        """Search for entities across codebase."""
        results = await self.search_engine.search(query)

        # Filter by language if specified
        if language:
            results = [r for r in results if r["language"] == language.value]

        return results
```

### 6. Agent API Integration

Provide language analysis capabilities to AI agents:

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.services.languages import get_unified_analyzer, Language

router = APIRouter(prefix="/api/v1/language-analysis", tags=["Language Analysis"])

class AnalysisRequest(BaseModel):
    file_path: str
    include_dependencies: bool = True
    include_call_graph: bool = False

class AnalysisResponse(BaseModel):
    language: str
    entities: list[dict]
    dependencies: list[dict] | None = None
    call_graph: dict | None = None
    errors: list[str]

@router.post("/analyze-file", response_model=AnalysisResponse)
async def analyze_file(request: AnalysisRequest):
    """Analyze a source file."""
    try:
        analyzer = get_unified_analyzer()
        result = analyzer.parse_file(request.file_path)

        return AnalysisResponse(
            language=result.language.value,
            entities=[e.to_dict() for e in result.entities],
            dependencies=[
                {"module": d.module, "symbols": d.symbols, "line": d.line_number}
                for d in result.dependencies
            ] if request.include_dependencies else None,
            call_graph={
                name: {
                    "line": node.line_number,
                    "calls": node.calls,
                }
                for name, node in result.call_graph.items()
            } if request.include_call_graph else None,
            errors=result.errors,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/supported-languages")
async def get_supported_languages():
    """Get list of supported languages."""
    analyzer = get_unified_analyzer()
    return {
        "languages": [lang.value for lang in analyzer.registry.supported_languages()]
    }

class DirectoryAnalysisRequest(BaseModel):
    directory: str
    recursive: bool = True
    languages: list[str] | None = None

@router.post("/analyze-directory")
async def analyze_directory(request: DirectoryAnalysisRequest):
    """Analyze all files in a directory."""
    analyzer = get_unified_analyzer()
    results = analyzer.analyze_directory(request.directory, request.recursive)

    # Filter by languages if specified
    if request.languages:
        requested_langs = set(request.languages)
        results = {
            path: result
            for path, result in results.items()
            if result.language.value in requested_langs
        }

    # Build summary
    summary = {
        "total_files": len(results),
        "by_language": {},
        "total_entities": sum(len(r.entities) for r in results.values()),
        "total_dependencies": sum(len(r.dependencies) for r in results.values()),
    }

    for result in results.values():
        lang = result.language.value
        if lang not in summary["by_language"]:
            summary["by_language"][lang] = {"files": 0, "entities": 0}
        summary["by_language"][lang]["files"] += 1
        summary["by_language"][lang]["entities"] += len(result.entities)

    return {
        "summary": summary,
        "files": [
            {
                "path": path,
                "language": result.language.value,
                "entity_count": len(result.entities),
            }
            for path, result in results.items()
        ],
    }
```

### 7. Orchestration Integration

Use language analysis for intelligent task routing:

```python
from api.services.orchestration import MagnetarOrchestrator
from api.services.languages import detect_language, Language

class LanguageAwareOrchestrator:
    """Orchestrator with language-specific routing."""

    def __init__(self, orchestrator: MagnetarOrchestrator):
        self.orchestrator = orchestrator

    async def route_task(self, file_path: str, task_type: str):
        """Route task based on file language."""
        language = detect_language(Path(file_path))

        # Route to appropriate agent based on language
        agent_mapping = {
            Language.TYPESCRIPT: "typescript-expert",
            Language.JAVASCRIPT: "javascript-expert",
            Language.GO: "go-expert",
            Language.RUST: "rust-expert",
            Language.JAVA: "java-expert",
            Language.PYTHON: "python-expert",
        }

        preferred_agent = agent_mapping.get(language, "general-code-expert")

        return await self.orchestrator.execute_task(
            task_type=task_type,
            file_path=file_path,
            preferred_agent=preferred_agent,
            metadata={"language": language.value},
        )
```

## Example: Full Codebase Analysis

```python
from api.services.languages import get_unified_analyzer
from api.services.analysis import get_ast_search
import asyncio

async def analyze_full_codebase(workspace_root: str):
    """Comprehensive multi-language codebase analysis."""

    # Initialize analyzers
    unified = get_unified_analyzer()
    python_ast = get_ast_search(workspace_root)

    # Index Python files with specialized analyzer
    await python_ast.index_workspace()
    python_stats = python_ast.get_stats()

    # Analyze other languages
    other_results = unified.analyze_directory(workspace_root)

    # Combine results
    all_files = {}
    all_entities = []

    # Add Python results
    for file_path, entities in python_ast._by_file.items():
        all_files[file_path] = {
            "language": "python",
            "entities": len(entities),
        }
        all_entities.extend(entities)

    # Add other language results
    for file_path, result in other_results.items():
        if result.language.value != "python":  # Avoid duplicates
            all_files[file_path] = {
                "language": result.language.value,
                "entities": len(result.entities),
                "dependencies": len(result.dependencies),
            }
            all_entities.extend(result.entities)

    # Build statistics
    stats = {
        "total_files": len(all_files),
        "total_entities": len(all_entities),
        "by_language": {},
        "entity_types": {},
    }

    for entity in all_entities:
        # By language
        lang = entity.language.value if hasattr(entity, "language") else "python"
        if lang not in stats["by_language"]:
            stats["by_language"][lang] = 0
        stats["by_language"][lang] += 1

        # By type
        entity_type = entity.entity_type.value if hasattr(entity.entity_type, "value") else entity.entity_type
        if entity_type not in stats["entity_types"]:
            stats["entity_types"][entity_type] = 0
        stats["entity_types"][entity_type] += 1

    return stats, all_files, all_entities

# Usage
stats, files, entities = await analyze_full_codebase("/path/to/workspace")
print(f"Analyzed {stats['total_files']} files")
print(f"Found {stats['total_entities']} entities")
print(f"Languages: {list(stats['by_language'].keys())}")
```

## Best Practices

1. **Language Detection**
   - Always use `detect_language()` for unknown files
   - Fall back to content analysis for ambiguous extensions

2. **Performance**
   - Use `UnifiedAnalyzer.analyze_directory()` for bulk analysis
   - Cache results when analyzing the same files repeatedly
   - Process large directories in batches

3. **Error Handling**
   - Check `ParseResult.errors` for parsing failures
   - Handle `Language.UNKNOWN` gracefully
   - Log analysis failures for debugging

4. **Cross-Language**
   - Use `CodeEntity.to_dict()` for serialization
   - Normalize entity types when comparing across languages
   - Build language-agnostic indexes for search

5. **Integration**
   - Combine with existing Python AST search for comprehensive coverage
   - Use with background analyzer for continuous monitoring
   - Integrate with semantic search for natural language queries

## Performance Tips

```python
# Good: Analyze directory once, cache results
results = analyzer.analyze_directory("src/")
cache[workspace_root] = results

# Good: Parallel processing for large codebases
import concurrent.futures

with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = [
        executor.submit(analyzer.parse_file, f)
        for f in file_list
    ]
    results = [f.result() for f in futures]

# Good: Filter files before analyzing
supported_extensions = {".ts", ".tsx", ".go", ".rs", ".java"}
files_to_analyze = [
    f for f in all_files
    if f.suffix in supported_extensions
]
```

## Troubleshooting

**Issue: Language not detected**
```python
# Solution: Use content-based detection
from api.services.languages import detect_language_from_content

with open(file_path) as f:
    content = f.read()
    language = detect_language_from_content(content)
```

**Issue: Missing entities**
```python
# Solution: Check parse errors
result = analyzer.parse_file(file_path)
if result.errors:
    print(f"Parse errors: {result.errors}")
```

**Issue: Slow analysis**
```python
# Solution: Use parallel processing or incremental analysis
# Only analyze changed files
from pathlib import Path
import time

last_modified = {}
for file_path in files:
    mtime = Path(file_path).stat().st_mtime
    if file_path not in last_modified or mtime > last_modified[file_path]:
        result = analyzer.parse_file(file_path)
        last_modified[file_path] = mtime
```
