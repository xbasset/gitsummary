"""
CLI entry point using Typer.

Provides the main command-line interface for gitsummary.
"""

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from gitsummary import __version__
from gitsummary.analyzers import DeploymentAnalyzer
from gitsummary.collector import ArtifactCollector
from gitsummary.storage import ArtifactStorage

app = typer.Typer(
    name="gitsummary",
    help="Collect and analyze Git change sets between tags.",
    add_completion=False,
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"gitsummary version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", callback=version_callback, help="Show version and exit."),
    ] = None,
) -> None:
    """gitsummary - Collect and analyze Git change sets."""
    pass


@app.command()
def collect(
    tag_a: Annotated[str, typer.Argument(help="Starting tag (exclusive)")],
    tag_b: Annotated[str, typer.Argument(help="Ending tag (inclusive)")],
    repo_path: Annotated[
        Optional[Path],
        typer.Option("--repo", "-r", help="Path to Git repository (default: current directory)"),
    ] = None,
) -> None:
    """
    Collect an artifact for changes between two tags.

    Extracts pure Git data (commits, diffs, metadata) between TAG_A and TAG_B
    and generates a structured artifact stored in .gitsummary/

    Example:
        gitsummary collect --tag v0.1.0 v0.2.0
    """
    try:
        # Initialize collector and storage
        collector = ArtifactCollector(repo_path)
        storage = ArtifactStorage(collector.git_repo.repo_path)

        # Show what we're collecting
        typer.echo(f"Collecting changes: {tag_a}..{tag_b}")

        # Collect the artifact
        artifact = collector.collect(tag_a, tag_b)

        # Save to storage
        artifact_id = storage.save_artifact(artifact, tag_a, tag_b)

        # Output result
        typer.echo(f"Artifact created: {artifact_id}")

    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        if "--debug" in sys.argv:
            raise
        raise typer.Exit(code=1)


@app.command()
def analyze(
    artifact_id: Annotated[str, typer.Argument(help="Artifact ID or prefix")],
    target: Annotated[
        str,
        typer.Option("--target", "-t", help="Target facet to analyze (e.g., 'deployment')"),
    ] = "deployment",
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: 'json' or 'text'"),
    ] = "text",
    repo_path: Annotated[
        Optional[Path],
        typer.Option("--repo", "-r", help="Path to Git repository (default: current directory)"),
    ] = None,
) -> None:
    """
    Analyze a stored artifact for a specific facet.

    Loads an artifact by ID (or prefix) and produces facet-specific analysis.
    Currently supported facets: deployment

    Example:
        gitsummary analyze 3fa4c021 --target deployment
    """
    try:
        # Determine repo path
        if repo_path is None:
            repo_path = Path.cwd()

        # Initialize storage
        storage = ArtifactStorage(repo_path)

        # Load artifact
        artifact = storage.load_artifact(artifact_id)
        if artifact is None:
            typer.echo(f"Error: Artifact '{artifact_id}' not found", err=True)
            raise typer.Exit(code=1)

        # Select analyzer
        if target == "deployment":
            analyzer = DeploymentAnalyzer()
        else:
            typer.echo(f"Error: Unknown target '{target}'", err=True)
            typer.echo("Supported targets: deployment", err=True)
            raise typer.Exit(code=1)

        # Run analysis
        analysis = analyzer.analyze(artifact)

        # Output results
        if format == "json":
            typer.echo(json.dumps(analysis, indent=2, ensure_ascii=False))
        else:
            # Text format (human-readable)
            _print_analysis_text(analysis, analyzer.name)

    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        if "--debug" in sys.argv:
            raise
        raise typer.Exit(code=1)


@app.command()
def list(
    repo_path: Annotated[
        Optional[Path],
        typer.Option("--repo", "-r", help="Path to Git repository (default: current directory)"),
    ] = None,
) -> None:
    """
    List all stored artifacts.

    Shows artifact IDs and creation timestamps.
    """
    try:
        # Determine repo path
        if repo_path is None:
            repo_path = Path.cwd()

        # Initialize storage
        storage = ArtifactStorage(repo_path)

        # List artifacts
        artifacts = storage.list_artifacts()

        if not artifacts:
            typer.echo("No artifacts found.")
            return

        typer.echo(f"Found {len(artifacts)} artifact(s):\n")
        for art in artifacts:
            typer.echo(f"  {art['artifact_id'][:12]}  {art['created_at']}")

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)


