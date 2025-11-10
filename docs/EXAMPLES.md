# gitsummary Examples

This document provides practical examples of using gitsummary.

## Basic Usage

### Collecting an Artifact

Collect changes between two tags:

```bash
gitsummary collect v0.1.0 v0.2.0
```

Output:
```
Collecting changes: v0.1.0..v0.2.0
Artifact created: 3fa4c021bc7e9f1f6c3d92da0d98cefd88b3fcd9
```

The artifact is stored in `.gitsummary/artifacts/` and can be analyzed later.

### Analyzing for Deployment

Analyze the deployment facet of an artifact:

```bash
gitsummary analyze 3fa4c021 --target deployment
```

Output (text format):
```
======================================================================
  DEPLOYMENT ANALYSIS
======================================================================

SUMMARY
----------------------------------------------------------------------
Deployment analysis for v0.1.0..v0.2.0, 5 files with new logging, 
3 configuration files changed.

LOGGING
----------------------------------------------------------------------
Impact: medium
New log statements: 5
Affected files: app/main.py, app/utils.py, app/api.py
Notes:
  • 5 file(s) with new logging statements
  • Review log levels (debug/info/warn/error)
  • Ensure sensitive data is not logged

...
```

### JSON Output

Get machine-readable output:

```bash
gitsummary analyze 3fa4c021 --target deployment --format json
```

This outputs structured JSON suitable for CI/CD pipelines or further processing.

### Listing Artifacts

See all stored artifacts:

```bash
gitsummary list
```

Output:
```
Found 3 artifact(s):

  3fa4c021bc7e  2025-11-10T14:30:22
  a1b2c3d4e5f6  2025-11-09T10:15:33
  9876543210ab  2025-11-08T16:45:12
```

## Real-World Scenarios

### Scenario 1: Pre-Deployment Check

Before deploying a release, generate a deployment analysis:

```bash
# Collect artifact
ARTIFACT=$(gitsummary collect v1.2.0 v1.3.0 | grep "Artifact created:" | awk '{print $3}')

# Analyze deployment impact
gitsummary analyze $ARTIFACT --target deployment > deployment-review.txt

# Review the file
cat deployment-review.txt
```

### Scenario 2: CI/CD Integration

In your CI/CD pipeline (e.g., GitHub Actions):

```yaml
name: Release Analysis

on:
  push:
    tags:
      - 'v*'

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0  # Need full history
      
      - name: Install gitsummary
        run: pip install -e .
      
      - name: Collect artifact
        run: |
          PREV_TAG=$(git describe --tags --abbrev=0 HEAD~1)
          CURR_TAG=$(git describe --tags --abbrev=0)
          gitsummary collect $PREV_TAG $CURR_TAG
      
      - name: Generate deployment analysis
        run: |
          ARTIFACT=$(ls -t .gitsummary/artifacts/ | head -1 | sed 's/.json//')
          gitsummary analyze $ARTIFACT --target deployment --format json > analysis.json
      
      - name: Upload analysis
        uses: actions/upload-artifact@v3
        with:
          name: deployment-analysis
          path: analysis.json
```

### Scenario 3: Multiple Repositories

For analyzing changes across multiple repositories:

```bash
#!/bin/bash
# analyze-all.sh

REPOS=("service-a" "service-b" "service-c")
TAG_FROM="v2.0.0"
TAG_TO="v2.1.0"

for repo in "${REPOS[@]}"; do
    echo "Analyzing $repo..."
    cd $repo
    
    ARTIFACT=$(gitsummary collect $TAG_FROM $TAG_TO | grep "Artifact created:" | awk '{print $3}')
    gitsummary analyze $ARTIFACT --target deployment > "../analysis-$repo.txt"
    
    cd ..
done

echo "Analysis complete. Review analysis-*.txt files."
```

### Scenario 4: Historical Analysis

Analyze the last 5 releases:

```bash
#!/bin/bash
# historical-analysis.sh

TAGS=($(git tag --sort=-v:refname | head -6))

for i in {0..4}; do
    TAG_A="${TAGS[$((i+1))]}"
    TAG_B="${TAGS[$i]}"
    
    echo "=== Analyzing $TAG_A to $TAG_B ==="
    
    ARTIFACT=$(gitsummary collect $TAG_A $TAG_B | grep "Artifact created:" | awk '{print $3}')
    gitsummary analyze $ARTIFACT --target deployment
    
    echo ""
done
```

## Understanding Output

### Artifact Structure

An artifact stored in `.gitsummary/artifacts/<OID>.json` contains:

```json
{
  "context": {
    "commit_range": "v0.1.0..v0.2.0",
    "tags": {"start": "v0.1.0", "end": "v0.2.0"},
    "authors": ["Alice <alice@example.com>"],
    "date_range": {"start": "2025-11-01T10:00:00", "end": "2025-11-10T15:30:00"},
    "commit_count": 25,
    "file_count": 12
  },
  "intention": {
    "inferred_goal": "...",
    "inferred_types": ["feature", "bugfix"],
    "affected_subsystems": ["api", "database"]
  },
  "implementation": {
    "files_changed": 12,
    "lines_added": 234,
    "lines_deleted": 67,
    "dependency_changes": ["requirements.txt"]
  },
  "impact": { ... },
  "maintainability": { ... },
  "deployment": { ... },
  "meta": { ... }
}
```

### Deployment Analysis Output

The deployment analyzer provides:

- **Summary**: High-level overview
- **Logging**: New log statements detected
- **Error Handling**: Exception handling changes
- **Configuration**: Config file modifications
- **Infrastructure**: IaC and deployment script changes
- **Risks**: Categorized deployment risks
- **Recommendations**: Actionable deployment guidance
- **Checklist**: Step-by-step deployment checklist

## Advanced Usage

### Custom Ignore Patterns

Add project-specific patterns to `.gitsummaryignore`:

```
# .gitsummaryignore
*.generated.ts
vendor/legacy/
test-fixtures/
```

### Working with Artifact IDs

Artifact IDs support Git-style prefixes:

```bash
# Full ID
gitsummary analyze 3fa4c021bc7e9f1f6c3d92da0d98cefd88b3fcd9 --target deployment

# Short prefix (7+ chars recommended)
gitsummary analyze 3fa4c02 --target deployment

# Even shorter if unambiguous
gitsummary analyze 3fa --target deployment
```

### Repository Path

Analyze a different repository:

```bash
gitsummary collect --repo /path/to/repo v1.0 v2.0
gitsummary analyze --repo /path/to/repo <artifact-id> --target deployment
```

## Tips and Best Practices

1. **Tag Consistently**: Use semantic versioning for tags (v1.0.0, v1.1.0, etc.)

2. **Analyze Early**: Run analysis during feature branches or pull requests

3. **Store Artifacts**: The `.gitsummary/` directory can be committed to track analysis history

4. **Automate**: Integrate into CI/CD for automatic deployment readiness checks

5. **Review Patterns**: Look for trends across multiple artifacts to identify systemic issues

6. **Custom Workflows**: Combine with other tools (jq, grep, awk) for custom reporting

## Troubleshooting

### "Tag not found" error

Ensure tags exist and are fetched:
```bash
git fetch --tags
git tag -l
```

### "No artifacts found"

Make sure you've run `collect` first:
```bash
gitsummary collect <tag-a> <tag-b>
```

### "Ambiguous artifact ID prefix"

Use a longer prefix:
```bash
gitsummary analyze 3fa4c0 --target deployment  # Instead of 3fa
```

### Large diffs timing out

Currently, gitsummary processes all diffs. For very large changes, consider:
- Splitting the range into smaller tag pairs
- Using custom ignore patterns to exclude large generated files
- Future versions will support diff size limits

## Future Capabilities

The POC currently supports basic functionality. Future versions will add:

- Interactive analysis mode with clarification questions
- Additional analyzers (security, performance, etc.)
- LLM integration for advanced intention inference
- Git-native storage backend
- Artifact comparison and trending
- Custom analyzer plugins

