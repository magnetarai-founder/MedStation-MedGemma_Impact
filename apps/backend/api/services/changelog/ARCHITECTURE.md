# Changelog Generator - Architecture

## Overview

The Changelog Generator is a production-quality system for automatically generating changelogs from git commit history. It follows the Conventional Commits specification and produces Keep a Changelog formatted output.

## Design Principles

1. **Convention over Configuration**: Expects Conventional Commits format but gracefully handles non-conforming commits
2. **Semantic Versioning**: Automatically suggests version bumps based on commit types
3. **User-Focused**: Only includes significant, user-facing changes by default
4. **Extensible**: Optional LLM enhancement for better descriptions
5. **Integration-Friendly**: Designed for CI/CD pipelines and automation

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                       ChangelogGenerator                         │
│                                                                  │
│  ┌────────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ Git Parser     │  │ Categorizer  │  │ Markdown Generator │  │
│  │                │  │              │  │                    │  │
│  │ - parse_commits│→ │ - categorize │→ │ - generate_log    │  │
│  │ - extract_refs │  │ - detect_    │  │ - generate_notes  │  │
│  │ - parse_conv.  │  │   breaking   │  │ - to_markdown     │  │
│  └────────────────┘  └──────────────┘  └────────────────────┘  │
│         ↓                    ↓                    ↓             │
│  ┌────────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ CommitInfo     │  │ ChangelogEntry│ │ Keep a Changelog   │  │
│  │ (dataclass)    │  │ (dataclass)   │  │ Format             │  │
│  └────────────────┘  └──────────────┘  └────────────────────┘  │
│                                                                  │
│  ┌────────────────┐  ┌──────────────┐                          │
│  │ Version Bump   │  │ LLM Enhance  │                          │
│  │ Suggester      │  │ (Optional)   │                          │
│  │                │  │              │                          │
│  │ - suggest_ver. │  │ - enhance_   │                          │
│  │ - bump_rules   │  │   with_llm   │                          │
│  └────────────────┘  └──────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Data Models

#### CommitInfo

Represents a parsed git commit with all relevant metadata.

```python
@dataclass
class CommitInfo:
    hash: str                    # Full SHA
    short_hash: str              # Short SHA (7 chars)
    message: str                 # Original message
    author: str                  # Author name
    email: str                   # Author email
    date: datetime               # Commit timestamp
    type: CommitType             # feat, fix, etc.
    scope: str | None            # Optional scope
    description: str             # Parsed description
    body: str                    # Full commit body
    breaking: bool               # Has breaking changes
    breaking_description: str    # Breaking change details
    issue_refs: list[str]        # Referenced issues
    pr_refs: list[str]          # Referenced PRs
```

**Key Properties**:
- `formatted_description`: Adds scope formatting (e.g., "**api**: description")
- `is_significant`: Determines if commit should appear in changelog

**Significance Rules**:
- Always significant: `feat`, `fix`, `perf`, `revert`
- Significant if breaking: any type with breaking changes
- Not significant: `chore`, `test`, `ci`, `docs`, `style`, `build`

#### ChangelogEntry

Groups commits by type for changelog sections.

```python
@dataclass
class ChangelogEntry:
    type: CommitType
    commits: list[CommitInfo]

    def to_markdown(
        self,
        include_links: bool = True,
        repo_url: str | None = None
    ) -> str
```

**Output Format**:
```markdown
### Features

- **scope**: description ([`hash`](url)) (fixes [#123](url)) (PR [#45](url))
```

#### Enums

```python
class CommitType(str, Enum):
    FEAT = "feat"         # Features → MINOR bump
    FIX = "fix"           # Bug Fixes → PATCH bump
    PERF = "perf"         # Performance → PATCH bump
    # ... others

class VersionBump(str, Enum):
    MAJOR = "major"       # Breaking changes
    MINOR = "minor"       # New features
    PATCH = "patch"       # Bug fixes
    NONE = "none"         # No changes
```

### 2. Parsing System

#### Git Command Execution

```python
def _run_git_command(self, *args: str) -> str:
    """Execute git command safely with error handling"""
```

- Runs in subprocess with proper error handling
- Captures stdout/stderr
- Uses repository working directory
- Raises descriptive exceptions on failure

#### Commit Parsing

```python
def parse_commits(
    self,
    from_ref: str | None = None,
    to_ref: str = "HEAD",
    limit: int | None = None
) -> list[CommitInfo]
```

**Process**:
1. Build git log command with custom format
2. Execute and capture output
3. Split into individual commits
4. Parse each commit's fields
5. Extract conventional commit components
6. Detect breaking changes
7. Extract issue/PR references

