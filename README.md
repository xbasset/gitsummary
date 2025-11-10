# gitsummary

A Python-based CLI tool for collecting and analyzing Git change sets between tags.

## Overview

`gitsummary` collects pure-git-derived information between two Git tags and generates structured artifacts representing the semantic meaning of change sets. These artifacts can then be analyzed for domain-specific facets like deployment impact.

## Features

- **Pure Git**: No platform dependencies (GitHub/GitLab APIs)
- **Artifact Collection**: Generate structured JSON artifacts from Git commits
- **Facet Analysis**: Analyze artifacts for specific aspects (e.g., deployment)
- **Host-Agnostic**: Works with any Git repository

## Installation

### Development Installation

```bash
# Clone the repository
git clone <repository-url>
cd gitsummary

# Install in development mode
pip install -e .
```

### Dependencies

- Python 3.8+
- GitPython >= 3.1.40
- Typer >= 0.9.0
- pathspec >= 0.11.0

## Usage

### Collect an artifact

```bash
gitsummary collect --tag v0.1.0 v0.2.0
```

This will:
- Collect all commits between the two tags
- Generate a structured artifact
- Store it in `.gitsummary/artifacts/`
- Output: `Artifact created: <ART_OID>`

### Analyze an artifact

```bash
gitsummary analyze <ART_OID> --target deployment
```

This will analyze the artifact for deployment-related insights and print results to stdout.

## Project Structure

```
gitsummary/
├── gitsummary/
│   ├── __init__.py              # Package initialization
│   ├── cli.py                   # CLI entry point (Typer)
│   ├── git_ops.py               # Git operations (GitPython wrapper)
│   ├── collector.py             # Artifact collection logic
│   ├── storage.py               # Storage backend (.gitsummary/)
│   ├── ignore.py                # Ignore rules handling
│   ├── py.typed                 # Type checking marker
│   └── analyzers/
│       ├── __init__.py          # Analyzer exports
│       ├── base.py              # Base analyzer protocol
│       └── deployment.py        # Deployment analyzer
├── docs/
│   └── spec.md                  # Full specification
├── pyproject.toml               # Project configuration
├── README.md                    # This file
└── .gitignore                   # Git ignore rules
```

## Architecture

### Core Components

1. **GitOperations** (`git_ops.py`): Pure Git operations using GitPython
   - Commit extraction
   - Diff analysis
   - Blame data collection

2. **ArtifactCollector** (`collector.py`): Builds structured artifacts
   - Context extraction
   - Intention inference (heuristic-based)
   - Implementation analysis
   - Impact assessment
   - Maintainability signals
   - Deployment detection

3. **Storage** (`storage.py`): Manages artifact persistence
   - SHA-256 content-addressed storage
   - Manifest management
   - Index tracking

4. **Analyzers** (`analyzers/`): Facet-specific analysis
   - Extensible architecture
   - Deployment analyzer included

### Artifact Schema

Each artifact contains:
- `context`: Commit range, authors, dates, branches
- `intention`: Inferred goal and rationale
- `implementation`: Files changed, LOC, patterns, dependencies
- `impact`: User-visible changes, compatibility risks
- `maintainability`: Tech debt, tests, ownership
- `deployment`: Logging, config, infrastructure changes
- `meta`: Confidence scores, evidence references, schema version
- `alias`: Reserved for future use

## Development

### Setup

```bash
# Install in development mode
pip install -e .

# Verify installation
gitsummary --version
```

### Running

```bash
# Show help
gitsummary --help

# Collect an artifact
gitsummary collect --tag v0.1.0 v0.2.0

# Analyze deployment facet
gitsummary analyze <ART_OID> --target deployment

# Analyze with markdown output
gitsummary analyze <ART_OID> --target deployment --format markdown
```

### Code Quality

The project follows best practices:
- Type hints throughout
- Comprehensive docstrings
- Clean architecture with separation of concerns
- KISS principle (Keep It Simple, Stupid)

## Design Principles

- **Pure Git**: No platform dependencies (GitHub/GitLab APIs)
- **Host-Agnostic**: Works with any Git repository
- **Extensible**: Analyzer architecture ready for plugins
- **Simple**: Clean, maintainable code following KISS principles

## Limitations (POC)

- Tags only (no branch/SHA support yet)
- Heuristic-based intention inference (no LLM)
- No AST parsing
- Determinism not required
- Analyzer outputs to stdout only

## Future Roadmap

- Support for broader Git references (branches, SHAs)
- LLM-based intention inference
- Additional analyzers (impact, maintainability)
- Git-native storage backend
- Interactive analysis mode
- Plugin system for custom analyzers

## License

MIT

