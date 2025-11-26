# Step 2: Artifact Schema Design
Version: 1.0
Date: 2025-11-26

## Objective
Define the data model for the "Artifact" that represents the semantic understanding of a code change.

## Key Decisions

### 1. Granularity: 1:1 with Commits
**Decision:** Artifacts will be generated and stored **per commit**, rather than grouping them into "features" at the collection stage.
**Rationale:**
- **Simplicity:** The Collector just iterates history; no complex grouping logic needed upfront.
- **Versatility:** Grouping and aggregation happen at the **Generator** (Analyze) stage. This allows the same raw artifacts to be sliced and diced in different ways (e.g., "Release Notes" vs. "Audit Log").
- **Deep Signal:** Allows the AI to focus on the specific intent and impact of a single atomic change ("reading between the lines").

### 2. Schema Structure (Pydantic)
**Decision:** Use `Pydantic` models to define the schema strictly.
**Fields:**
- **Identity:** `commit_hash`, `schema_version`
- **Intent:** `intent_summary` (AI-corrected message), `category` (Feature, Fix, etc.)
- **Behavior:** `behavior_before` vs `behavior_after` (Crucial for release notes)
- **Impact:** `impact_scope` (Public API, Internal, etc.), `is_breaking`, `risk_explanation`
- **Implementation:** `technical_highlights` (Key decisions found in diff)

### 3. Data vs Procedures
**Decision:** **Store Artifacts as Data**.
**Rationale:**
- **Context Window:** We cannot process 500 commits in one prompt. We must "Map" (collect artifacts) then "Reduce" (generate report).
- **Performance:** Pay the AI tax once during collection. Reporting is instant.

## Artifacts Created
- `gitsummary/schema.py`: The Pydantic model definition.
- `gitsummary/artifact.py`: Updated to use the new schema.

## Next Steps
- **Step 3:** Design Git Notes Storage Layout.
