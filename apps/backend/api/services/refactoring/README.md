# Smart Refactoring System

A production-quality, AST-based code refactoring system for Python codebases. Provides intelligent refactoring suggestions with safe preview-before-apply capability.

## Features

### 1. Extract Method
Identifies code blocks that should be extracted into separate functions:
- Detects high complexity functions (cyclomatic complexity > 10)
- Detects deep nesting (depth > 3)
- Suggests extracting complex code blocks
- Provides metrics-based confidence scores

### 2. Extract Class
Identifies related functions that should be grouped into a class:
- Groups functions by common parameters
- Groups functions by name prefixes
- Suggests class names based on patterns
- Generates class structure preview

### 3. Dead Code Detection
Finds unused code that can be safely removed:
- Unused function definitions
- Unused variable definitions
- Unused imports
- High confidence suggestions (80-90%)

### 4. Import Optimization
Organizes and cleans up imports:
- Removes duplicate imports
- Organizes imports per PEP 8 (stdlib, third-party, local)
- Removes unused imports
- Sorts imports alphabetically within groups

### 5. Rename Symbol
Safely renames symbols across the codebase:
- Finds all occurrences of a symbol
- Supports functions, classes, variables
- Generates unified diff preview
- Can scope to single file or entire workspace

### 6. Inline Variable
Identifies variables that should be inlined:
- Detects variables used only once
- Suggests inlining for simplicity
- Shows value to be inlined

### 7. Duplicate Code Detection
Finds and suggests consolidating duplicate code:
- Uses AST-based hashing for accurate detection
- Groups identical code blocks
- Suggests extracting to shared function

## Architecture

### Core Components

#### `RefactoringType` (Enum)
```python
class RefactoringType(Enum):
    EXTRACT_METHOD = "extract_method"
    EXTRACT_CLASS = "extract_class"
    DEAD_CODE = "dead_code"
    OPTIMIZE_IMPORTS = "optimize_imports"
    RENAME_SYMBOL = "rename_symbol"
    INLINE_VARIABLE = "inline_variable"
    MOVE_TO_FILE = "move_to_file"
    SIMPLIFY_CONDITION = "simplify_condition"
    REMOVE_DUPLICATE = "remove_duplicate"
```

#### `RefactoringSuggestion` (Dataclass)
```python
@dataclass
class RefactoringSuggestion:
    type: RefactoringType
    location: CodeLocation
    description: str
    confidence: float          # 0.0 to 1.0
    diff_preview: str
    reasoning: str
    metadata: dict[str, Any]
    impact_score: float        # How much this improves code quality
    effort_score: float        # How much work to apply (0=easy, 1=hard)
    safety_score: float        # How safe is this refactoring (0=risky, 1=safe)
```

#### `RefactoringEngine` (Main Class)
The core engine that performs all analysis and refactoring operations.

**Key Methods:**
- `analyze_file(file_path)` - Analyze a file for all refactoring opportunities
- `suggest_extract_method(file_path, start_line, end_line)` - Suggest extracting specific code range
- `find_dead_code(file_path)` - Find unused code
- `optimize_imports(file_path)` - Optimize import statements
- `rename_symbol(symbol_name, new_name)` - Rename symbol safely
- `apply_refactoring(suggestion, dry_run=True)` - Apply or preview refactoring

### AST Visitors

#### `ComplexityVisitor`
Calculates cyclomatic complexity and nesting depth:
- Tracks control flow statements (if, while, for, try/except)
- Calculates maximum nesting depth
- Counts total statements

#### `DeadCodeVisitor`
Finds unused definitions:
- Tracks all definitions (functions, classes, variables, imports)
- Tracks all usages (Name, Attribute nodes)
- Identifies unused definitions

#### `DuplicateCodeFinder`
Finds duplicate code blocks:
- Hashes function bodies using AST unparsing
- Groups identical implementations
- Suggests consolidation

## Usage

### Basic Usage

```python
from api.services.refactoring import get_refactoring_engine, RefactoringType

# Initialize engine
engine = get_refactoring_engine(workspace_root="/path/to/project")

# Analyze a file
suggestions = engine.analyze_file("path/to/file.py")

# Filter by type
extract_suggestions = [
    s for s in suggestions
    if s.type == RefactoringType.EXTRACT_METHOD
]

# Preview a refactoring
for suggestion in suggestions:
    print(f"{suggestion.description}")
    print(f"Confidence: {suggestion.confidence:.1%}")
    print(f"Impact: {suggestion.impact_score:.1%}")
    print(f"\nPreview:\n{suggestion.diff_preview}")

# Apply a refactoring (dry run)
result = engine.apply_refactoring(suggestions[0], dry_run=True)
print(result['diff'])

# Apply for real
result = engine.apply_refactoring(suggestions[0], dry_run=False)
```

### Find Dead Code

```python
from api.services.refactoring import get_refactoring_engine

engine = get_refactoring_engine()

# Find all dead code in a file
dead_code = engine.find_dead_code("myfile.py")

for suggestion in dead_code:
    print(f"Remove: {suggestion.description}")
    print(f"Line {suggestion.location.start_line}")
```

### Optimize Imports

```python
from api.services.refactoring import get_refactoring_engine

engine = get_refactoring_engine()

# Get import optimization suggestions
suggestions = engine.optimize_imports("myfile.py")

for suggestion in suggestions:
    print(suggestion.description)
    print(suggestion.diff_preview)
```

### Rename Symbol

