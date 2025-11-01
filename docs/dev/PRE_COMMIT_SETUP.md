# Pre-commit Hooks Setup Guide

Pre-commit hooks automatically run code quality checks before each commit, catching issues early in development.

## Quick Start

### 1. Install pre-commit

```bash
# Using pip
pip install pre-commit

# Or using homebrew (macOS)
brew install pre-commit
```

### 2. Install the git hooks

From the project root:

```bash
pre-commit install
```

### 3. Test the hooks

Run all hooks manually against all files:

```bash
pre-commit run --all-files
```

## What Gets Checked

### Python (Backend)
- **Black**: Code formatting (120 char line length)
- **isort**: Import sorting
- **Ruff**: Fast linting (replaces flake8, pylint)
- **Bandit**: Security vulnerability scanning

### TypeScript/JavaScript (Frontend)
- **ESLint**: TypeScript/React linting

### General
- **File hygiene**: Trailing whitespace, end-of-file newlines
- **Large files**: Prevents commits >500KB
- **Merge conflicts**: Detects unresolved markers
- **YAML/JSON**: Syntax validation

## Configuration Files

- `.pre-commit-config.yaml`: Hook configuration
- `pyproject.toml`: Black, isort, ruff, mypy settings
- `.bandit.yml`: Security scanner configuration

## Common Workflows

### Skip hooks for urgent commit
```bash
git commit --no-verify -m "urgent: fix production issue"
```

### Run specific hook
```bash
pre-commit run black --all-files
pre-commit run ruff --all-files
```

### Update hook versions
```bash
pre-commit autoupdate
```

### Bypass hook for specific file
Add to `.pre-commit-config.yaml`:
```yaml
exclude: ^path/to/exclude\.py$
```

## Troubleshooting

### Hook fails with "command not found"
Re-install dependencies:
```bash
pre-commit clean
pre-commit install
```

### Python version mismatch
Update `language_version` in `.pre-commit-config.yaml` to match your Python:
```yaml
language_version: python3.11  # Change to your version
```

### Slow mypy checks
Mypy is commented out by default. To enable:
1. Uncomment the mypy section in `.pre-commit-config.yaml`
2. Run `pre-commit install` again

## Manual Formatting (Without Pre-commit)

If you prefer manual control:

```bash
# Format Python code
black apps/backend --line-length 120

# Sort imports
isort apps/backend --profile black

# Lint Python
ruff check apps/backend --fix

# Security scan
bandit -r apps/backend -c .bandit.yml
```

## CI/CD Integration

Pre-commit can run in CI pipelines:

```yaml
# GitHub Actions example
- uses: actions/checkout@v3
- uses: actions/setup-python@v4
- run: pip install pre-commit
- run: pre-commit run --all-files
```

## Recommended Settings

### For Solo Developers
Keep all hooks enabled for maximum code quality.

### For Teams
- Enable all formatting hooks (black, isort)
- Enable linting (ruff)
- Optional: Enable mypy for typed projects
- Consider adding `no-commit-to-branch` to prevent direct main commits

## Additional Resources

- [Pre-commit documentation](https://pre-commit.com/)
- [Black code style](https://black.readthedocs.io/)
- [Ruff linter](https://github.com/astral-sh/ruff)
- [Bandit security](https://bandit.readthedocs.io/)
