# gitsummary

A proof-of-concept CLI that mines git metadata, stores structured artifacts under `.gitsummary/`, and renders domain specific facets on demand.

## Installation

The project is intentionally lightweight and has no packaging metadata yet. Install the runtime dependencies and execute directly from the repository:

```bash
pip install -r requirements.txt  # optional if Typer not yet available
python -m gitsummary --help
```

## Usage

### Collecting an artifact

```bash
gitsummary collect --tag v0.1.0 v0.2.0
```

This command fetches pure-git facts for the provided tag range, stores a summarised artifact inside `.gitsummary/artifacts/<ARTIFACT_ID>.json`, and prints the resulting identifier and file path.

### Analysing an artifact

```bash
gitsummary analyze <ARTIFACT_ID> --target implementation
```

Artifacts can be addressed by their full identifier or by an unambiguous prefix. The `--target` flag selects which facet to render to stdout. Available targets can be listed via:

```bash
gitsummary analyze 1234567 --target implementation  # replace with a real prefix
```

### Version information

```bash
gitsummary version
```

Prints the CLI version embedded in artifacts.

## Development

The codebase favours clarity and small focused modules. Each module is documented and covered with docstrings to make future enhancements straightforward.