def _print_analysis_text(analysis: dict, facet_name: str) -> None:
    """
    Print analysis in human-readable text format.

    Args:
        analysis: Analysis results dictionary.
        facet_name: Name of the facet being analyzed.
    """
    typer.echo(f"\n{'=' * 70}")
    typer.echo(f"  {facet_name.upper()} ANALYSIS")
    typer.echo(f"{'=' * 70}\n")

    # Summary
    if "summary" in analysis:
        typer.echo("SUMMARY")
        typer.echo("-" * 70)
        typer.echo(analysis["summary"])
        typer.echo()

    # Logging
    if "logging" in analysis:
        logging = analysis["logging"]
        typer.echo("LOGGING")
        typer.echo("-" * 70)
        typer.echo(f"Impact: {logging['impact']}")
        typer.echo(f"New log statements: {logging['new_log_statements']}")
        if logging.get("affected_files"):
            typer.echo(f"Affected files: {', '.join(logging['affected_files'][:5])}")
        if logging.get("notes"):
            typer.echo("Notes:")
            for note in logging["notes"]:
                typer.echo(f"  • {note}")
        typer.echo()

    # Error Handling
    if "error_handling" in analysis:
        error = analysis["error_handling"]
        typer.echo("ERROR HANDLING")
        typer.echo("-" * 70)
        typer.echo(f"Impact: {error['impact']}")
        typer.echo(f"Modified files: {error['modified_files']}")
        if error.get("notes"):
            typer.echo("Notes:")
            for note in error["notes"]:
                typer.echo(f"  • {note}")
        typer.echo()

    # Configuration
    if "configuration" in analysis:
        config = analysis["configuration"]
        typer.echo("CONFIGURATION")
        typer.echo("-" * 70)
        typer.echo(f"Impact: {config['impact']}")
        typer.echo(f"Files changed: {config['files_changed']}")
        if config.get("files"):
            typer.echo("Files:")
            for f in config["files"]:
                typer.echo(f"  • {f}")
        if config.get("notes"):
            typer.echo("Notes:")
            for note in config["notes"]:
                typer.echo(f"  • {note}")
        typer.echo()

    # Infrastructure
    if "infrastructure" in analysis:
        infra = analysis["infrastructure"]
        typer.echo("INFRASTRUCTURE")
        typer.echo("-" * 70)
        typer.echo(f"Impact: {infra['impact']}")
        typer.echo(f"Files changed: {infra['files_changed']}")
        if infra.get("files"):
            typer.echo("Files:")
            for f in infra["files"]:
                typer.echo(f"  • {f}")
        if infra.get("notes"):
            typer.echo("Notes:")
            for note in infra["notes"]:
                typer.echo(f"  • {note}")
        typer.echo()

    # Risks
    if "risks" in analysis:
        typer.echo("RISKS")
        typer.echo("-" * 70)
        for risk in analysis["risks"]:
            level = risk["level"].upper()
            category = risk["category"]
            desc = risk["description"]
            typer.echo(f"[{level}] {category}: {desc}")
        typer.echo()

    # Recommendations
    if "recommendations" in analysis:
        typer.echo("RECOMMENDATIONS")
        typer.echo("-" * 70)
        for i, rec in enumerate(analysis["recommendations"], 1):
            typer.echo(f"{i}. {rec}")
        typer.echo()

    # Checklist
    if "checklist" in analysis:
        typer.echo("DEPLOYMENT CHECKLIST")
        typer.echo("-" * 70)
        for item in analysis["checklist"]:
            required = "[REQUIRED]" if item["required"] else "[OPTIONAL]"
            typer.echo(f"  {required} {item['item']}")
        typer.echo()

    typer.echo(f"{'=' * 70}\n")


if __name__ == "__main__":
    app()
