# Step 12 – Release-note helper for latest tag

## Goal
Ship an end-to-end `gitsummary release-note latest` flow that fetches tags, analyzes missing commits, and produces Markdown + HTML release notes for the newest tag.

## Decisions
- Require a clean worktree up front; bail with guidance instead of running on dirty trees.
- Select latest tag by annotated date (fallback to creation date); error when no tags exist.
- Range selection: `prev..latest` when two+ tags exist; otherwise include all commits reachable from the lone tag (root → tag).
- Interactive UX shows commit coverage, prompts to analyze missing artifacts, and confirms output directory creation; `--yes` skips prompts.
- Generate release notes via existing ReporterService; store YAML in Git Notes and render Markdown to stdout plus HTML to `<repo>/release-notes/<tag>.html`.
- Default to opening the HTML file unless `--no-open` is passed.

## Open items
- Consider allowing explicit range overrides (e.g., `--range` or `--since <tag>`).
- Add template customization for the HTML skin in a follow-up.
