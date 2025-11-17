# **gitsummary — Let Your Codebase Explain Itself**

You know the feeling: you open a repo you haven't touched in months—or one you’ve never seen. The commit messages are vague (“fix”, “update”, “wip”), the PR history is scattered across hosting platforms, and the diffs tell you *what* changed but never *why*. 
When you want to ship a release, you start by hunting for signal in a sea of noise. Documentation drifts. And the truth of the system hides inside thousands of commits waiting to be rediscovered.

LLMs know the story when you feed them the diffs, and they are happy to tell you, let's make them do the work for you.

**gitsummary** exists to make this happen.

It turns your Git history into a source of living, structured understanding—something both humans and AI can rely on. By automatically generating semantic metadata for every commit and storing it in Git Notes, gitsummary makes the repository self-descriptive. A codebase that once whispered its intent now *speaks clearly*.

Instead of raw diffs, you get meaning: purpose, intent, architectural consequences, risk, deployment impact, user-facing behavior. These artifacts become durable artifacts used for docs, changelogs, audits, onboarding, and automated tooling. Documentation stays aligned with code. Release notes stop being guesswork.

Developers, architects, SREs, and CI systems all read from the same source of truth: the code itself—enriched, structured, permanent.

**gitsummary is the foundation of the AI-augmented repository.**
A simple CLI. Zero workflow changes. Maximum clarity.

Your codebase already knows its story.
**gitsummary lets it tell it.**

## Installation

The project is intentionally lightweight and has no packaging metadata yet. Install the runtime dependencies and execute directly from the repository:

```bash
pip install -r requirements.txt  # optional if Typer not yet available
python -m gitsummary --help
```

## Usage

### Collecting an artifact

```bash
gitsummary collect --tag v0.1.0 --tag v0.2.0
```

This command fetches pure-git facts for the provided tag range, stores a summarised artifact inside `.gitsummary/artifacts/<ARTIFACT_ID>.json`, and prints the resulting identifier and file path.

### Analysing an artifact

```bash
gitsummary analyze <ARTIFACT_ID> --target implementation
```

Artifacts can be addressed by their full identifier or by an unambiguous prefix. The `--target` flag selects which facet to render to stdout. Available targets can be listed via:

```bash
gitsummary analyze 1234567 --target implementation  # replace with a real prefix
```

### Version information

```bash
gitsummary version
```

Prints the CLI version embedded in artifacts.

## Development

The codebase favours clarity and small focused modules. Each module is documented and covered with docstrings to make future enhancements straightforward.
