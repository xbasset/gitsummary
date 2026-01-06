"""Minimal setup.py for development installation."""

from setuptools import setup, find_packages

# Read version from __init__.py
with open("gitsummary/__init__.py") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split("=")[1].strip().strip('"').strip("'")
            break

setup(
    name="gitsummary",
    version=version,
    description="Summarise git changes into durable artifacts",
    packages=find_packages(),
    python_requires=">=3.10",
    package_data={
        "gitsummary": ["llm/prompt_assets/commit_artifact_v2/*.md"],
    },
    include_package_data=True,
    install_requires=[
        "typer>=0.9",
        "PyYAML>=6.0",
        "pydantic>=2.0",
        "psycopg[binary]>=3.1",
        "openai>=1.0.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "gitsummary=gitsummary.cli:app",
        ],
    },
)
