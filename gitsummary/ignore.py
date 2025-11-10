"""
Ignore rules handling.

Manages filtering of files based on .gitignore and .gitsummaryignore patterns.
"""

from pathlib import Path
from typing import List, Set

import pathspec


# Default patterns to ignore (built-in noise filters)
DEFAULT_IGNORE_PATTERNS = [
    # Lockfiles
    "*.lock",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "composer.lock",
    "Gemfile.lock",
    "Cargo.lock",
    # Build outputs
    "dist/",
    "build/",
    "target/",
    "out/",
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    ".cache/",
    # Vendored/bundled
    "vendor/",
    "node_modules/",
    "third_party/",
    # Minified/bundles
    "*.min.js",
    "*.min.css",
    "bundle.js",
    "bundle.css",
    # Binary blobs
    "*.zip",
    "*.bin",
    "*.tar",
    "*.tar.gz",
    "*.7z",
    "*.exe",
    "*.dll",
    "*.so",
    "*.dylib",
]


class IgnoreFilter:
    """
    Filter for determining which files to include in analysis.

    Respects .gitignore and .gitsummaryignore patterns, with sensible
    defaults for common noise files.
    """

    def __init__(self, repo_root: Path) -> None:
        """
        Initialize the ignore filter.

        Args:
            repo_root: Root directory of the Git repository.
        """
        self.repo_root = repo_root
        self._patterns: List[str] = []
        self._spec: pathspec.PathSpec = pathspec.PathSpec.from_lines("gitwildmatch", [])

        self._load_patterns()

    def _load_patterns(self) -> None:
        """Load ignore patterns from files and defaults."""
        patterns: List[str] = []

        # Start with default patterns
        patterns.extend(DEFAULT_IGNORE_PATTERNS)

        # Load .gitsummaryignore if it exists
        gitsummary_ignore = self.repo_root / ".gitsummaryignore"
        if gitsummary_ignore.exists():
            patterns.extend(self._read_ignore_file(gitsummary_ignore))

        # Note: .gitignore is respected by Git itself, so we don't need to
        # parse it here - Git operations already filter those files out

        self._patterns = patterns
        self._spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)

    def _read_ignore_file(self, file_path: Path) -> List[str]:
        """
        Read patterns from an ignore file.

        Args:
            file_path: Path to the ignore file.

        Returns:
            List of pattern strings.
        """
        patterns: List[str] = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith("#"):
                        patterns.append(line)
        except (OSError, UnicodeDecodeError):
            pass  # Silently skip files that can't be read

        return patterns

    def should_include(self, file_path: str) -> bool:
        """
        Check if a file should be included in analysis.

        Args:
            file_path: Relative path to the file from repo root.

        Returns:
            True if the file should be included, False otherwise.
        """
        # Check against patterns
        return not self._spec.match_file(file_path)

    def filter_files(self, file_paths: List[str]) -> List[str]:
        """
        Filter a list of file paths.

        Args:
            file_paths: List of file paths relative to repo root.

        Returns:
            Filtered list of file paths.
        """
        return [path for path in file_paths if self.should_include(path)]

    @property
    def patterns(self) -> List[str]:
        """Get the current list of ignore patterns."""
        return self._patterns.copy()
