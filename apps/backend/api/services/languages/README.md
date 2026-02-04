# Multi-Language Code Analysis System

Production-quality code analysis system for MagnetarCode supporting multiple programming languages with unified entity extraction, dependency analysis, and call graph generation.

## Supported Languages

- **TypeScript/JavaScript** - AST parsing, type extraction, JSX/TSX support
- **Go** - struct/interface extraction, package analysis, receiver methods
- **Rust** - trait/impl analysis, lifetime detection, derive macros
- **Java** - class hierarchy, annotation processing, generics
- **Python** - Full AST analysis (via `api.services.analysis.ast_search`)

## Features

### Core Capabilities

1. **Language Detection**
   - Extension-based detection (`.ts`, `.go`, `.rs`, `.java`, `.py`)
   - Content-based heuristics for ambiguous cases
   - Automatic language identification

2. **Entity Extraction**
   - Classes, interfaces, structs, traits, enums
   - Functions, methods, constructors
   - Type definitions and aliases
   - Generic/template parameters
   - Visibility modifiers and annotations

3. **Dependency Analysis**
   - Import/use/require statements
   - Module resolution
   - Relative vs absolute imports
   - Cross-language dependency tracking

4. **Call Graph Generation**
   - Function call relationships
   - Method invocations
   - Caller/callee mapping
   - Cross-file analysis support

5. **Unified Format**
   - Single `CodeEntity` format across all languages
   - Normalized representation for cross-language analysis
   - Language-specific metadata preserved

## Architecture

```
languages/
├── __init__.py          # Public API exports
├── analyzers.py         # Core analyzer implementations
├── README.md           # This file
└── test_analyzers.py   # Test suite
```

### Key Components

#### Language Enum
```python
class Language(str, Enum):
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    # ... more languages
```

#### CodeEntity - Unified Format
```python
@dataclass
class CodeEntity:
    name: str
    entity_type: str  # function, class, method, interface, etc.
    language: Language
    file_path: str
    line_number: int
    end_line: Optional[int]
    signature: Optional[str]
    parameters: list[dict]
    return_type: Optional[str]
    decorators: list[str]
    implements: list[str]
    extends: list[str]
    # ... additional fields
```

#### Base Analyzer
```python
class LanguageAnalyzer(ABC):
    @abstractmethod
    def parse_file(self, file_path: str | Path) -> ParseResult:
        """Parse source file into entities."""

    @abstractmethod
    def extract_entities(self, source_code: str, file_path: str) -> list[CodeEntity]:
        """Extract code entities from source."""

    @abstractmethod
    def find_dependencies(self, source_code: str, file_path: str) -> list[DependencyInfo]:
        """Find imports and dependencies."""

    @abstractmethod
    def get_call_graph(self, source_code: str, file_path: str) -> dict[str, CallGraphNode]:
        """Build function call graph."""
```

## Usage Examples

### Basic Analysis

```python
from api.services.languages import TypeScriptAnalyzer, Language

# Create analyzer
analyzer = TypeScriptAnalyzer(Language.TYPESCRIPT)

# Parse TypeScript code
code = """
export interface User {
    name: string;
    age: number;
}

export class UserService {
    async getUser(id: string): Promise<User> {
        return fetch(`/api/users/${id}`).then(r => r.json());
    }
}
"""

# Extract entities
entities = analyzer.extract_entities(code, "user.ts")

for entity in entities:
    print(f"{entity.entity_type}: {entity.name} @ line {entity.line_number}")
    if entity.methods:
        print(f"  methods: {entity.methods}")
```

Output:
```
interface: User @ line 2
class: UserService @ line 7
  methods: ['getUser']
```

### Unified Analyzer

```python
from api.services.languages import get_unified_analyzer
from pathlib import Path

# Get unified analyzer (auto-detects language)
analyzer = get_unified_analyzer()

# Parse any supported file
result = analyzer.parse_file("src/main.go")

print(f"Language: {result.language.value}")
print(f"Entities: {len(result.entities)}")
print(f"Dependencies: {len(result.dependencies)}")

# Analyze entire directory
results = analyzer.analyze_directory("src/", recursive=True)

for file_path, result in results.items():
    print(f"\n{file_path}:")
    for entity in result.entities:
        print(f"  - {entity.entity_type}: {entity.name}")
```

