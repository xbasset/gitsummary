Release guide using `manage_release.py`
=======================================

Overview
--------
`manage_release.py` is a non-interactive helper to calculate the next version, bump the version file, create a commit on `main` (by default), and push an annotated tag via the GitHub API using the `gh` CLI.

Prerequisites
-------------
- `gh` is installed and authenticated for the target repo (`gh auth login`).
- Local clone is up to date on the release branch (default `main`).
- Environment configured with:
  - `RELEASE_REPO` as `owner/repo` (or pass `--repo`).
  - Optional: `RELEASE_BRANCH` (default `main`), `RELEASE_VERSION_FILE` (default `pyproject.toml`), `RELEASE_COMMIT_TEMPLATE`, `RELEASE_TAG_TEMPLATE`.
- For this repo, set `--version-file gitsummary/__init__.py` (or export `RELEASE_VERSION_FILE`).

Modes
-----
- `--publish-release` : Next stable = bump minor of latest stable, reset patch to 0 (vA.B.C → vA.(B+1).0).
- `--publish-alpha`   : Next alpha for upcoming minor (vA.B.C → vA.(B+1).0-alpha.N, incrementing N).
- `--promote-alpha vX.Y.Z-alpha.N` : Strip `-alpha.N` to produce stable vX.Y.Z using the alpha’s commit/merge-base.
- `--emergency-version-override vX.Y.Z[-alpha.N|-beta.N]` : Force a specific version.
- Add `--dry-run` to compute and log without creating blobs/trees/commits/tags.

Typical flows
-------------
Dry-run publish release:
```
python manage_release.py --publish-release --dry-run --repo xbasset/gitsummary --version-file gitsummary/__init__.py
```

Dry-run publish alpha:
```
python manage_release.py --publish-alpha --dry-run --repo xbasset/gitsummary --version-file gitsummary/__init__.py
```

Promote an alpha to stable (dry-run):
```
python manage_release.py --promote-alpha v0.2.0-alpha.3 --dry-run --repo xbasset/gitsummary --version-file gitsummary/__init__.py
```

Real publish (no `--dry-run`):
```
python manage_release.py --publish-release --repo xbasset/gitsummary --version-file gitsummary/__init__.py
```

What the tool does
------------------
1) Lists repo tags via `gh api` and computes the target version per mode rules (supports `vX.Y.Z[-alpha.N|-beta.N]`).  
2) Resolves the base commit (`main` head, or merge-base for `--promote-alpha`).  
3) Reads the version file at that commit from GitHub, replaces exactly one `version` or `__version__` assignment.  
4) (Non-dry-run) Creates blob → tree → commit (`Release <version>`) → annotated tag (`Release <version>`) → tag ref.  
5) Prints `version=...`, `commit_sha=...`, `tag_sha=...` on success.

Failure cases to expect
-----------------------
- Missing mode or invalid semver input.
- No valid stable tags when required.
- Version file update hits 0 or multiple occurrences.
- GitHub API errors (reported with method/path/status text).

Notes
-----
- The script uses GitHub REST via `gh api`; no local git mutations occur.  
- CI is expected to build/publish on tag push; this script only creates the commit and tag.  
- Adjust branch/version file via flags or env vars without modifying the script.  
- GitHub “Releases” are separate from tags. This tool creates annotated tags only. To surface under Releases:
  - UI: Releases → Draft a new release → pick the tag (e.g., `v0.3.0-alpha.1`) → publish.
  - CLI: `gh release create v0.3.0-alpha.1 --notes "Release v0.3.0-alpha.1"` (add `--prerelease` if appropriate).
  - You can automate this in CI (on tag push) by running `gh release create` after your build/publish step.  

gitsummary automated release notes (recommended)
----------------------------------------------

If you publish GitHub Releases, you can fully automate release notes generation with **one command**:

```bash
gitsummary init github-release-notes
```

What this installs:
- A GitHub Actions workflow triggered on **Release published**
- A `release-notes/` directory for persisted markdown artifacts

What happens on every release:
- Computes the revision range (previous published release → current tag)
- Runs `gitsummary analyze <range>`
- Generates `release-notes/<tag>.md`
- Updates the GitHub Release body from that file
- Opens a PR committing the file back into the repo (auditable + reviewable)

### Required setup (CI)

Because CI is non-interactive, this workflow **fails fast** if the OpenAI key is missing:
- Add a repo secret named `OPENAI_API_KEY` in GitHub Actions.

Optional CLI:

```bash
gh secret set OPENAI_API_KEY --body "<your-key>"
```

### Works with `manage_release.py`

`manage_release.py` creates tags (and optionally the commit/tag), but it does not publish a GitHub Release.
To trigger the workflow, you need to publish a Release for that tag (UI or `gh release create ...`).

Version bumps on main (no Release)
---------------------------------

If you want the repository version to move forward on every merge to `main` without creating tags or Releases,
enable the workflow `.github/workflows/bump-version-on-main.yml`.

This workflow bumps `gitsummary/__init__.py` from `X.Y.Z` to `X.Y.(Z+1)` and pushes a commit to `main`.
Releases remain manual and are not triggered by this bump.

GitHub Actions workflow example
-------------------------------
This sample workflow builds with `uv`, publishes to PyPI (or another index), and creates a GitHub Release for every `v*.*.*` tag. Adjust names, secrets, and publish command to your environment.

Save as `.github/workflows/release.yml`:
```yaml
name: Release

on:
  push:
    tags:
      - "v*.*.*"

permissions:
  contents: write  # needed for gh release and uploading assets
  id-token: write  # if using trusted publishing; otherwise remove

env:
  UV_PUBLISH_TOKEN: ${{ secrets.UV_PUBLISH_TOKEN }} # or PYPI_TOKEN depending on your setup

jobs:
  build-and-publish:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install uv
        run: pip install uv

      - name: Install dependencies
        run: uv sync --all-extras

      - name: Build artifacts
        run: uv build

      # Replace with your publish command (uv publish, twine, etc.)
      - name: Publish to PyPI
        env:
          UV_PUBLISH_TOKEN: ${{ secrets.UV_PUBLISH_TOKEN }}
        run: uv publish --token "$UV_PUBLISH_TOKEN"

      - name: Create GitHub Release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          TAG="${GITHUB_REF##*/}"
          gh release create "$TAG" \
            --notes "Release $TAG" \
            dist/*
```

Notes for the workflow:
- If you use PyPI trusted publishing, swap `uv publish --token ...` with the trust-based flow and keep `id-token: write`.
- Adjust `dist/*` to match your build output location; remove if you do not upload assets.
- The workflow triggers on tags pushed by `manage_release.py`; no manual branch push needed.  
