# Changelog Generator - Quick Start Guide

## 30-Second Start

```python
from services.changelog import ChangelogGenerator

# Create generator
gen = ChangelogGenerator(repo_url="https://github.com/user/repo")

# Generate changelog
changelog = gen.generate_changelog(version="1.0.0")
print(changelog)
```

## Common Tasks

### 1. Generate Changelog for Release

```python
from services.changelog import ChangelogGenerator

gen = ChangelogGenerator(
    repo_path="/path/to/repo",
    repo_url="https://github.com/user/repo"
)

# Generate changelog from last tag to HEAD
changelog = gen.generate_changelog(
    from_ref="v1.0.0",
    version="1.1.0"
)

# Save to file
with open("RELEASE_NOTES.md", "w") as f:
    f.write(changelog)
```

### 2. Suggest Next Version

```python
gen = ChangelogGenerator()

# Get commits since last release
commits = gen.parse_commits(from_ref="v1.0.0")

# Get suggestion
bump, new_version = gen.suggest_version("1.0.0", commits)
print(f"Next version: {new_version} ({bump.value} bump)")
```

### 3. Update CHANGELOG.md

```python
import asyncio
from services.changelog import ChangelogGenerator

async def update():
    gen = ChangelogGenerator(repo_url="https://github.com/user/repo")

    await gen.update_changelog_file(
        from_ref="v1.0.0",
        version="1.1.0"
    )

asyncio.run(update())
```

### 4. CLI Usage

```bash
# List recent commits
python cli.py list --limit 10

# Generate changelog
python cli.py generate --version 1.1.0 --from v1.0.0

# Generate release notes
python cli.py release --version 1.1.0 --from v1.0.0 -o RELEASE.md

# Suggest version
python cli.py suggest --current 1.0.0

# Update CHANGELOG.md
python cli.py update --version 1.1.0 --from v1.0.0
```

## Conventional Commits Cheatsheet

### Format

```
<type>[(scope)][!]: <description>

[optional body]

[optional footer]
```

### Types

| Type       | When to Use                    | Changelog | Version |
|------------|--------------------------------|-----------|---------|
| `feat`     | New feature                    | Yes       | MINOR   |
| `fix`      | Bug fix                        | Yes       | PATCH   |
| `docs`     | Documentation only             | No        | -       |
| `style`    | Formatting, whitespace         | No        | -       |
| `refactor` | Code refactoring               | No        | -       |
| `perf`     | Performance improvement        | Yes       | PATCH   |
| `test`     | Adding tests                   | No        | -       |
| `build`    | Build system changes           | No        | -       |
| `ci`       | CI configuration               | No        | -       |
| `chore`    | Maintenance, dependencies      | No        | -       |

### Breaking Changes

**Method 1: Exclamation mark**
```
feat!: remove deprecated API endpoints
```

**Method 2: Footer**
```
feat: update authentication

BREAKING CHANGE: OAuth 1.0 support removed
```

### Examples

```bash
# Simple feature
feat: add user authentication

# Feature with scope
feat(api): add JWT token validation

# Bug fix with issue reference
fix(security): prevent SQL injection vulnerability

Closes #123

# Breaking change
feat(auth)!: migrate to OAuth 2.0

BREAKING CHANGE: OAuth 1.0 endpoints removed.
See migration guide for details.

# Multiple references
fix(db): optimize query performance

Fixes #45, #67
PR #89
```

## Configuration

### Repository URL Formats

```python
# GitHub
repo_url="https://github.com/owner/repo"

# GitLab
repo_url="https://gitlab.com/owner/repo"

# Bitbucket
repo_url="https://bitbucket.org/owner/repo"

# GitHub Enterprise
repo_url="https://github.company.com/owner/repo"
```

### LLM Enhancement

```python
from services.ollama_client import OllamaClient

# Initialize with LLM
llm = OllamaClient()
gen = ChangelogGenerator(llm_client=llm)

# Enhance commit descriptions
commits = gen.parse_commits(limit=10)
enhanced = await gen.enhance_with_llm(commits)
```

## Output Examples

### Changelog Output

```markdown
## [1.1.0] - 2024-12-20

### Features

- **api**: add user authentication endpoint ([`a1b2c3d`](url))
- **ui**: add dark mode support ([`e4f5g6h`](url))

### Bug Fixes

- **security**: prevent SQL injection ([`m0n1o2p`](url)) (fixes [#123](url))
```

### Release Notes Output

