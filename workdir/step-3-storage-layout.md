# Step 3: Storage Layout Design
Version: 1.0
Date: 2025-11-26

## Objective
Decide how to store `CommitArtifact` JSON objects in Git Notes.

## Key Decisions

### 1. Namespace: `refs/notes/intent`
**Decision:** Use a dedicated namespace `refs/notes/intent`.
**Rationale:**
- **Native Feel:** Pairs perfectly with `git commit`. A commit records the *change*; this note records the *intent*.
- **No Branding:** Avoids tool-specific names like `gitsummary` in the user's repo.

### 2. Attachment: Direct to Commit
**Decision:** Attach notes directly to the **Commit Object**.
**Rationale:**
- **Standard:** This is the native way Git Notes work.
- **Simplicity:** No need for synthetic "Range Objects" or complex indexing for v0.1.
- **O(1) Lookup:** `git notes show <COMMIT_HASH>` is instant.

### 3. Format: YAML (Validated via Pydantic)
**Decision:** Store as **YAML**, validate via **Pydantic**.
**Rationale:**
- **Storage:** YAML is readable and token-efficient.
- **Validation:** Pydantic ensures strict schema enforcement regardless of serialization format.

## Artifacts Created
- `docs/storage_layout.md`: The detailed specification.

## Next Steps
- **Step 4:** CLI Surface Design (Defining the commands).
- **Step 7:** Wire Artifacts into Git Notes (Implementation).
