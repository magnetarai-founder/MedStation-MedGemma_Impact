# Changelog Generator Service

A comprehensive changelog generation system for MagnetarCode that parses git commit history, categorizes commits using Conventional Commits format, and generates professional changelogs in Keep a Changelog format.

## Features

- **Conventional Commits Parsing**: Automatically parses commit messages following the [Conventional Commits](https://www.conventionalcommits.org/) specification
- **Commit Categorization**: Groups commits by type (feat, fix, docs, refactor, etc.)
- **Breaking Change Detection**: Identifies breaking changes via `!` marker or `BREAKING CHANGE:` footer
- **Semantic Versioning**: Suggests version bumps (major, minor, patch) based on commit types
- **Keep a Changelog Format**: Generates changelogs following the [Keep a Changelog](https://keepachangelog.com/) standard
- **Issue/PR Linking**: Automatically links to GitHub/GitLab issues and pull requests
- **Release Notes**: Generates comprehensive release notes with statistics
- **LLM Enhancement**: Optional LLM-powered enhancement of commit descriptions
- **File Management**: Updates existing CHANGELOG.md files intelligently

## Installation

No additional dependencies required beyond the standard MagnetarCode backend dependencies.

## Quick Start

```python
from services.changelog import ChangelogGenerator

# Initialize generator
generator = ChangelogGenerator(
    repo_path="/path/to/your/repo",
    repo_url="https://github.com/username/repo"
)

# Parse recent commits
commits = generator.parse_commits(limit=50)

# Generate changelog
changelog = generator.generate_changelog(version="1.2.0")
print(changelog)

# Suggest version bump
bump, new_version = generator.suggest_version("1.1.0", commits)
print(f"Suggested version: {new_version} ({bump})")

# Generate release notes
release_notes = generator.generate_release_notes(version="1.2.0")

# Update CHANGELOG.md file
await generator.update_changelog_file(version="1.2.0")
```

## Conventional Commits Format

The system expects commits to follow the Conventional Commits format:

```
<type>[optional scope][optional !]: <description>

[optional body]

[optional footer(s)]
```

### Supported Types

| Type       | Display Name              | Changelog Section | Version Bump |
|------------|---------------------------|-------------------|--------------|
| `feat`     | Features                  | ✅ Yes            | MINOR        |
| `fix`      | Bug Fixes                 | ✅ Yes            | PATCH        |
| `docs`     | Documentation             | ⚠️  Optional      | -            |
| `style`    | Styles                    | ⚠️  Optional      | -            |
| `refactor` | Code Refactoring          | ⚠️  Optional      | -            |
| `perf`     | Performance Improvements  | ✅ Yes            | PATCH        |
| `test`     | Tests                     | ⚠️  Optional      | -            |
| `build`    | Build System              | ⚠️  Optional      | -            |
| `ci`       | Continuous Integration    | ⚠️  Optional      | -            |
| `chore`    | Chores                    | ⚠️  Optional      | -            |
| `revert`   | Reverts                   | ✅ Yes            | PATCH        |

### Breaking Changes

Breaking changes trigger a MAJOR version bump and can be indicated in two ways:

1. **Exclamation mark**: `feat!: remove deprecated API`
2. **Footer**:
   ```
   feat: update authentication

   BREAKING CHANGE: OAuth 1.0 support removed
   ```

### Examples

```bash
# Feature with scope
feat(api): add user authentication endpoint

# Bug fix with issue reference
fix(security): prevent SQL injection vulnerability

Fixes #123

# Breaking change with exclamation
feat(auth)!: migrate to OAuth 2.0

# Breaking change with footer
feat(api): update response format

BREAKING CHANGE: API now returns JSON instead of XML

# Multiple references
fix(db): optimize query performance

Closes #45, #67
PR #89
```

## API Reference

### `ChangelogGenerator`

Main service class for changelog generation.

#### Constructor

```python
ChangelogGenerator(
    repo_path: str | Path | None = None,
    llm_client = None,
    repo_url: str | None = None
)
```

**Parameters:**
- `repo_path`: Path to git repository (defaults to current directory)
- `llm_client`: Optional OllamaClient for LLM-enhanced descriptions
- `repo_url`: Repository URL for generating links (e.g., `https://github.com/user/repo`)

#### Methods

##### `parse_commits()`

Parse git commits into structured CommitInfo objects.

```python
commits = generator.parse_commits(
    from_ref="v1.0.0",  # Optional: starting reference
    to_ref="HEAD",       # Ending reference
    limit=100            # Optional: max commits to parse
)
```

**Returns:** `list[CommitInfo]`

##### `categorize_commits()`

Categorize commits by type.

```python
categorized = generator.categorize_commits(commits)
# Returns: dict[CommitType, ChangelogEntry]
```

##### `detect_breaking_changes()`

Extract commits with breaking changes.

```python
breaking = generator.detect_breaking_changes(commits)
# Returns: list[CommitInfo]
```

##### `suggest_version()`

Suggest semantic version bump based on commits.

```python
bump, new_version = generator.suggest_version(
    current_version="1.2.3",
    commits=commits  # Optional: uses unreleased if None
)
# Returns: (VersionBump, str)
```

**Version Bump Rules:**
- Breaking changes → MAJOR (1.2.3 → 2.0.0)
- New features → MINOR (1.2.3 → 1.3.0)
- Bug fixes → PATCH (1.2.3 → 1.2.4)
- No changes → NONE (1.2.3 → 1.2.3)

##### `generate_changelog()`

Generate complete changelog in Keep a Changelog format.

```python
changelog = generator.generate_changelog(
    from_ref="v1.0.0",      # Optional: starting reference
    to_ref="HEAD",          # Ending reference
    version="1.1.0",        # Optional: version string
    date=datetime.now(),    # Optional: release date
    include_all=False       # Include all commits or just significant
)
# Returns: str (Markdown)
```

##### `generate_release_notes()`

Generate release notes for a specific version.

```python
release_notes = generator.generate_release_notes(
    version="1.2.0",
    from_ref="v1.1.0",
    to_ref="HEAD",
    include_stats=True  # Include commit statistics
)
# Returns: str (Markdown)
```

##### `update_changelog_file()`

Update CHANGELOG.md file with new entries.

```python
await generator.update_changelog_file(
    changelog_path=None,    # Defaults to repo_root/CHANGELOG.md
    from_ref="v1.0.0",
    version="1.1.0"
)
```

##### `enhance_with_llm()`

Enhance commit descriptions using LLM.

```python
enhanced_commits = await generator.enhance_with_llm(commits)
# Returns: list[CommitInfo]
```

### Data Classes

#### `CommitInfo`

Parsed commit information.

```python
@dataclass
class CommitInfo:
    hash: str                           # Full commit hash
    short_hash: str                     # Short hash (7 chars)
    message: str                        # Original commit message
    author: str                         # Author name
    email: str                          # Author email
    date: datetime                      # Commit date
    type: CommitType                    # Commit type (feat, fix, etc.)
    scope: str | None                   # Optional scope
    description: str                    # Parsed description
    body: str                           # Commit body
    breaking: bool                      # Has breaking changes
    breaking_description: str           # Breaking change description
    issue_refs: list[str]               # Referenced issues
    pr_refs: list[str]                  # Referenced PRs
```

**Properties:**
- `formatted_description`: Description with scope formatting
- `is_significant`: Whether commit should appear in changelog

#### `ChangelogEntry`

Categorized changelog entry.

```python
@dataclass
class ChangelogEntry:
    type: CommitType
    commits: list[CommitInfo]
```

**Methods:**
- `to_markdown(include_links=True, repo_url=None)`: Convert to markdown

### Enums

#### `CommitType`

```python
class CommitType(str, Enum):
    FEAT = "feat"
    FIX = "fix"
    DOCS = "docs"
    STYLE = "style"
    REFACTOR = "refactor"
    PERF = "perf"
    TEST = "test"
    BUILD = "build"
    CI = "ci"
    CHORE = "chore"
    REVERT = "revert"
    UNKNOWN = "unknown"
```

**Properties:**
- `display_name`: Human-readable section name

#### `VersionBump`

```python
class VersionBump(str, Enum):
    MAJOR = "major"  # x.0.0
    MINOR = "minor"  # 0.x.0
    PATCH = "patch"  # 0.0.x
    NONE = "none"    # No bump
```

## Examples

### Example 1: Generate Changelog for Release

```python
from services.changelog import ChangelogGenerator
from datetime import datetime

generator = ChangelogGenerator(
    repo_path="/path/to/repo",
    repo_url="https://github.com/user/repo"
)

# Generate changelog for version 2.0.0
changelog = generator.generate_changelog(
    from_ref="v1.0.0",
    to_ref="HEAD",
    version="2.0.0",
    date=datetime(2024, 12, 20)
)

print(changelog)
```

**Output:**

```markdown
## [2.0.0] - 2024-12-20

### BREAKING CHANGES

- **auth**: migrate to OAuth 2.0 ([`a1b2c3d`](https://github.com/user/repo/commit/a1b2c3d))

### Features

- **api**: add user authentication endpoint ([`e4f5g6h`](https://github.com/user/repo/commit/e4f5g6h))
- **ui**: add dark mode support ([`i7j8k9l`](https://github.com/user/repo/commit/i7j8k9l))

### Bug Fixes

- **security**: prevent SQL injection vulnerability ([`m0n1o2p`](https://github.com/user/repo/commit/m0n1o2p)) (fixes [#123](https://github.com/user/repo/issues/123))
```

### Example 2: Automated Version Bumping

```python
# Get current version from git tags
current_version = generator._run_git_command("describe", "--tags", "--abbrev=0")

# Get unreleased commits
commits = generator.parse_commits(from_ref=current_version)

# Suggest next version
bump, new_version = generator.suggest_version(current_version, commits)

print(f"Current: {current_version}")
print(f"Suggested: {new_version} ({bump.value} bump)")

# If breaking changes exist
if bump == VersionBump.MAJOR:
    print("⚠️  WARNING: Breaking changes detected!")
```

### Example 3: Release Notes with Statistics

```python
release_notes = generator.generate_release_notes(
    version="2.0.0",
    from_ref="v1.0.0",
    include_stats=True
)

# Outputs:
# # Release 2.0.0
#
# ## Summary
# This release contains 1 breaking change(s). Please review carefully.
# This release includes 5 new feature(s) and 3 bug fix(es).
#
# ## Statistics
# - Total commits: 23
# - Contributors: 4
# - New features: 5
# - Bug fixes: 3
# - Breaking changes: 1
# ...
```

### Example 4: Update CHANGELOG.md Automatically

```python
async def update_changelog():
    generator = ChangelogGenerator()

    # Get latest tag
    latest_tag = generator._run_git_command("describe", "--tags", "--abbrev=0")

    # Update changelog with unreleased changes
    await generator.update_changelog_file(
        from_ref=latest_tag,
        version="Unreleased"
    )

    print("✓ CHANGELOG.md updated with unreleased changes")

# Run in async context
import asyncio
asyncio.run(update_changelog())
```

### Example 5: LLM-Enhanced Descriptions

```python
from services.ollama_client import OllamaClient

# Initialize with LLM support
llm = OllamaClient()
generator = ChangelogGenerator(llm_client=llm)

# Parse commits
commits = generator.parse_commits(limit=10)

# Enhance descriptions
enhanced = await generator.enhance_with_llm(commits)

# Compare
for orig, enh in zip(commits, enhanced):
    print(f"Original: {orig.description}")
    print(f"Enhanced: {enh.description}\n")
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Generate Changelog

on:
  push:
    tags:
      - 'v*'

jobs:
  changelog:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0  # Full history for changelog

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Generate Release Notes
        run: |
          python -c "
          import asyncio
          from services.changelog import ChangelogGenerator

          async def main():
              gen = ChangelogGenerator(
                  repo_url='https://github.com/${{ github.repository }}'
              )

              tag = '${{ github.ref_name }}'
              version = tag.lstrip('v')

              # Get previous tag
              prev_tag = gen._run_git_command('describe', '--tags', '--abbrev=0', f'{tag}^')

              # Generate release notes
              notes = gen.generate_release_notes(
                  version=version,
                  from_ref=prev_tag,
                  to_ref=tag
              )

              # Save to file
              with open('RELEASE_NOTES.md', 'w') as f:
                  f.write(notes)

          asyncio.run(main())
          "

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          body_path: RELEASE_NOTES.md
```

## Best Practices

### 1. Commit Message Guidelines

Train your team to write good commit messages:

```bash
# Good
feat(api): add user profile endpoint with avatar support
fix(auth): prevent token expiration race condition
docs(readme): add installation instructions for Docker

# Bad
update stuff
fix bug
wip
```

### 2. Use Pre-commit Hooks

Validate commit messages before they're committed:

```bash
#!/bin/bash
# .git/hooks/commit-msg

commit_msg=$(cat "$1")

if ! echo "$commit_msg" | grep -qE "^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?: .+"; then
    echo "Error: Commit message doesn't follow Conventional Commits format"
    echo "Format: type(scope): description"
    exit 1
fi
```

### 3. Automate Changelog Updates

Run changelog generation on every release:

```python
# scripts/release.py
async def release(version: str):
    generator = ChangelogGenerator()

    # Update changelog
    await generator.update_changelog_file(version=version)

    # Generate release notes
    notes = generator.generate_release_notes(version=version)

    # Commit and tag
    subprocess.run(["git", "add", "CHANGELOG.md"])
    subprocess.run(["git", "commit", "-m", f"chore: release {version}"])
    subprocess.run(["git", "tag", f"v{version}"])
    subprocess.run(["git", "push", "--follow-tags"])
```

### 4. Semantic Versioning Rules

Follow these rules for version bumps:

- **MAJOR**: Breaking changes (API changes, removed features)
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### 5. Keep Changelog Clean

Only include user-facing changes in changelogs:

- ✅ Include: feat, fix, perf, breaking changes
- ❌ Exclude: chore, test, ci, style (unless significant)

## Troubleshooting

### No commits found

**Problem**: `parse_commits()` returns empty list

**Solutions**:
1. Check git repository exists: `(repo_path / ".git").exists()`
2. Verify git is installed: `which git`
3. Check commit range: Ensure `from_ref` exists

### Version parsing failed

**Problem**: `suggest_version()` raises "Invalid version format"

**Solution**: Ensure version follows semver format: `1.2.3` or `v1.2.3`

### LLM enhancement fails

**Problem**: `enhance_with_llm()` raises connection error

**Solutions**:
1. Check Ollama is running: `curl http://localhost:11434`
2. Verify model is available: `ollama list`
3. Use try/except for graceful degradation

## Performance Considerations

- **Large repositories**: Use `limit` parameter to parse fewer commits
- **LLM enhancement**: Can be slow; use sparingly or cache results
- **File I/O**: `update_changelog_file()` reads entire file into memory
- **Git operations**: Each git command spawns a subprocess

## Future Enhancements

- [ ] Support for GitLab/Bitbucket commit formats
- [ ] Automatic issue/PR description fetching
- [ ] Changelog templating system
- [ ] Multi-language support
- [ ] Change categorization rules customization
- [ ] Integration with semantic-release
- [ ] Changelog diff generation
- [ ] Automated release scheduling

## License

Part of MagnetarCode - see project LICENSE for details.

## Contributing

When contributing to this service:

1. Follow Conventional Commits format
2. Add tests for new features
3. Update this README
4. Run example_usage.py to verify functionality
