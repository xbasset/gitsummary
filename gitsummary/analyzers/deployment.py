"""Deployment analyzer for artifacts."""

import json
from typing import Any, Dict

from gitsummary.analyzers.base import Analyzer


class DeploymentAnalyzer(Analyzer):
    """Analyzer for deployment-related facets."""

    def analyze(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze deployment facet of an artifact.

        Args:
            artifact: The artifact dictionary

        Returns:
            Deployment analysis results
        """
        deployment = artifact.get("deployment", {})
        implementation = artifact.get("implementation", {})
        context = artifact.get("context", {})

        # Build comprehensive deployment analysis
        analysis = {
            "summary": self._generate_summary(deployment, implementation, context),
            "logging_changes": {
                "new_logs": deployment.get("new_logs", []),
                "impact": "Review new logging statements for production readiness",
            },
            "error_handling": {
                "changes": deployment.get("error_handling_changes", []),
                "impact": "Error handling modifications may affect error reporting and monitoring",
            },
            "configuration": {
                "files": deployment.get("configuration_changes", []),
                "impact": "Configuration changes may require environment updates",
                "recommendations": [
                    "Verify all configuration changes are documented",
                    "Check for environment variable changes",
                    "Review configuration defaults",
                ],
            },
            "infrastructure": {
                "files": deployment.get("infrastructure_changes", []),
                "impact": "Infrastructure changes detected - review deployment procedures",
                "recommendations": [
                    "Review Dockerfile changes for base image updates",
                    "Check Kubernetes manifests for resource changes",
                    "Verify CI/CD pipeline changes",
                    "Test infrastructure changes in staging",
                ],
            },
            "monitoring": {
                "notes": deployment.get("monitoring_notes", ""),
                "recommendations": [
                    "Integrate new logging with monitoring systems",
                    "Set up alerts for new error handling paths",
                    "Review metrics collection for new features",
                ],
            },
            "deployment_readiness": self._assess_readiness(deployment, implementation),
        }

        return analysis

    def _generate_summary(self, deployment: Dict, implementation: Dict, context: Dict) -> str:
        """Generate a summary of deployment changes.

        Args:
            deployment: Deployment section of artifact
            implementation: Implementation section of artifact
            context: Context section of artifact

        Returns:
            Summary string
        """
        infra_count = len(deployment.get("infrastructure_changes", []))
        config_count = len(deployment.get("configuration_changes", []))
        log_count = len(deployment.get("new_logs", []))
        error_count = len(deployment.get("error_handling_changes", []))

        parts = []
        if infra_count > 0:
            parts.append(f"{infra_count} infrastructure change(s)")
        if config_count > 0:
            parts.append(f"{config_count} configuration change(s)")
        if log_count > 0:
            parts.append(f"{log_count} new logging statement(s)")
        if error_count > 0:
            parts.append(f"{error_count} error handling change(s)")

        if parts:
            summary = f"Deployment analysis for {context.get('commit_range', 'unknown range')}: "
            summary += ", ".join(parts) + "."
        else:
            summary = f"No significant deployment changes detected for {context.get('commit_range', 'unknown range')}."

        return summary

    def _assess_readiness(self, deployment: Dict, implementation: Dict) -> Dict[str, Any]:
        """Assess deployment readiness.

        Args:
            deployment: Deployment section of artifact
            implementation: Implementation section of artifact

        Returns:
            Readiness assessment dictionary
        """
        readiness_score = 1.0
        concerns = []

        # Check for infrastructure changes without tests
        infra_changes = deployment.get("infrastructure_changes", [])
        test_files = implementation.get("test_files_changed", 0)
        if infra_changes and test_files == 0:
            concerns.append("Infrastructure changes detected without corresponding test changes")
            readiness_score -= 0.2

        # Check for configuration changes
        config_changes = deployment.get("configuration_changes", [])
        if config_changes:
            concerns.append("Configuration changes require manual review")
            readiness_score -= 0.1

        # Check for error handling changes
        error_changes = deployment.get("error_handling_changes", [])
        if error_changes:
            concerns.append("Error handling changes should be tested thoroughly")

        readiness_score = max(0.0, readiness_score)

        return {
            "score": readiness_score,
            "level": self._score_to_level(readiness_score),
            "concerns": concerns,
            "recommendations": [
                "Run full test suite before deployment",
                "Review all configuration changes",
                "Verify infrastructure changes in staging environment",
            ],
        }

    def _score_to_level(self, score: float) -> str:
        """Convert readiness score to level.

        Args:
            score: Readiness score (0.0 to 1.0)

        Returns:
            Level string
        """
        if score >= 0.9:
            return "high"
        elif score >= 0.7:
            return "medium"
        elif score >= 0.5:
            return "low"
        else:
            return "critical_review_needed"

    def format_output(self, analysis: Dict[str, Any], format_type: str = "json") -> str:
        """Format analysis results for output.

        Args:
            analysis: Analysis results dictionary
            format_type: Output format ('json' or 'markdown')

        Returns:
            Formatted string
        """
        if format_type == "json":
            return json.dumps(analysis, indent=2, default=str)
        elif format_type == "markdown":
            return self._format_markdown(analysis)
        else:
            raise ValueError(f"Unknown format type: {format_type}")

    def _format_markdown(self, analysis: Dict[str, Any]) -> str:
        """Format analysis as Markdown.

        Args:
            analysis: Analysis results dictionary

        Returns:
            Markdown formatted string
        """
        lines = ["# Deployment Analysis\n", f"{analysis['summary']}\n"]

        # Logging changes
        if analysis["logging_changes"]["new_logs"]:
            lines.append("## Logging Changes\n")
            for log in analysis["logging_changes"]["new_logs"]:
                lines.append(f"- **{log['file']}**: {log['pattern']}\n")
            lines.append(f"\n{analysis['logging_changes']['impact']}\n")

        # Error handling
        if analysis["error_handling"]["changes"]:
            lines.append("## Error Handling Changes\n")
            for file in analysis["error_handling"]["changes"]:
                lines.append(f"- {file}\n")
            lines.append(f"\n{analysis['error_handling']['impact']}\n")

        # Configuration
        if analysis["configuration"]["files"]:
            lines.append("## Configuration Changes\n")
            for file in analysis["configuration"]["files"]:
                lines.append(f"- {file}\n")
            lines.append("\n### Recommendations\n")
            for rec in analysis["configuration"]["recommendations"]:
                lines.append(f"- {rec}\n")

        # Infrastructure
        if analysis["infrastructure"]["files"]:
            lines.append("## Infrastructure Changes\n")
            for file in analysis["infrastructure"]["files"]:
                lines.append(f"- {file}\n")
            lines.append(f"\n{analysis['infrastructure']['impact']}\n")
            lines.append("\n### Recommendations\n")
            for rec in analysis["infrastructure"]["recommendations"]:
                lines.append(f"- {rec}\n")

        # Monitoring
        lines.append("## Monitoring\n")
        lines.append(f"{analysis['monitoring']['notes']}\n")
        lines.append("\n### Recommendations\n")
        for rec in analysis["monitoring"]["recommendations"]:
            lines.append(f"- {rec}\n")

        # Deployment readiness
        readiness = analysis["deployment_readiness"]
        lines.append("## Deployment Readiness\n")
        lines.append(f"**Score**: {readiness['score']:.2f} ({readiness['level']})\n")
        if readiness["concerns"]:
            lines.append("\n### Concerns\n")
            for concern in readiness["concerns"]:
                lines.append(f"- ⚠️ {concern}\n")
        lines.append("\n### Recommendations\n")
        for rec in readiness["recommendations"]:
            lines.append(f"- {rec}\n")

        return "".join(lines)

