# gitsummary Architecture

This document describes the architecture and design decisions for gitsummary POC.

## Overview

`gitsummary` is built around three core concepts:

1. **Collection**: Extract pure Git data and structure it semantically
2. **Storage**: Persist artifacts in a content-addressed store
3. **Analysis**: Generate facet-specific insights from stored artifacts

## Design Principles

### KISS (Keep It Simple, Stupid)

Every component does one thing well:
- `git_ops.py`: Git operations only
- `collector.py`: Data structuring only
- `storage.py`: Persistence only
- `analyzers/`: Analysis only

### Host-Agnostic

No dependencies on:
- GitHub/GitLab/Bitbucket APIs
- Platform-specific features
- External services

Everything works from the Git repository alone.

### Future-Ready

The POC uses a filesystem-based storage that mirrors a future Git-native implementation:
- Content-addressed artifacts (SHA-256)
- Manifest and index structure
- Schema versioning

## Module Hierarchy

```
gitsummary/
├── __init__.py          # Package metadata
├── cli.py               # User interface (Typer)
├── collector.py         # Orchestration layer
├── git_ops.py           # Git abstraction layer
├── storage.py           # Persistence layer
├── ignore.py            # Filtering layer
└── analyzers/           # Analysis layer
    ├── base.py          # Protocol definition
    └── deployment.py    # Deployment facet
```

### Layer Responsibilities

#### CLI Layer (`cli.py`)

**Responsibility**: User interaction and output formatting

- Argument parsing and validation
- Command routing
- Output formatting (text/JSON)
- Error handling and user feedback

**Dependencies**: All other modules

#### Orchestration Layer (`collector.py`)

**Responsibility**: Coordinate data collection and artifact construction

- Drive Git operations
- Apply filtering rules
- Structure data according to spec
- Calculate derived metrics

**Dependencies**: `git_ops`, `ignore`

#### Git Layer (`git_ops.py`)

**Responsibility**: Pure Git operations

- Commit enumeration
- Diff extraction
- Blame information
- Tag resolution

**Dependencies**: GitPython only

#### Storage Layer (`storage.py`)

**Responsibility**: Artifact persistence

- Content-addressed storage (SHA-256)
- Manifest management
- Index maintenance
- Schema version tracking

**Dependencies**: None (stdlib only)

#### Filtering Layer (`ignore.py`)

**Responsibility**: Determine which files to include

- Parse ignore patterns
- Apply built-in noise filters
- Support custom `.gitsummaryignore`

**Dependencies**: pathspec library

#### Analysis Layer (`analyzers/`)

**Responsibility**: Generate facet-specific insights

- Load artifacts
- Extract relevant data
- Apply domain logic
- Format results

**Dependencies**: None (operate on artifact dicts)

## Data Flow

### Collection Flow

```
User Input (tags)
    ↓
CLI validates input
    ↓
Collector orchestrates:
    ├→ GitRepository.get_commits_between()
    ├→ GitRepository.get_diff_between()
    └→ IgnoreFilter.filter_files()
    ↓
Collector builds artifact structure
    ↓
Storage saves artifact
    ↓
Returns artifact ID to user
```

### Analysis Flow

```
User Input (artifact ID + facet)
    ↓
CLI validates input
    ↓
Storage loads artifact
    ↓
CLI selects analyzer
    ↓
Analyzer processes artifact
    ↓
CLI formats output
    ↓
Results to stdout
```

## Artifact Schema

### Top-Level Structure

```json
{
  "context": { ... },         // Git facts
  "intention": { ... },       // Inferred semantics
  "implementation": { ... },  // Code changes
  "impact": { ... },          // User-facing effects
  "maintainability": { ... }, // Tech debt signals
  "deployment": { ... },      // Ops-relevant data
  "meta": { ... },           // Confidence & evidence
  "alias": null              // Reserved
}
```

### Section Purposes

- **context**: Directly from Git (high confidence)
- **intention**: Heuristic-based inference (low confidence in POC)
- **implementation**: Git diffs + pattern detection (high confidence)
- **impact**: Pattern-based inference (medium confidence)
- **maintainability**: Pattern-based inference (medium confidence)
- **deployment**: Pattern-based detection (medium confidence)
- **meta**: Schema version, tool version, evidence references

### Confidence Levels

Each section in `meta.confidence` indicates data quality:

- **high**: Directly from Git, no inference
- **medium**: Pattern-based heuristics, generally reliable
- **low**: Simple keyword matching, requires human review

Future versions will improve low-confidence sections with LLM integration.

## Storage Format

### Directory Structure

```
.gitsummary/
├── artifacts/              # Content-addressed artifact store
│   └── <SHA256>.json      # Full artifact
├── manifests/             # Tag range → artifact mappings
│   └── by-range/
│       └── A..B.json      # Pointer to artifact
├── index/                 # Quick lookups
│   └── latest.json        # Most recent artifact
├── schema/                # Schema version
│   └── version            # "0.1.0"
└── notes/                 # Reserved for future
    └── summary/
```