### Language-Specific Features

#### TypeScript/JavaScript
```python
from api.services.languages import TypeScriptAnalyzer, Language

analyzer = TypeScriptAnalyzer(Language.TYPESCRIPT)

# Extracts:
# - Interfaces and type aliases
# - Classes with generics
# - Arrow functions
# - Async/await patterns
# - React components (TSX)
# - Import/export statements

result = analyzer.parse_file("component.tsx")
```

#### Go
```python
from api.services.languages import GoAnalyzer

analyzer = GoAnalyzer()

# Extracts:
# - Structs and interfaces
# - Methods with receivers
# - Package declarations
# - Type definitions
# - Function signatures

result = analyzer.parse_file("service.go")
```

#### Rust
```python
from api.services.languages import RustAnalyzer

analyzer = RustAnalyzer()

# Extracts:
# - Structs and enums
# - Traits and impl blocks
# - Derive macros (#[derive(Debug)])
# - Lifetime parameters
# - pub/private visibility
# - use statements

result = analyzer.parse_file("lib.rs")
```

#### Java
```python
from api.services.languages import JavaAnalyzer

analyzer = JavaAnalyzer()

# Extracts:
# - Classes and interfaces
# - Annotations (@Entity, @Service)
# - Generics
# - extends/implements relationships
# - Package declarations
# - import statements

result = analyzer.parse_file("User.java")
```

### Cross-Language Analysis

```python
from api.services.languages import get_unified_analyzer

analyzer = get_unified_analyzer()

# Analyze multi-language project
results = analyzer.analyze_directory("src/")

# Build cross-language dependency graph
dep_graph = analyzer.get_cross_language_dependencies(results)

for file, dependencies in dep_graph.items():
    if dependencies:
        print(f"{file} depends on:")
        for dep in dependencies:
            print(f"  - {dep}")
```

### Language Detection

```python
from api.services.languages import detect_language, detect_language_from_content
from pathlib import Path

# From file extension
lang = detect_language(Path("app.ts"))
print(lang)  # Language.TYPESCRIPT

# From content
code = """
package main

func main() {
    println("Hello")
}
"""

lang = detect_language_from_content(code)
print(lang)  # Language.GO
```

### Custom Registry

```python
from api.services.languages import LanguageRegistry, Language

# Create custom registry
registry = LanguageRegistry()

# Register custom analyzer
class PythonAnalyzer(LanguageAnalyzer):
    def parse_file(self, file_path):
        # Custom implementation
        pass

registry.register(Language.PYTHON, PythonAnalyzer)

# Get analyzer
analyzer = registry.get_analyzer(Language.PYTHON)
```

## API Reference

### Core Classes

#### `Language`
Enum of supported programming languages.

**Methods:**
- `from_extension(ext: str) -> Language` - Detect language from file extension
- `is_typescript_family() -> bool` - Check if TypeScript/JavaScript variant

#### `CodeEntity`
Unified code entity representation.

**Fields:**
- `name: str` - Entity name
- `entity_type: str` - Type (class, function, method, etc.)
- `language: Language` - Source language
- `file_path: str` - File location
- `line_number: int` - Start line
- `signature: str | None` - Full signature
- `parameters: list[dict]` - Function parameters
- `return_type: str | None` - Return type annotation
- `decorators: list[str]` - Decorators/attributes
- `implements: list[str]` - Implemented interfaces
- `extends: list[str]` - Base classes
- `methods: list[str]` - Method names (for classes)
- `attributes: list[str]` - Field names (for classes)

**Methods:**
- `to_dict() -> dict` - Convert to dictionary

#### `LanguageAnalyzer`
Abstract base class for language analyzers.

