"""CLI entry point for gitsummary."""

from pathlib import Path
from typing import Optional

import typer
from git.exc import InvalidGitRepositoryError

from gitsummary import __version__
from gitsummary.analyzers import DeploymentAnalyzer
from gitsummary.collector import ArtifactCollector
from gitsummary.storage import Storage

app = typer.Typer(
    name="gitsummary",
    help="A Python CLI tool for collecting and analyzing Git change sets",
    add_completion=False,
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"gitsummary version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", callback=version_callback, help="Show version and exit"
    ),
) -> None:
    """gitsummary - Collect and analyze Git change sets."""
    pass


@app.command()
def collect(
    tag_a: str = typer.Argument(..., help="Starting tag (exclusive)"),
    tag_b: str = typer.Argument(..., help="Ending tag (inclusive)"),
    tag: bool = typer.Option(True, "--tag/--no-tag", help="Treat arguments as tags (POC: always tags)"),
    repo_path: str = typer.Option(".", "--repo", "-r", help="Path to Git repository root"),
) -> None:
    """Collect Git data between two tags and generate an artifact.

    Examples:
        gitsummary collect --tag v0.1.0 v0.2.0
        gitsummary collect --tag 0.1 0.2 --repo /path/to/repo
    """
    try:
        # Initialize collector
        collector = ArtifactCollector(repo_path)

        # Collect artifact
        typer.echo(f"Collecting data between tags {tag_a} and {tag_b}...", err=True)
        artifact = collector.collect(tag_a, tag_b)

        # Save artifact
        storage = Storage(collector.repo_root)
        artifact_id = storage.save_artifact(artifact, tag_a, tag_b)

        typer.echo(f"Artifact created: {artifact_id}")
    except InvalidGitRepositoryError:
        typer.echo(f"Error: '{repo_path}' is not a valid Git repository", err=True)
        raise typer.Exit(1)
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Unexpected error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def analyze(
    artifact_id: str = typer.Argument(..., help="Artifact ID (full or prefix)"),
    target: str = typer.Option(..., "--target", "-t", help="Facet to analyze (e.g., 'deployment')"),
    format_type: str = typer.Option("json", "--format", "-f", help="Output format: 'json' or 'markdown'"),
    repo_path: str = typer.Option(".", "--repo", "-r", help="Path to Git repository root"),
) -> None:
    """Analyze an artifact for a specific facet.

    Examples:
        gitsummary analyze 3fa4c021 --target deployment
        gitsummary analyze 3fa4c021bc7e9f1f6c3d92da0d98cefd88b3fcd9 --target deployment --format markdown
    """
    try:
        repo_root = Path(repo_path).resolve()
        if not repo_root.exists():
            typer.echo(f"Error: Repository path '{repo_path}' does not exist", err=True)
            raise typer.Exit(1)

        # Load artifact
        storage = Storage(repo_root)
        artifact = storage.load_artifact(artifact_id)

        if artifact is None:
            typer.echo(f"Error: Artifact '{artifact_id}' not found", err=True)
            raise typer.Exit(1)

        # Select analyzer
        analyzer = None
        if target == "deployment":
            analyzer = DeploymentAnalyzer()
        else:
            typer.echo(f"Error: Unknown analyzer target '{target}'", err=True)
            typer.echo("Available targets: deployment", err=True)
            raise typer.Exit(1)

        # Run analysis
        analysis = analyzer.analyze(artifact)
        output = analyzer.format_output(analysis, format_type)

        # Print to stdout
        typer.echo(output)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

