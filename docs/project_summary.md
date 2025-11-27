# Project Summary — Key Insights (Condensed & Structured)

1. Core Vision (Release Manager Focus)

You are building a tool for **Release Managers** and teams who need to extract meaning from a repository’s evolution between two points in time (commits, branches, tags). The primary goal for v0.1 is to produce structured, semantic release notes and internal documentation that describe:
	•	Developer intention
	•	Implementation decisions
	•	User-visible impact (Risk/Breaking Changes)
	•	Before/After behavior

These artifacts become durable metadata living alongside the code.

⸻

2. Constraint: Pure Git Source

You intentionally avoid relying on GitHub/GitLab APIs.
You want this tool to work:
	•	Offline
	•	In any Git hosting environment
	•	Based purely on the git object model, commit metadata, and diffs

This means all semantic inference must come from:
	•	Commit messages
	•	Diffs
	•	File paths/types
	•	Code changes
	•	Repository conventions

**Note on AI/LLM:** We rely on current generation LLMs (large context, reasoning) to bridge the gap between raw diffs and semantic intent ("The Magic Wand").

⸻

3. Artifact Concept

The “artifact” is a structured, semantic representation of a change range.
It is composed of multiple facets. For v0.1, we prioritize:

(a) Context
	•	Commit range, merge points, tags
	•	Authors & timestamps
	•	Summarized commit messages

(b) Intention (Inferred)
	•	Why the change exists
	•	Problem solved

(c) Impact (Risk & Breaking Changes)
	•	User-visible behavior change
	•	Compatibility or migration risks

(d) Meta
	•	Artifact ID, Schema version, Confidence

*(Other facets like Deployment, Maintainability, and SRE specific details are deferred to future versions).*

⸻

4. Artifact Storage Direction

You want storage to be Git-native and to work out of the box using Git Notes, so artifacts can be:
	•	Versioned
	•	Pushed/pulled
	•	Garbage-collection safe
	•	Inspectable with standard Git commands

The core idea:
	•	Use the Git Notes mechanism as the primary integration point.
	•	Define a clear, stable data model for the artifacts that lives in notes.

⸻

5. CLI Design (Two-Phase: Analyze → Generate)

(a) Analyze (Semantic Extraction):
	`gitsummary analyze v1.0..v2.0`
	→ Reads commits, uses LLM to extract semantic understanding, stores artifacts in Git Notes.

(b) Generate (Report Production):
	`gitsummary generate changelog v1.0..v2.0`
	`gitsummary generate release-notes v1.0..v2.0`
	→ Consumes stored artifacts to produce human-readable reports.

**Why this naming?**
- `analyze` is industry-standard (semantic-release, static analyzers)
- `generate` is standard for changelog tools (git-cliff, git-chglog)
- Clear two-phase mental model: expensive analysis once, cheap generation many times

⸻

6. Long-Term Strategy

You see this project as:
	•	A future Git-native extension
	•	A stable base for AI agents cooperating across commits and time
	•	A cross-cutting tool for release management

*See `docs/future_plans.md` for extended scope regarding Developers, SREs, and Agents.*

⸻

7. Values & Philosophy

Key philosophical choices:
	•	Prefer semantic understanding over raw diffs
	•	Favor portability and minimal dependencies
	•	Emphasize project durability over ephemeral tooling
	•	Invest heavily in artifact schema design (this is the hard part).