**Methods:**
- `parse_file(file_path) -> ParseResult` - Parse entire file
- `extract_entities(source_code, file_path) -> list[CodeEntity]` - Extract entities
- `find_dependencies(source_code, file_path) -> list[DependencyInfo]` - Find imports
- `get_call_graph(source_code, file_path) -> dict[str, CallGraphNode]` - Build call graph

#### `UnifiedAnalyzer`
Multi-language analyzer with automatic language detection.

**Methods:**
- `parse_file(file_path) -> ParseResult` - Parse file (auto-detect language)
- `analyze_directory(directory, recursive=True) -> dict[str, ParseResult]` - Analyze directory
- `get_cross_language_dependencies(results) -> dict[str, list[str]]` - Build dependency graph

### Concrete Analyzers

#### `TypeScriptAnalyzer`
TypeScript/JavaScript analyzer.

```python
analyzer = TypeScriptAnalyzer(Language.TYPESCRIPT)
# or
analyzer = TypeScriptAnalyzer(Language.JAVASCRIPT)
```

#### `GoAnalyzer`
Go language analyzer.

```python
analyzer = GoAnalyzer()
```

#### `RustAnalyzer`
Rust language analyzer.

```python
analyzer = RustAnalyzer()
```

#### `JavaAnalyzer`
Java language analyzer.

```python
analyzer = JavaAnalyzer()
```

### Utility Functions

#### `detect_language(file_path: Path) -> Language`
Detect language from file path and optionally content.

#### `detect_language_from_content(content: str) -> Language`
Detect language from source code content using heuristics.

#### `get_analyzer(language: Language) -> LanguageAnalyzer | None`
Get analyzer for specific language from global registry.

#### `get_unified_analyzer() -> UnifiedAnalyzer`
Get global unified analyzer instance.

## Implementation Details

### Parsing Strategy

The analyzers use a **regex-based approach** with support for tree-sitter as an optional enhancement:

1. **Regex patterns** - Fast, portable, no dependencies
2. **Tree-sitter fallback** - More accurate parsing when available
3. **Heuristic detection** - Content-based language identification

### Entity Extraction

Each analyzer implements language-specific patterns:

- **TypeScript**: Interfaces, classes, functions, arrow functions, generics
- **Go**: Structs, interfaces, methods with receivers, type definitions
- **Rust**: Structs, enums, traits, impl blocks, derive macros
- **Java**: Classes, interfaces, enums, annotations, generics

### Call Graph Building

Call graphs are built by:
1. Extracting function/method definitions
2. Finding function body boundaries (brace matching)
3. Identifying function calls within bodies
4. Building caller -> callee relationships

### Cross-Language Support

The unified `CodeEntity` format enables:
- Consistent representation across languages
- Language-agnostic analysis tools
- Cross-language dependency tracking
- Polyglot project understanding

## Performance

- **Fast**: Regex-based parsing is very fast
- **Scalable**: Can process large codebases
- **Memory efficient**: Streaming file processing
- **Parallel**: Can analyze multiple files concurrently

## Testing

Run the test suite:

```bash
cd apps/backend
python3 test_language_analyzers.py
```

## Integration

### With AST Search Engine

The Python analyzer integrates with the existing AST search engine:

```python
from api.services.analysis import get_ast_search

# For Python files, use the AST search engine
ast_search = get_ast_search(workspace_root)
await ast_search.index_workspace()

entities = ast_search.find_definition("User")
```

### With Background Analyzer

```python
from api.services.analysis import get_background_analyzer
from api.services.languages import get_unified_analyzer

bg_analyzer = get_background_analyzer()
lang_analyzer = get_unified_analyzer()

# Combine for comprehensive analysis
results = lang_analyzer.analyze_directory("src/")
# Feed to background analyzer for deeper insights
```

## Future Enhancements

- [ ] Tree-sitter integration for more accurate parsing
- [ ] Python analyzer (currently uses ast_search)
- [ ] C/C++ support
- [ ] C# support
- [ ] Semantic analysis (type inference, flow analysis)
- [ ] Symbol resolution across files
- [ ] Incremental parsing for large files
- [ ] LSP integration for real-time analysis

## License

Part of MagnetarCode - All rights reserved.
