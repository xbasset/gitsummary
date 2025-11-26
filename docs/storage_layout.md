# Storage Layout Specification
Version: 0.1.0
Date: 2025-11-26

## Overview
**gitsummary** uses [Git Notes](https://git-scm.com/docs/git-notes) to store semantic artifacts directly in the `.git` directory. This ensures that the "Why" (the artifact) travels with the "What" (the commit) when pushed/pulled, without polluting the commit message or file tree.

## 1. Storage Location
- **Namespace:** `refs/notes/intent`
- **Object Attachment:** Notes are attached directly to the **Commit Object** they analyze.

## 2. Data Format
The content of the note is a UTF-8 encoded **YAML** string.
**Validation:** The YAML content must strictly conform to the `CommitArtifact` Pydantic model defined in `gitsummary/schema.py`. This ensures type safety and schema validation despite the storage format being YAML.

### Example Note Content
```yaml
commit_hash: a1b2c3d4...
schema_version: 0.1.0
intent_summary: Fixes a null pointer exception in the user login flow...
category: fix
behavior_before: Users could not login if...
behavior_after: Users can now login with...
impact_scope: internal
is_breaking: false
risk_explanation: null
technical_highlights:
  - Used regex for validation
  - Added unit test
confidence_score: 0.95
```

## 3. Operations

### Writing (Collect)
- **Command:** `git notes --ref=intent add -f -m <YAML_STRING> <COMMIT_HASH>`
- **Behavior:** Overwrites any existing note for that commit in the `intent` namespace.
- **Idempotency:** Rerunning `collect` on the same commit will regenerate and replace the artifact.

### Reading (Analyze/Show)
- **Command:** `git notes --ref=intent show <COMMIT_HASH>`
- **Fallback:** If no note exists, the system treats the commit as "unanalyzed".

### Transport (Push/Pull)
- **Push:** `git push origin refs/notes/intent`
- **Fetch:** `git fetch origin refs/notes/intent:refs/notes/intent`

## 4. Indexing & Lookup
- **Primary Index:** The Git Object Database itself.
- **Lookup:** `Artifact(CommitHash)` is O(1) via `git notes show`.
- **Range Queries:** To find all artifacts in `A..B`, the system:
    1. Lists commits in `A..B`.
    2. Batches `git notes show` calls (or uses `git log --show-notes=gitsummary --format=%N`) to retrieve artifacts.

## 5. Constraints
- **Size:** Git Notes are blob objects. They handle large JSONs fine, but we should aim to keep artifacts under 100KB for performance.
- **Merge Conflicts:** If two users analyze the same commit differently and push, Git Notes merge strategies apply (default is usually union or manual). For v0.1, "last write wins" (force overwrite) is acceptable.
