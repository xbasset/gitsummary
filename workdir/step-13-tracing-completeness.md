# Step 13 – Tracing completeness

## Goal
Tighten tracing so every CLI flow leaves a consistent record of generated outputs (Git Notes, files, stdout) for downstream debugging and analytics.

## Decisions
- Centralize release note Git Notes logging inside `save_release_note()` to avoid duplicated hooks and ensure all callers emit an output reference.
- Trace generated report destinations via `_write_output()` with metadata for format and revision range, including stdout-only runs.
- Emit trace references for HTML feed generation to capture file locations alongside Git Note writes.
- Cover the new hooks with targeted pytest cases that monkeypatch the trace manager rather than touching real git notes.

## Open items
- Add tracing for any future interactive prompts outside `release-note`.
- Consider a lightweight trace viewer command to inspect recent `.gitsummary/*.log` files.
