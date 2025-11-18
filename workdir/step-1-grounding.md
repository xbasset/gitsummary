# Step 1: Ground the Problem & Constraints
Version: 1.0
Date: 2025-11-18

## Objective
- Align on the project vision, constraints, and users so later schema/CLI work rests on solid context.

## Reviewed Sources
- `docs/project_summary.md` (vision, Git-only constraint, artifact facets, Git Notes storage direction).
- `docs/why.md` (goals, motivations, explicit/implicit goals, target user list).

## Constraints / Non-negotiables
- Use only Git metadata and diffs; operate offline with no hosting APIs.
- Keep artifacts portable in Git Notes (versioned, GC-safe, inspectable).
- Build the CLI in Python with Typer; keep outputs stable for downstream tooling.
- Document semantics and behavior in the docs (spec + TODO plan).

## Target Users & Jobs (Refined)
**Primary Focus (v0.1): Release Managers**
- **Job:** Create release notes and internal documentation from Tag A to Tag B.
- **Pain:** Reading hundreds of vague commit messages to understand "What actually changed?" and "What is the risk?".
- **Solution:**
    1. **Builder:** `gitsummary collect` builds a semantic database (artifacts) from git history using LLM inference to capture intent.
    2. **Generator:** `gitsummary analyze` generates the human-readable report.

*Secondary/Future Users (See `docs/future_plans.md`):*
- Developers (Onboarding/Context)
- SRE/Ops (Deployment configs)
- AI Agents (Automated context)

## Tasks
- [x] Review the foundational docs listed above.
- [x] Capture any additional constraints or goals beyond the current docs.
- [x] List and confirm the top jobs-to-be-done per key user group.
- [x] Draft a concise, 1–2 paragraph problem statement and add it to the docs/README.
- [x] Identify the right doc location or structure for the problem statement (README + Project Summary).
- [x] Update `docs/current_development_status.md`.