**Git Format String**:
```
%H    - Full commit hash
%h    - Short commit hash
%an   - Author name
%ae   - Author email
%at   - Author timestamp (Unix)
%s    - Subject (first line)
%b    - Body (rest of message)
```

#### Conventional Commits Pattern

```python
COMMIT_PATTERN = re.compile(
    r"^(?P<type>\w+)"                    # type
    r"(?:\((?P<scope>[^)]+)\))?"         # (scope)
    r"(?P<breaking>!)?"                  # !
    r":\s+"                              # :
    r"(?P<description>.+)$"              # description
)
```

**Examples**:
- `feat: add feature` → type=feat, scope=None
- `feat(api): add endpoint` → type=feat, scope=api
- `feat!: breaking change` → type=feat, breaking=true
- `feat(auth)!: OAuth 2.0` → type=feat, scope=auth, breaking=true

#### Reference Extraction

```python
ISSUE_PATTERN = re.compile(
    r"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)",
    re.IGNORECASE
)

PR_PATTERN = re.compile(
    r"(?:PR|MR)\s+#?(\d+)",
    re.IGNORECASE
)

BREAKING_CHANGE_PATTERN = re.compile(
    r"^BREAKING[- ]CHANGE:\s+(.+)$",
    re.MULTILINE | re.IGNORECASE
)
```

### 3. Categorization System

```python
def categorize_commits(
    self,
    commits: list[CommitInfo]
) -> dict[CommitType, ChangelogEntry]
```

**Algorithm**:
1. Filter to significant commits only
2. Group by commit type
3. Create ChangelogEntry for each type
4. Preserve commit order within groups

### 4. Version Suggestion

```python
def suggest_version(
    self,
    current_version: str,
    commits: list[CommitInfo] | None = None
) -> tuple[VersionBump, str]
```

**Rules** (in priority order):
1. **MAJOR**: Any breaking changes → x.0.0
2. **MINOR**: Any features (no breaking) → 0.x.0
3. **PATCH**: Any fixes (no features/breaking) → 0.0.x
4. **NONE**: No significant changes → no bump

**Version Parsing**:
- Supports `1.2.3` or `v1.2.3`
- Extracts major.minor.patch components
- Validates semver format

### 5. Changelog Generation

```python
def generate_changelog(
    self,
    from_ref: str | None = None,
    to_ref: str = "HEAD",
    version: str | None = None,
    date: datetime | None = None,
    include_all: bool = False
) -> str
```

**Process**:
1. Parse commits in range
2. Filter to significant (unless `include_all`)
3. Categorize by type
4. Detect breaking changes
5. Build markdown sections in order:
   - Version header
   - Breaking changes (always first)
   - Features
   - Bug Fixes
   - Performance
   - Other types

**Section Order**:
```python
section_order = [
    CommitType.FEAT,       # Features
    CommitType.FIX,        # Bug Fixes
    CommitType.PERF,       # Performance
    CommitType.REFACTOR,   # Refactoring
    CommitType.DOCS,       # Documentation
    CommitType.TEST,       # Tests
    CommitType.BUILD,      # Build
    CommitType.CI,         # CI/CD
    CommitType.CHORE,      # Chores
    CommitType.REVERT,     # Reverts
]
```

### 6. Release Notes Generation

```python
def generate_release_notes(
    self,
    version: str,
    from_ref: str | None = None,
    to_ref: str = "HEAD",
    include_stats: bool = True
) -> str
```

**Sections**:
1. **Header**: Release title
2. **Summary**: High-level overview with counts
3. **Statistics**: Commits, contributors, changes
4. **Changelog**: Full changelog section
5. **Contributors**: List of all contributors

### 7. File Management

```python
async def update_changelog_file(
    self,
    changelog_path: str | Path | None = None,
    from_ref: str | None = None,
    version: str | None = None
) -> None
```

**Algorithm**:
1. Generate new changelog section
2. Read existing CHANGELOG.md (if exists)
3. Insert new section:
   - After header (if header exists)
   - At top (if no header)
4. Write updated content
5. Preserve existing sections

### 8. LLM Enhancement (Optional)

```python
async def enhance_with_llm(
    self,
    commits: list[CommitInfo]
) -> list[CommitInfo]
```

**Process**:
1. For each commit:
   - Build enhancement prompt
   - Call LLM (OllamaClient)
   - Extract improved description
   - Validate length/quality
2. Gracefully handle failures
3. Return enhanced commits

**Prompt Template**:
```
Improve this git commit description for a changelog:

Original: {description}
Type: {type}
Scope: {scope}

Provide a clear, user-friendly description (one sentence, max 100 chars).
Focus on WHAT changed and WHY it matters to users.
Do not include technical implementation details.
```