```markdown
# Release 1.1.0

## Summary

This release includes 2 new feature(s) and 1 bug fix(es).

## Statistics

- Total commits: 15
- Contributors: 3
- New features: 2
- Bug fixes: 1

## Changelog

[Full changelog here]

## Contributors

Thank you to all contributors:
- Alice Johnson
- Bob Smith
- Carol Williams
```

## Troubleshooting

### "Not a git repository"

```python
# Ensure you're in a git repo or specify path
gen = ChangelogGenerator(repo_path="/path/to/repo")
```

### "Invalid version format"

```python
# Version must be semver format
gen.suggest_version("1.2.3", commits)  # Good
gen.suggest_version("v1.2.3", commits) # Also good
gen.suggest_version("1.2", commits)    # Bad - must be x.y.z
```

### LLM Enhancement Fails

```python
# LLM is optional - will gracefully degrade
try:
    enhanced = await gen.enhance_with_llm(commits)
except:
    enhanced = commits  # Use original
```

## Integration Recipes

### GitHub Actions

```yaml
name: Release

on:
  push:
    tags: ['v*']

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0

      - name: Generate Release Notes
        run: |
          TAG=${GITHUB_REF#refs/tags/}
          PREV_TAG=$(git describe --tags --abbrev=0 ${TAG}^)
          python cli.py release \
            --version ${TAG#v} \
            --from $PREV_TAG \
            -o RELEASE_NOTES.md

      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          body_path: RELEASE_NOTES.md
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/commit-msg

msg=$(cat "$1")

if ! echo "$msg" | grep -qE "^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?: .+"; then
    echo "Error: Commit message must follow Conventional Commits format"
    echo ""
    echo "Format: type(scope): description"
    echo ""
    echo "Types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert"
    exit 1
fi
```

### Release Script

```python
#!/usr/bin/env python3
"""Automated release script"""

import asyncio
import subprocess
import sys
from services.changelog import ChangelogGenerator

async def release(version: str):
    gen = ChangelogGenerator(repo_url="https://github.com/user/repo")

    # Update changelog
    latest_tag = gen._run_git_command("describe", "--tags", "--abbrev=0")
    await gen.update_changelog_file(
        from_ref=latest_tag,
        version=version
    )

    # Commit and tag
    subprocess.run(["git", "add", "CHANGELOG.md"])
    subprocess.run(["git", "commit", "-m", f"chore: release {version}"])
    subprocess.run(["git", "tag", f"v{version}"])
    subprocess.run(["git", "push", "--follow-tags"])

    print(f"✓ Released version {version}")

if __name__ == "__main__":
    asyncio.run(release(sys.argv[1]))
```

## Best Practices

1. **Write Good Commit Messages**
   - Be specific and descriptive
   - Use present tense ("add feature" not "added feature")
   - Reference issues/PRs when relevant

2. **Use Scopes Consistently**
   - Define scopes for your project (api, ui, db, etc.)
   - Use the same scopes across commits
   - Keep scopes short and memorable

3. **Mark Breaking Changes Clearly**
   - Always use `!` or `BREAKING CHANGE:`
   - Explain what broke and how to migrate
   - Include examples if possible

4. **Automate Where Possible**
   - Use pre-commit hooks to validate commits
   - Generate changelogs automatically on release
   - Integrate with CI/CD pipelines

5. **Review Before Publishing**
   - Generated changelogs may need editing
   - Add context or examples where helpful
   - Consider using LLM enhancement for clarity

## Need Help?

- **Documentation**: See [README.md](README.md) for full documentation
- **Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
- **Examples**: See [example_usage.py](example_usage.py) for code examples
- **Tests**: Run `python test_generator.py` to see tests

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│                  CONVENTIONAL COMMITS                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Format:   type(scope): description                         │
│                                                              │
│  Breaking: type(scope)!: description                        │
│            OR body with "BREAKING CHANGE: ..."              │
│                                                              │
│  Types:    feat fix docs style refactor                     │
│            perf test build ci chore revert                  │
│                                                              │
│  Example:  feat(api): add user authentication               │
│            fix(security): prevent SQL injection             │
│            feat!: remove deprecated endpoints               │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                    VERSION BUMPING                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  MAJOR:  Breaking changes      (1.0.0 → 2.0.0)             │
│  MINOR:  New features          (1.0.0 → 1.1.0)             │
│  PATCH:  Bug fixes             (1.0.0 → 1.0.1)             │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                   COMMON COMMANDS                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  List:     python cli.py list --limit 20                   │
│  Generate: python cli.py generate --version 1.0.0          │
│  Release:  python cli.py release --version 1.0.0           │
│  Suggest:  python cli.py suggest --current 1.0.0           │
│  Update:   python cli.py update --version 1.0.0            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```
