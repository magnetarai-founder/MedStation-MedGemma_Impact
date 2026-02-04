# Auto-Documentation System

Intelligent documentation generation and maintenance system for MagnetarCode.

## Features

### 1. Automatic Docstring Generation
- Generates Google, NumPy, and Sphinx style docstrings
- Uses LLM (Ollama) for intelligent, context-aware documentation
- Analyzes function/class signatures and implementations
- Fallback to template-based generation if LLM unavailable

### 2. Documentation Sync Detection
- Detects when code changes but documentation doesn't
- Tracks parameter changes, return type changes, and implementation changes
- Uses code signature hashing for efficient change detection
- Maintains cache of previous signatures for comparison

### 3. Stale Documentation Detection
- Identifies documentation that describes old behavior
- Compares current code structure with documented structure
- Flags mismatches in parameters, types, and decorators

### 4. Project Documentation Generation
- **README.md**: Auto-generated from codebase structure
  - Project structure tree
  - API endpoint overview
  - Module summaries
- **API Documentation**: Extracted from FastAPI/Flask endpoints
  - Grouped by module
  - Includes HTTP methods, paths, and descriptions
  - Supports Markdown and HTML formats

### 5. Documentation Health Scanning
- Scans entire workspace for documentation coverage
- Reports missing, stale, and up-to-date documentation
- Provides coverage percentages per file and overall
- Customizable include/exclude patterns

### 6. Diff Preview System
- Preview documentation changes before applying
- Shows unified diff of old vs. new docstrings
- Supports "add" and "update" actions
- Allows review before committing changes

## Installation

The system is already integrated into MagnetarCode's backend services.

```python
from api.services.docs import DocGenerator, DocstringStyle
```

## Quick Start

### Generate a Docstring

```python
from api.services.docs import get_doc_generator, DocstringStyle

# Initialize
generator = get_doc_generator(workspace_root="/path/to/project")

# Generate Google-style docstring
docstring = await generator.generate_docstring(
    file_path="api/services/example.py",
    entity_name="my_function",
    style=DocstringStyle.GOOGLE
)

print(docstring)
```

### Check Documentation Health

```python
# Scan entire workspace
results = await generator.scan_documentation_health()

for status in results:
    print(f"File: {status.file_path}")
    print(f"Coverage: {status.coverage_percent}%")
    print(f"Missing: {len(status.missing)}")
    print(f"Stale: {len(status.stale)}")
```

### Update Stale Documentation

```python
# Preview changes first
diff = await generator.update_docstring(
    file_path="api/services/example.py",
    entity_name="my_function",
    preview=True  # Just show diff, don't apply
)

print(f"Action: {diff.action}")
print(diff.diff)

# Apply if satisfied
await generator.update_docstring(
    file_path="api/services/example.py",
    entity_name="my_function",
    preview=False  # Apply changes
)
```

### Generate README

```python
# Generate and write README
await generator.generate_readme(
    output_path="README.md",
    include_api_overview=True,
    include_structure=True
)
```

### Generate API Documentation

```python
# Generate API docs for all endpoints
files = await generator.generate_api_docs(
    output_dir="docs/api",
    format="markdown"
)

print(f"Generated {len(files)} documentation files")
```

## Docstring Styles

### Google Style (Default)

```python
"""
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
```

### NumPy Style

```python
"""
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
```

### Sphinx Style

```python
"""
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
```

## Architecture

### Core Components

1. **DocGenerator**: Main orchestrator
   - Manages documentation generation workflow
   - Integrates with LLM for intelligent generation
   - Handles file I/O and AST parsing

2. **DocstringExtractor**: AST-based code parser
   - Extracts functions, classes, methods
   - Retrieves existing docstrings
   - Builds code signatures for comparison

3. **CodeSignature**: Change detection
   - Tracks parameters, return types, decorators
   - Hashes function bodies for change detection
   - Enables efficient sync checking

4. **DocumentationStatus**: Health reporting
   - Tracks missing, stale, and OK documentation
   - Calculates coverage percentages
   - Provides actionable insights

### Data Flow

```
┌─────────────────┐
│  Python File    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ DocstringExtractor│
│  (AST Parser)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Code Signature  │
│  Generation     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LLM (Ollama)   │
│   Generation    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Docstring       │
│ Formatting      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  File Update    │
│  (with diff)    │
└─────────────────┘
```

## Advanced Usage

