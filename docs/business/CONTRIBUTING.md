# Contributing to ElohimOS

Thank you for your interest in contributing to **ElohimOS**! This project is built on the conviction that technology should serve people and glorify God. We welcome contributions from developers, designers, documentarians, and anyone passionate about our mission.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Areas for Contribution](#areas-for-contribution)

---

## Code of Conduct

### Our Values

ElohimOS is built on the conviction that:
- **All people are made in the image of God** and deserve dignity and respect
- **Technology should serve, not dominate**
- **Collaboration makes us stronger**
- **Excellence glorifies the Creator**

### Expected Behavior

- Be respectful and considerate in all interactions
- Welcome newcomers and help them learn
- Focus on what's best for the community and mission
- Accept constructive criticism gracefully
- Show empathy toward others

### Unacceptable Behavior

- Harassment, discrimination, or exclusion of any kind
- Personal attacks or inflammatory language
- Trolling or deliberately disruptive behavior
- Publishing others' private information without consent

---

## Getting Started

### Prerequisites

- **macOS 14.0+** (for Metal/ANE features)
- **Python 3.11+**
- **Node.js 18+**
- **Git** and **Git LFS**
- A GitHub account

### First Steps

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/ElohimOS.git
   cd ElohimOS
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/magnetar-ai/ElohimOS.git
   ```
4. **Run the application** to verify everything works:
   ```bash
   ./elohim
   ```

---

## Development Setup

### Backend Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r web_requirements.txt

# Run backend server
cd apps/backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
# Navigate to frontend
cd apps/frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

The frontend will be available at http://localhost:5173 and will proxy API requests to the backend at http://localhost:8000.

---

## Making Changes

### Branching Strategy

1. **Keep your main branch clean**:
   ```bash
   git checkout main
   git pull upstream main
   ```

2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Use descriptive branch names**:
   - `feature/add-export-pdf` — New features
   - `fix/query-timeout-issue` — Bug fixes
   - `docs/update-readme` — Documentation
   - `refactor/optimize-metal-inference` — Code improvements

### Commit Messages

Write clear, descriptive commit messages:

```
Add PDF export functionality

- Implement PDF generation using reportlab
- Add export button to results view
- Include formatting options for tables
- Add unit tests for PDF generation

Closes #123
```

**Format:**
- First line: Brief summary (50 chars or less)
- Blank line
- Detailed explanation if needed
- Reference related issues

---

## Coding Standards

### Python (Backend)

**Style Guide:**
- Follow [PEP 8](https://pep8.org/) style guidelines
- Use [Black](https://black.readthedocs.io/) for formatting
- Maximum line length: 88 characters (Black default)

**Linting:**
```bash
# Format code
make format

# Run linter
make lint

# Strict linting
make lint-strict
```

**Best Practices:**
- Use type hints for function signatures
- Write docstrings for public functions/classes
- Keep functions focused and single-purpose
- Avoid global state when possible

**Example:**
```python
from typing import List, Optional

def process_query(query: str, timeout: Optional[int] = None) -> List[dict]:
    """
    Execute a SQL query and return results.

    Args:
        query: SQL query string
        timeout: Optional timeout in seconds

    Returns:
        List of result rows as dictionaries

    Raises:
        QueryTimeoutError: If query exceeds timeout
        InvalidQueryError: If query syntax is invalid
    """
    # Implementation...
```

### TypeScript/React (Frontend)

**Style Guide:**
- Follow [Airbnb JavaScript Style Guide](https://airbnb.io/javascript/react/)
- Use functional components with hooks
- Prefer TypeScript strict mode

**Best Practices:**
- Use meaningful component and variable names
- Extract reusable logic into custom hooks
- Keep components small and focused
- Use TypeScript for type safety

**Example:**
```typescript
interface QueryResultsProps {
  data: ResultRow[];
  onExport: (format: ExportFormat) => void;
  loading?: boolean;
}

export const QueryResults: React.FC<QueryResultsProps> = ({
  data,
  onExport,
  loading = false,
}) => {
  // Component implementation...
};
```

---

## Testing

### Backend Tests

```bash
# Run Python tests
pytest

# Run with coverage
pytest --cov=apps/backend
```

### Frontend Tests

```bash
# Run JavaScript/TypeScript tests
cd apps/frontend
npm test

# Run with coverage
npm test -- --coverage
```

### Writing Tests

- Write tests for new features
- Update tests when modifying existing features
- Aim for meaningful test coverage, not just high percentages
- Test edge cases and error conditions

---

## Submitting Changes

### Pull Request Process

1. **Update your branch** with the latest changes:
   ```bash
   git checkout main
   git pull upstream main
   git checkout your-feature-branch
   git rebase main
   ```

2. **Push your changes**:
   ```bash
   git push origin your-feature-branch
   ```

3. **Create a Pull Request** on GitHub:
   - Use a clear, descriptive title
   - Reference related issues
   - Describe what changed and why
   - Include screenshots for UI changes
   - Mention any breaking changes

4. **Respond to feedback**:
   - Address reviewer comments promptly
   - Make requested changes in new commits
   - Be open to suggestions and improvements

### Pull Request Template

```markdown
## Description
Brief description of the changes

## Motivation
Why are these changes needed?

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
How were these changes tested?

## Screenshots (if applicable)
[Add screenshots for UI changes]

## Related Issues
Closes #123
Related to #456

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code formatted and linted
- [ ] No breaking changes (or documented if unavoidable)
```

---

## Areas for Contribution

### High Priority

- **Documentation** — Improve guides, add examples, fix typos
- **Testing** — Increase test coverage, add integration tests
- **Accessibility** — Make UI more accessible (WCAG compliance)
- **Performance** — Optimize query performance, reduce memory usage
- **Internationalization** — Add multi-language support

### Feature Ideas

- Additional export formats (PDF, HTML)
- Advanced data visualization options
- Query optimization suggestions
- Collaborative features improvements
- Mobile-responsive UI enhancements

### Good First Issues

Look for issues labeled `good-first-issue` on GitHub. These are beginner-friendly tasks that help you get familiar with the codebase.

---

## Getting Help

### Resources

- **Documentation**: [docs/README.md](README.md)
- **Issues**: [GitHub Issues](https://github.com/magnetar-ai/ElohimOS/issues)
- **Discussions**: [GitHub Discussions](https://github.com/magnetar-ai/ElohimOS/discussions)

### Questions?

- Open a [GitHub Discussion](https://github.com/magnetar-ai/ElohimOS/discussions)
- Check existing issues and documentation
- Reach out to maintainers

---

## Recognition

All contributors will be:
- Listed in our CONTRIBUTORS file
- Acknowledged in release notes
- Part of building technology that serves people and glorifies God

---

## License

By contributing to ElohimOS, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to ElohimOS!**

*Built with conviction. Deployed with compassion. Powered by faith.*