### Artifact Identity

Artifacts are identified by SHA-256 hash of their JSON content:

```python
artifact_id = sha256(json.dumps(artifact, sort_keys=True))
```

This provides:
- Content-addressable storage
- Deduplication (same content = same ID)
- Integrity verification
- Git-compatible model

### Prefix Resolution

Like Git, artifact IDs support prefix matching:

```bash
# Full ID
gitsummary analyze deb060dc33831024355692b963963cf5620dc33bc7b03ea48624df4816b0efa7

# Short prefix (unambiguous)
gitsummary analyze deb060dc
```

## Analyzer Architecture

### Protocol

All analyzers implement the `Analyzer` protocol:

```python
class Analyzer(ABC):
    @property
    def name(self) -> str:
        """Facet name"""
        
    def analyze(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        """Process artifact, return insights"""
```

### Deployment Analyzer

The deployment analyzer focuses on operational readiness:

**Inputs** (from artifact):
- New logging patterns
- Error handling changes
- Configuration modifications
- Infrastructure changes

**Outputs**:
- Summary
- Logging analysis
- Error handling analysis
- Configuration analysis
- Infrastructure analysis
- Risk assessment
- Recommendations
- Deployment checklist

**Design**: Conservative and checklist-oriented

### Adding New Analyzers

1. Create `analyzers/your_analyzer.py`
2. Inherit from `Analyzer`
3. Implement `name` and `analyze()`
4. Register in `analyzers/__init__.py`
5. Add to CLI router in `cli.py`

## Error Handling

### Strategy

- **Fail fast**: Invalid tags, missing artifacts → immediate error
- **Clear messages**: Git-like error output
- **Graceful degradation**: Missing blame data → continue without it

### Error Categories

1. **User Input Errors**: Invalid tags, bad artifact IDs
   - Report clearly, suggest fixes
   
2. **Git Errors**: Repository issues, permission problems
   - Pass through Git's error messages
   
3. **Internal Errors**: Unexpected exceptions
   - Catch at CLI level, provide traceback in debug mode

## Performance Considerations

### POC Constraints

The POC prioritizes correctness over performance:
- No diff size limits
- No incremental processing
- Full artifact loading

### Future Optimizations

When needed:
- Stream large diffs
- Lazy-load artifact sections
- Cache intermediate results
- Parallel analysis

## Testing Strategy

### POC Testing

Manual testing via:
- Real repository test cases
- Example workflows in docs
- CLI smoke tests

### Future Testing

When adding test suite:
- Unit tests for each module
- Integration tests with sample repos
- E2E tests for full workflows
- Property-based testing for storage

## Extension Points

### Designed for Future Enhancement

1. **LLM Integration**
   - Intention inference
   - Impact analysis
   - Recommendation generation

2. **Git-Native Storage**
   - Use Git notes for attachment
   - Store in refs/summary/*
   - Push/pull support

3. **Interactive Mode**
   - Clarification questions
   - Iterative refinement
   - Session storage

4. **Plugin System**
   - Custom analyzers
   - Custom collectors
   - Custom output formats

5. **Historical Analysis**
   - Trend detection
   - Artifact comparison
   - Project-wide metrics

## Code Quality Standards

### Type Safety

All functions have type hints:
```python
def collect(self, tag_a: str, tag_b: str) -> Dict[str, Any]:
    ...
```

### Documentation

All public APIs have docstrings:
```python
def collect(self, tag_a: str, tag_b: str) -> Dict[str, Any]:
    """
    Collect an artifact for the range between two tags.
    
    Args:
        tag_a: Starting tag (exclusive).
        tag_b: Ending tag (inclusive).
        
    Returns:
        Complete artifact dictionary.
    """
```

### Simplicity

- Short functions (< 50 lines preferred)
- Clear naming
- Single responsibility
- Minimal nesting

### Consistency

- PEP 8 compliance (via black)
- 100 character line length
- Type annotations required
- Docstring format consistent

## Security Considerations

### Current Scope

POC assumes trusted repository:
- No input sanitization beyond type checking
- No sandboxing of Git operations
- No rate limiting

### Production Requirements

Before production use:
- Validate all Git refs
- Sanitize file paths
- Limit resource usage (memory, time)
- Audit log access
- Consider sensitive data in logs/diffs

## Conclusion

This architecture prioritizes:
1. **Simplicity**: Easy to understand and modify
2. **Correctness**: Reliable Git data extraction
3. **Extensibility**: Clear extension points
4. **Future-proofing**: Migration path to Git-native backend

The POC demonstrates feasibility while maintaining high code quality and clear separation of concerns.

