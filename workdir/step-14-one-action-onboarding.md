# Step 14 — One-Action Onboarding: GitHub Release Notes Automation

## Problem

Teams ship fast, but release notes often fail for predictable reasons:

- They’re **manual** (people forget).
- They’re **inconsistent** (style and structure drift).
- They’re **not reviewable** (text lives only in the GitHub UI).
- They’re **high-latency** (someone “does it later”).

We want release notes to be a default outcome of shipping—not a separate manual step.

## UX goal

### One action

Run one command in the repo:

```bash
gitsummary init github-release-notes
```

This command:
- Scaffolds a GitHub Actions workflow
- Creates `release-notes/README.md`
- Forces a local OpenAI key prompt if not present (for local use), and prints the single required CI setup step

### One required follow-up step (because CI is non-interactive)

Add a repo secret:
- `OPENAI_API_KEY`

CI must fail fast if missing. Silent fallback is not acceptable for teams relying on high-quality release notes.

## What happens on every GitHub Release publish

- Compute revision range: previous published Release tag → current Release tag
- `gitsummary analyze <range>` (stores commit artifacts in Git Notes)
- `gitsummary generate release-notes <range> --output release-notes/<tag>.md`
- Update GitHub Release body from `release-notes/<tag>.md`
- Open a PR committing the file (auditable artifact + review flow)

## Design decisions

- **Release body + committed file**: the Release page stays user-facing, while the repo gets a durable artifact that can be reviewed, diffed, and indexed.
- **PR-based persistence**: generated text enters the team’s normal review process.
- **Fail fast on missing secret**: no partial automation. If the system can’t produce the intended quality, it should stop loudly.
- **Core engine remains git-native**: GitHub automation is an opt-in integration layer. The analysis and artifact model remains portable.

## Implementation notes

- CLI command: `gitsummary init github-release-notes`
- Workflow trigger: `release: published` (explicitly tied to what users read)
- Permissions: `contents: write`, `pull-requests: write`
- PR creation: `peter-evans/create-pull-request`

## Follow-ups / future refinements

- Support alternate providers (`anthropic`, `ollama`) via `GITSUMMARY_PROVIDER` and matching secrets.
- Optional “doctor” command to validate repo setup + secrets expectations.
- Allow customizing output path and PR branch naming for org conventions.


