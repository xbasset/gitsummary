# Step 11 – Artifact Feed HTML

## Goal
Ship a playful, mobile-friendly HTML feed that lets developers scroll through analyzed commits and nudges them to analyze missing ones.

## Decisions
- Added `gitsummary generate feed <range>` that writes `<project>-feed.html` by default (override with `--output`). `--skip-unanalyzed` hides missing artifacts; by default they are shown as CTAs.
- Feed model: `ArtifactFeedReport`/`FeedItem` (service-level) reuses `CommitInfo` + `CommitArtifact`, keeps derived stats (total, analyzed, missing, breaking, category/impact counts).
- Renderer: inline CSS/JS, sticky header stats, gradient background, badge styling, and copy-to-clipboard CTAs. Missing artifacts render friendly prompts with `gitsummary analyze <sha>` or range-level `gitsummary analyze <range>`.
- CTA tone: make “analyze me” a fun invitation, not an error.

## Implementation Notes
- New builder in `gitsummary/reporters/feed.py`; exposed via `ReporterService.generate_artifact_feed`.
- New renderer `gitsummary/renderers/html_feed.py` for a self-contained HTML page (no external assets).
- CLI wiring in `gitsummary generate feed` with optional `--open`.
- Default slug uses repo name sanitized for filesystem safety.

## Testing
- Added unit tests for feed builder, renderer CTA rendering, and CLI command writing the default file. Tests currently require dependencies from `requirements.txt`.
