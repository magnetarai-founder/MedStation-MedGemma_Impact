# Quick Start Guide - Multi-Language Analyzer

5-minute guide to using the multi-language code analysis system.

## Installation

Already installed in MagnetarCode! Just import:

```python
from api.services.languages import get_unified_analyzer
```

## Basic Usage

### Analyze a Single File

```python
from api.services.languages import get_unified_analyzer

# Create analyzer
analyzer = get_unified_analyzer()

# Parse file (auto-detects language)
result = analyzer.parse_file("src/UserService.ts")

# Access results
print(f"Language: {result.language.value}")
print(f"Found {len(result.entities)} entities:")

for entity in result.entities:
    print(f"  - {entity.entity_type}: {entity.name} @ line {entity.line_number}")
```

### Analyze a Directory

```python
from api.services.languages import get_unified_analyzer

analyzer = get_unified_analyzer()

# Analyze entire directory
results = analyzer.analyze_directory("src/", recursive=True)

# Print summary
for file_path, result in results.items():
    print(f"{file_path}: {len(result.entities)} entities ({result.language.value})")
```

### Language-Specific Analysis

```python
from api.services.languages import TypeScriptAnalyzer, Language

# Create TypeScript analyzer
analyzer = TypeScriptAnalyzer(Language.TYPESCRIPT)

# Parse TypeScript code
code = """
export interface User {
    name: string;
    age: number;
}
"""

entities = analyzer.extract_entities(code, "user.ts")
```

## Common Tasks

### Find All Classes

```python
result = analyzer.parse_file("src/models.ts")

classes = [e for e in result.entities if e.entity_type == "class"]
for cls in classes:
    print(f"Class: {cls.name}")
    print(f"  Methods: {cls.methods}")
    print(f"  Extends: {cls.extends}")
```

### Find Dependencies

```python
result = analyzer.parse_file("src/app.ts")

for dep in result.dependencies:
    print(f"Import: {dep.module}")
    if dep.symbols:
        print(f"  Symbols: {dep.symbols}")
```

### Build Call Graph

```python
result = analyzer.parse_file("src/service.go")

for func_name, node in result.call_graph.items():
    print(f"{func_name} calls:")
    for called in node.calls:
        print(f"  - {called}")
```

### Detect Language

```python
from api.services.languages import detect_language, detect_language_from_content
from pathlib import Path

# From file extension
lang = detect_language(Path("app.ts"))
print(lang)  # Language.TYPESCRIPT

# From code content
code = "package main\nfunc main() {}"
lang = detect_language_from_content(code)
print(lang)  # Language.GO
```

## Supported Languages

- TypeScript/JavaScript (`.ts`, `.tsx`, `.js`, `.jsx`)
- Go (`.go`)
- Rust (`.rs`)
- Java (`.java`)

## Entity Types

Common entity types extracted:
- `class` - Classes
- `interface` - Interfaces/traits
- `struct` - Structs (Go, Rust)
- `function` - Functions
- `method` - Methods
- `enum` - Enums
- `type` - Type aliases

## CodeEntity Fields

Each extracted entity has:

```python
entity.name            # Entity name
entity.entity_type     # Type (class, function, etc.)
entity.language        # Source language
entity.file_path       # File location
entity.line_number     # Start line
entity.signature       # Full signature
entity.parameters      # Function parameters
entity.return_type     # Return type
entity.docstring       # Documentation
entity.methods         # Methods (for classes)
entity.attributes      # Fields (for classes)
entity.extends         # Base classes
entity.implements      # Interfaces
```

## Examples by Language

### TypeScript

```python
from api.services.languages import TypeScriptAnalyzer, Language

analyzer = TypeScriptAnalyzer(Language.TYPESCRIPT)

code = """
export class UserService {
    async getUser(id: string): Promise<User> {
        return fetch(`/api/users/${id}`);
    }
}
"""

entities = analyzer.extract_entities(code, "service.ts")
# Returns: [CodeEntity(name="UserService", entity_type="class", ...)]
```

### Go

```python
from api.services.languages import GoAnalyzer

analyzer = GoAnalyzer()

code = """
type User struct {
    ID   int
    Name string
}

func (u *User) GetName() string {
    return u.Name
}
"""

entities = analyzer.extract_entities(code, "user.go")
# Returns: [CodeEntity(name="User", entity_type="struct", ...),
#           CodeEntity(name="GetName", entity_type="method", ...)]
```

### Rust

```python
from api.services.languages import RustAnalyzer

analyzer = RustAnalyzer()

code = """
#[derive(Debug)]
pub struct User {
    pub name: String,
}

impl User {
    pub fn new(name: String) -> Self {
        Self { name }
    }
}
"""

entities = analyzer.extract_entities(code, "user.rs")
# Returns: [CodeEntity(name="User", entity_type="struct", ...),
#           CodeEntity(name="impl User", entity_type="impl", ...),
#           CodeEntity(name="new", entity_type="function", ...)]
```

### Java

```python
from api.services.languages import JavaAnalyzer

analyzer = JavaAnalyzer()

code = """
@Entity
public class User {
    private String name;

    public String getName() {
        return name;
    }
}
"""

entities = analyzer.extract_entities(code, "User.java")
# Returns: [CodeEntity(name="User", entity_type="class", ...)]
```

## Cheat Sheet

| Task | Code |
|------|------|
| Analyze file | `analyzer.parse_file("file.ts")` |
| Analyze directory | `analyzer.analyze_directory("src/")` |
| Extract entities | `analyzer.extract_entities(code, "file.ts")` |
| Find dependencies | `analyzer.find_dependencies(code, "file.ts")` |
| Get call graph | `analyzer.get_call_graph(code, "file.ts")` |
| Detect language | `detect_language(Path("file.ts"))` |
| Get unified analyzer | `get_unified_analyzer()` |
| Get specific analyzer | `get_analyzer(Language.GO)` |

## Tips

1. **Use UnifiedAnalyzer** for multi-language projects
2. **Cache results** when analyzing the same files repeatedly
3. **Check result.errors** for parsing failures
4. **Use entity.to_dict()** for JSON serialization
5. **Filter by entity_type** to find specific symbols

## Next Steps

- Read [README.md](./README.md) for detailed documentation
- Check [EXAMPLES.md](./EXAMPLES.md) for advanced use cases
- See [INTEGRATION.md](./INTEGRATION.md) for service integration

## Help

```python
# List supported languages
analyzer = get_unified_analyzer()
supported = analyzer.registry.supported_languages()
print([lang.value for lang in supported])

# Get entity info
entity = entities[0]
print(entity.to_dict())

# Check language capabilities
from api.services.languages import Language
print(Language.TYPESCRIPT.is_typescript_family())  # True
```

## Common Patterns

### Find all functions in a file

```python
result = analyzer.parse_file("app.ts")
functions = [e for e in result.entities if e.entity_type == "function"]
```

### Get all imports

```python
result = analyzer.parse_file("app.ts")
imports = [dep.module for dep in result.dependencies]
```

### Find classes with methods

```python
result = analyzer.parse_file("service.go")
classes_with_methods = [
    e for e in result.entities
    if e.entity_type in ["class", "struct"] and e.methods
]
```

### Build file statistics

```python
results = analyzer.analyze_directory("src/")
stats = {
    "total_files": len(results),
    "total_entities": sum(len(r.entities) for r in results.values()),
    "by_language": {}
}

for result in results.values():
    lang = result.language.value
    stats["by_language"][lang] = stats["by_language"].get(lang, 0) + 1
```

That's it! You're ready to analyze code across multiple languages.