### Batch Update All Missing Docstrings

```python
# Scan for missing documentation
results = await generator.scan_documentation_health()

for status in results:
    for entity_name in status.missing:
        # Generate and apply docstring
        await generator.update_docstring(
            file_path=status.file_path,
            entity_name=entity_name,
            style=DocstringStyle.GOOGLE,
            preview=False
        )
```

### Custom Include/Exclude Patterns

```python
results = await generator.scan_documentation_health(
    include_patterns=[
        "api/**/*.py",
        "services/**/*.py"
    ],
    exclude_patterns=[
        "**/test_*.py",
        "**/tests/**",
        "**/__pycache__/**",
        "**/migrations/**"
    ]
)
```

### Monitoring Documentation Drift

```python
# Check if specific file needs updates
is_synced, reason = await generator.check_sync(
    file_path="api/services/example.py",
    entity_name="important_function"
)

if not is_synced:
    print(f"Documentation out of sync: {reason}")
    # Trigger update...
```

## Integration with CI/CD

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Run documentation health check
python -c "
import asyncio
from pathlib import Path
from api.services.docs import get_doc_generator

async def check():
    gen = get_doc_generator(Path.cwd())
    results = await gen.scan_documentation_health()

    total = sum(r.total_entities for r in results)
    ok = sum(len(r.ok) for r in results)
    coverage = (ok / total * 100) if total > 0 else 0

    if coverage < 80.0:
        print(f'ERROR: Documentation coverage {coverage:.1f}% < 80%')
        exit(1)

    print(f'Documentation coverage: {coverage:.1f}%')

asyncio.run(check())
"
```

### GitHub Actions

```yaml
name: Documentation Check

on: [pull_request]

jobs:
  doc-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Check Documentation Health
        run: |
          python apps/backend/api/services/docs/example_usage.py
```

## Best Practices

1. **Regular Health Scans**: Run documentation health scans weekly
2. **Preview Before Apply**: Always preview changes before applying
3. **Style Consistency**: Pick one docstring style and stick with it
4. **Context Matters**: Provide additional context when generating complex docstrings
5. **Review LLM Output**: Always review LLM-generated documentation for accuracy
6. **Incremental Updates**: Update documentation incrementally as code changes
7. **Exclude Test Files**: Tests usually don't need formal docstrings

## Performance

- **Parsing**: ~100 files/second with AST
- **LLM Generation**: ~2-5 seconds per docstring (depends on Ollama model)
- **Batch Operations**: Supports async processing for scalability
- **Caching**: Code signature caching for efficient sync checking

## Limitations

1. **LLM Dependency**: Requires Ollama running locally (has fallback)
2. **Python Only**: Currently supports only Python codebases
3. **AST-based**: Relies on valid Python syntax
4. **Context Window**: Limited by LLM context size for very large functions

## Future Enhancements

- [ ] Support for TypeScript/JavaScript
- [ ] Integration with IDE plugins
- [ ] Real-time documentation linting
- [ ] Automated PR comments for missing docs
- [ ] Documentation quality scoring
- [ ] Multi-language support
- [ ] Integration with Sphinx/MkDocs

## Troubleshooting

### "Cannot connect to Ollama"
- Ensure Ollama is running: `ollama serve`
- Check OLLAMA_BASE_URL environment variable
- System will fall back to template-based generation

### "Entity not found"
- Verify entity name exactly matches function/class name
- Check for typos
- Use full name for methods: `ClassName.method_name`

### "Documentation coverage not improving"
- Ensure preview=False when applying changes
- Check file permissions
- Verify no syntax errors in generated docstrings

## API Reference

See the inline documentation in `generator.py` for full API reference.

### Main Classes

- `DocGenerator`: Main documentation generator
- `DocstringStyle`: Enum for docstring styles
- `DocumentationStatus`: Status report for file/entity
- `CodeSignature`: Code signature for change detection
- `DocstringDiff`: Diff preview object

### Main Functions

- `get_doc_generator()`: Get singleton instance
- `generate_docstring()`: Generate docstring for entity
- `check_sync()`: Check if documentation is synced
- `update_docstring()`: Update entity's docstring
- `scan_documentation_health()`: Scan workspace health
- `generate_readme()`: Generate README.md
- `generate_api_docs()`: Generate API documentation

## License

Part of MagnetarCode project.

## Contributing

See main project CONTRIBUTING.md for guidelines.