```python
from api.services.refactoring import get_refactoring_engine

engine = get_refactoring_engine()

# Rename across entire workspace
suggestions = engine.rename_symbol(
    symbol_name="old_name",
    new_name="new_name"
)

# Rename in specific file only
suggestions = engine.rename_symbol(
    symbol_name="old_name",
    new_name="new_name",
    file_path="specific_file.py"
)

for suggestion in suggestions:
    print(f"File: {suggestion.location.file_path}")
    print(f"Occurrences: {suggestion.metadata['occurrence_count']}")
    print(suggestion.diff_preview)
```

### Extract Method

```python
from api.services.refactoring import get_refactoring_engine

engine = get_refactoring_engine()

# Suggest extracting specific lines
suggestion = engine.suggest_extract_method(
    file_path="myfile.py",
    start_line=10,
    end_line=25,
    suggested_name="extracted_logic"
)

if suggestion:
    print(suggestion.description)
    print(suggestion.diff_preview)
```

## Configuration

The engine can be configured with thresholds:

```python
engine = get_refactoring_engine()

# Customize thresholds
engine.min_extract_lines = 5      # Min lines for extract method
engine.max_complexity = 10        # Max complexity before suggesting extract
engine.max_nesting = 3            # Max nesting before suggesting extract
engine.min_duplicate_lines = 4    # Min lines to consider duplicate
```

## Metrics and Scoring

### Impact Score (0.0 - 1.0)
How much this refactoring improves code quality:
- 0.8+ : High impact (complex → simple, major improvement)
- 0.5-0.8 : Medium impact (good improvement)
- 0.0-0.5 : Low impact (minor improvement)

### Effort Score (0.0 - 1.0)
How much work is required to apply:
- 0.0-0.2 : Easy (simple changes, low risk)
- 0.2-0.5 : Medium (some complexity)
- 0.5+ : Hard (complex refactoring, high effort)

### Safety Score (0.0 - 1.0)
How safe is this refactoring:
- 0.9+ : Very safe (no external dependencies)
- 0.7-0.9 : Safe (minimal risk)
- 0.0-0.7 : Risky (may affect other code)

### Confidence Score (0.0 - 1.0)
How confident the engine is in this suggestion:
- 0.9+ : Very confident
- 0.7-0.9 : Confident
- 0.5-0.7 : Moderate confidence
- 0.0-0.5 : Low confidence

## Code Metrics

The engine calculates these metrics for code analysis:

```python
@dataclass
class CodeMetrics:
    lines: int                  # Total lines
    complexity: int             # Cyclomatic complexity
    nesting_depth: int          # Maximum nesting depth
    num_statements: int         # Total statements
    num_variables: int          # Number of variables
    num_parameters: int         # Number of parameters (functions)
    has_return: bool            # Has return statement
```

## Safety Features

### Preview Before Apply
All refactorings support dry-run mode:
```python
# Preview changes
result = engine.apply_refactoring(suggestion, dry_run=True)
print(result['diff'])

# Apply if satisfied
result = engine.apply_refactoring(suggestion, dry_run=False)
```

### AST-Based Analysis
- All analysis uses Python's AST module
- No regex-based pattern matching
- Understands code structure deeply

### Confidence Scores
- Every suggestion includes confidence score
- Filter by confidence threshold:
```python
high_confidence = [s for s in suggestions if s.confidence >= 0.8]
```

### Safety Scores
- Cross-file refactorings have lower safety scores
- Local refactorings have higher safety scores
- Use to assess risk before applying

## Examples

See `example_usage.py` for comprehensive examples of all features:

```bash
python -m api.services.refactoring.example_usage
```

## Performance

### Caching
- File ASTs are cached after first parse
- File contents cached for diff generation
- Symbol locations cached across analyses

### Scalability
- Analyzes ~1000 lines/second per file
- Workspace-wide rename scans all Python files
- Efficient AST traversal using visitor pattern

## Integration

### With LSP
```python
# Provide code actions
def get_code_actions(file_path, line, column):
    engine = get_refactoring_engine()
    suggestions = engine.analyze_file(file_path)

    # Filter to relevant line
    relevant = [
        s for s in suggestions
        if s.location.start_line <= line <= s.location.end_line
    ]

    return relevant
```

### With CI/CD
```python
# Fail build if too many issues found
def check_code_quality(file_path):
    engine = get_refactoring_engine()
    suggestions = engine.analyze_file(file_path)

    high_impact = [
        s for s in suggestions
        if s.impact_score >= 0.7 and s.confidence >= 0.8
    ]

    if len(high_impact) > 5:
        raise Exception(f"Too many refactoring opportunities: {len(high_impact)}")
```

### With Code Review
```python
# Add refactoring suggestions to PR comments
def review_pr(changed_files):
    engine = get_refactoring_engine()

    all_suggestions = []
    for file_path in changed_files:
        suggestions = engine.analyze_file(file_path)
        all_suggestions.extend(suggestions)

    # Sort by impact
    all_suggestions.sort(key=lambda s: s.impact_score, reverse=True)

    return all_suggestions[:10]  # Top 10 suggestions
```

## Testing

The refactoring system includes comprehensive test coverage:

```bash
# Run unit tests
pytest tests/test_refactoring.py

# Run integration tests
pytest tests/test_refactoring_integration.py

# Run example scenarios
python -m api.services.refactoring.example_usage
```

## Future Enhancements

Planned features:
1. **Move to File** - Suggest better file locations for code
2. **Simplify Condition** - Simplify complex boolean conditions
3. **Type Annotation** - Suggest adding type hints
4. **Docstring Generation** - Generate missing docstrings
5. **Performance Optimization** - Suggest performance improvements
6. **Security Fixes** - Detect and fix security issues
7. **Multi-file Refactoring** - Coordinate refactorings across files
8. **Batch Apply** - Apply multiple refactorings at once

## License

Part of MagnetarCode - see main project license.
