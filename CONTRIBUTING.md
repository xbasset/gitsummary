# Contributing to gitsummary

Thank you for your interest in contributing to gitsummary!

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd gitsummary
   ```

2. **Install in development mode:**
   ```bash
   pip install -e .
   ```

3. **Verify installation:**
   ```bash
   gitsummary --version
   ```

## Code Quality

This project maintains high code quality standards:

- **KISS Principle:** Keep implementations simple and straightforward
- **Type Hints:** All functions should have proper type annotations
- **Documentation:** All modules, classes, and functions must have docstrings
- **Clean Code:** Follow PEP 8 guidelines

### Code Style

We use:
- **black** for code formatting (line length: 100)
- **ruff** for linting
- **mypy** for type checking

Run checks before committing:
```bash
# Format code
black gitsummary/

# Check types
mypy gitsummary/

# Lint
ruff check gitsummary/
```

## Architecture

### Core Components

1. **git_ops.py** - Pure Git operations wrapper
   - No platform dependencies (GitHub/GitLab APIs)
   - Clean abstractions over GitPython
   - Focus on commit ranges, diffs, and blame

2. **collector.py** - Artifact generation
   - Orchestrates Git operations
   - Structures data according to spec
   - Applies filtering rules

3. **storage.py** - Artifact persistence
   - Manages `.gitsummary/` directory structure
   - Content-addressed storage (SHA-256)
   - Manifest and index management

4. **ignore.py** - File filtering
   - Respects `.gitignore` (via Git)
   - Applies `.gitsummaryignore` patterns
   - Built-in noise filters

5. **analyzers/** - Facet-specific analysis
   - Base analyzer protocol
   - Pluggable architecture
   - Currently: deployment analyzer

6. **cli.py** - Command-line interface
   - Built with Typer
   - Clean, Git-like UX
   - Comprehensive error handling

### Artifact Structure

Each artifact contains these sections:

- **context**: Raw Git data (commits, authors, dates)
- **intention**: Inferred goals and rationale
- **implementation**: Code changes and patterns
- **impact**: User-visible and compatibility changes
- **maintainability**: Tech debt and testing signals
- **deployment**: Ops-relevant insights
- **meta**: Confidence scores and evidence
- **alias**: Reserved for future use

## Adding New Analyzers

To add a new facet analyzer:

1. Create `gitsummary/analyzers/your_analyzer.py`:

```python
from typing import Any, Dict
from gitsummary.analyzers.base import Analyzer

class YourAnalyzer(Analyzer):
    @property
    def name(self) -> str:
        return "your_facet"
    
    def analyze(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        # Your analysis logic here
        return {"results": "..."}
```

2. Register in `gitsummary/analyzers/__init__.py`:

```python
from gitsummary.analyzers.your_analyzer import YourAnalyzer
__all__ = [..., "YourAnalyzer"]
```

3. Add to CLI in `gitsummary/cli.py`:

```python
elif target == "your_facet":
    analyzer = YourAnalyzer()
```

## Testing

Currently, this is a POC without a formal test suite. When adding tests:

1. Place tests in `tests/` directory
2. Use pytest as the test runner
3. Aim for high coverage of critical paths
4. Include integration tests with real Git repos

## Documentation

- Keep module docstrings up to date
- Use clear, descriptive function names
- Add inline comments for complex logic only
- Update README.md for user-facing changes
- Update docs/spec.md for architectural changes

## Pull Request Process

1. Create a feature branch from `main`
2. Implement your changes following code quality guidelines
3. Ensure no linter errors
4. Update documentation as needed
5. Submit PR with clear description
6. Address review feedback

## Questions?

Open an issue for discussion or clarification.