## Keep a Changelog Format

### Header

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
```

### Version Section

```markdown
## [1.2.0] - 2024-12-20

### BREAKING CHANGES

- **auth**: OAuth 1.0 support removed

### Features

- **api**: add user authentication endpoint ([`a1b2c3d`](url))
- **ui**: add dark mode support ([`e4f5g6h`](url))

### Bug Fixes

- **security**: prevent SQL injection ([`m0n1o2p`](url)) (fixes [#123](url))
```

## Integration Points

### 1. Git Repository

**Requirements**:
- Valid git repository (`.git` directory)
- Accessible git binary
- Proper permissions

**Commands Used**:
- `git log` - Fetch commit history
- `git describe --tags` - Find latest tag

### 2. LLM Client (Optional)

**Interface**:
```python
async def chat(
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 100
) -> dict
```

**Providers**:
- OllamaClient (default)
- Any compatible LLM client

### 3. CI/CD Systems

**GitHub Actions**:
```yaml
- name: Generate Changelog
  run: python cli.py generate --version $VERSION
```

**Integration Points**:
- Tag creation triggers
- Release workflows
- PR checks

## Error Handling

### Git Errors

```python
try:
    result = subprocess.run(["git", ...], check=True)
except subprocess.CalledProcessError as e:
    logger.error(f"Git command failed: {e.stderr}")
    raise Exception(f"Git command failed: {e.stderr}")
```

### Parse Errors

```python
try:
    commit = self._parse_single_commit(raw)
except Exception as e:
    logger.warning(f"Failed to parse commit: {e}")
    continue  # Skip malformed commits
```

### LLM Errors

```python
try:
    enhanced = await llm.chat(...)
except Exception as e:
    logger.warning(f"LLM enhancement failed: {e}")
    return original_commits  # Graceful degradation
```

## Performance Considerations

### Git Operations

- **Cost**: O(n) where n = number of commits
- **Optimization**: Use `limit` parameter
- **Caching**: Consider caching parsed commits

### File I/O

- **CHANGELOG.md**: Entire file read into memory
- **Large files**: May need streaming for very large changelogs
- **Write operations**: Atomic writes recommended

### LLM Enhancement

- **Cost**: O(n) LLM calls, can be slow
- **Optimization**:
  - Batch processing
  - Caching enhanced descriptions
  - Rate limiting
- **Timeout**: Handle timeouts gracefully

## Testing Strategy

### Unit Tests

- Commit parsing (all types)
- Version suggestion (all rules)
- Breaking change detection
- Reference extraction
- Markdown generation

### Integration Tests

- Real repository parsing
- File operations
- LLM enhancement (mocked)

### Test Coverage

```
test_generator.py:
  - TestCommitType (2 tests)
  - TestCommitInfo (5 tests)
  - TestConventionalCommitsParsing (8 tests)
  - TestVersionSuggestion (5 tests)
  - TestChangelogEntry (2 tests)
  - TestIssueAndPRExtraction (3 tests)
  - TestChangelogGeneration (2 tests)

Total: 27 tests
```

## Future Enhancements

### Planned Features

1. **Multi-repository Support**
   - Aggregate changelogs from monorepos
   - Cross-repository references

2. **Custom Templates**
   - User-defined changelog formats
   - Organization-specific styles

3. **Advanced Filtering**
   - Author-based filtering
   - Path-based filtering
   - Date range filtering

4. **Change Categories**
   - Custom category rules
   - Auto-categorization via ML
   - Category aliases

5. **Integration Improvements**
   - GitLab/Bitbucket API integration
   - Automatic issue description fetching
   - PR comment generation

6. **Performance**
   - Incremental parsing
   - Persistent caching
   - Parallel processing

### Technical Debt

- None currently - this is a new, clean implementation

## Security Considerations

### Command Injection

- All git commands use array args (not shell strings)
- No user input directly in git commands
- Repository path validated

### File Operations

- Path validation for CHANGELOG.md
- No arbitrary file writes
- Proper encoding handling (UTF-8)

### LLM Integration

- Prompts sanitized
- Output length validated
- Timeout protection

## Maintenance

### Dependencies

- **Python**: 3.10+
- **Git**: 2.0+
- **Optional**: OllamaClient for LLM enhancement

### Backward Compatibility

- Semver versioning
- Deprecated features logged
- Migration guides provided

### Monitoring

```python
logger.info("Generated changelog with %d commits", len(commits))
logger.warning("Failed to parse commit: %s", error)
logger.error("Git command failed: %s", stderr)
```

## License

Part of MagnetarCode - see project LICENSE.
