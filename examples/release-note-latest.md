# Example: release-note latest

Command:
```bash
gitsummary release-note latest --no-llm
```

Sample output (abbreviated):
```
[OK] Detecting repository root
[OK] Reading tags
[OK] Computing commit range
[OK] Analyzing 3 commit(s) in v1.2.2..v1.2.3 (heuristic only)

# myproj v1.2.3 — 2025-12-06

*Various improvements and fixes.*

Highlights:
- Add retries to webhook delivery
- Reduce startup time for CLI
- Fix broken pagination in /users API
```

Tip: add `--reanalyze` to force fresh analysis or `--llm` with a configured provider for richer summaries.
