"""Built-in analyzers for gitsummary facets."""

from __future__ import annotations

import json
from typing import Callable, Dict, Mapping

Analyzer = Callable[[Mapping[str, object]], str]


def _format_json(data: object) -> str:
    return json.dumps(data, indent=2, sort_keys=True)


def _context_analyzer(artifact: Mapping[str, object]) -> str:
    return _format_json(artifact.get("context", {}))


def _intention_analyzer(artifact: Mapping[str, object]) -> str:
    return _format_json(artifact.get("intention", {}))


def _implementation_analyzer(artifact: Mapping[str, object]) -> str:
    return _format_json(artifact.get("implementation", {}))


def _impact_analyzer(artifact: Mapping[str, object]) -> str:
    return _format_json(artifact.get("impact", {}))


def _maintainability_analyzer(artifact: Mapping[str, object]) -> str:
    return _format_json(artifact.get("maintainability", {}))


def _deployment_analyzer(artifact: Mapping[str, object]) -> str:
    return _format_json(artifact.get("deployment", {}))


def _release_notes_analyzer(artifact: Mapping[str, object]) -> str:
    """Composite analyzer that extracts release-relevant sections."""
    report = {
        "context": artifact.get("context", {}),
        "intention": artifact.get("intention", {}),
        "impact": artifact.get("impact", {}),
    }
    return _format_json(report)


_ANALYZERS: Dict[str, Analyzer] = {
    "context": _context_analyzer,
    "intention": _intention_analyzer,
    "implementation": _implementation_analyzer,
    "impact": _impact_analyzer,
    "maintainability": _maintainability_analyzer,
    "deployment": _deployment_analyzer,
    "release-notes": _release_notes_analyzer,
}


def available_targets() -> Dict[str, Analyzer]:
    """Return the registered analyzers."""

    return dict(_ANALYZERS)


def run(target: str, artifact: Mapping[str, object]) -> str:
    """Execute the analyzer for ``target`` and return a string payload."""

    analyzers = available_targets()
    try:
        analyzer = analyzers[target]
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise KeyError(f"Unknown analyzer target '{target}'.") from exc
    return analyzer(artifact)
