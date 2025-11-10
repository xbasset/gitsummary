"""
Base analyzer interface.

Defines the protocol for all analyzer implementations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class Analyzer(ABC):
    """
    Abstract base class for artifact analyzers.

    Each analyzer processes a stored artifact and produces
    facet-specific insights.
    """

    @abstractmethod
    def analyze(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze an artifact and return facet-specific insights.

        Args:
            artifact: The complete artifact dictionary.

        Returns:
            Analysis results as a dictionary.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this analyzer/facet."""
        pass

    @property
    def description(self) -> str:
        """Return a human-readable description of this analyzer."""
        return f"{self.name} analyzer"
