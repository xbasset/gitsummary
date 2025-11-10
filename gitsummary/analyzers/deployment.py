"""
Deployment facet analyzer.

Analyzes artifacts for deployment-related insights including logging,
configuration, infrastructure, and operational considerations.
"""

from typing import Any, Dict, List

from gitsummary.analyzers.base import Analyzer


class DeploymentAnalyzer(Analyzer):
    """
    Analyzer for deployment-related facets.

    Focuses on:
    - New logging patterns
    - Error handling changes
    - Configuration modifications
    - Infrastructure changes
    - Monitoring recommendations
    """

    @property
    def name(self) -> str:
        """Return the analyzer name."""
        return "deployment"

    @property
    def description(self) -> str:
        """Return analyzer description."""
        return "Analyzes deployment impact including logs, config, and infrastructure"

    def analyze(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the artifact for deployment insights.

        Args:
            artifact: Complete artifact dictionary.

        Returns:
            Deployment analysis results.
        """
        deployment = artifact.get("deployment", {})
        context = artifact.get("context", {})
        implementation = artifact.get("implementation", {})
        impact = artifact.get("impact", {})

        # Build comprehensive deployment analysis
        analysis = {
            "summary": self._build_summary(deployment, context),
            "logging": self._analyze_logging(deployment),
            "error_handling": self._analyze_error_handling(deployment),
            "configuration": self._analyze_configuration(deployment),
            "infrastructure": self._analyze_infrastructure(deployment),
            "risks": self._assess_deployment_risks(deployment, impact),
            "recommendations": self._generate_recommendations(
                deployment, implementation, impact
            ),
            "checklist": self._generate_checklist(deployment),
        }

        return analysis

    def _build_summary(
        self, deployment: Dict[str, Any], context: Dict[str, Any]
    ) -> str:
        """Generate a high-level deployment summary."""
        tag_range = context.get("commit_range", "unknown")
        file_count = context.get("file_count", 0)

        parts = [f"Deployment analysis for {tag_range}"]

        # Count significant changes
        log_count = deployment.get("new_logs_detected", {}).get("count", 0)
        error_count = deployment.get("error_handling_changes", {}).get("count", 0)
        config_count = len(deployment.get("configuration_changes", []))
        infra_count = len(deployment.get("infrastructure_changes", []))

        if log_count > 0:
            parts.append(f"{log_count} files with new logging")
        if error_count > 0:
            parts.append(f"{error_count} files with error handling changes")
        if config_count > 0:
            parts.append(f"{config_count} configuration files changed")
        if infra_count > 0:
            parts.append(f"{infra_count} infrastructure files changed")

        if len(parts) == 1:
            parts.append("no significant deployment changes detected")

        return ", ".join(parts) + "."

    def _analyze_logging(self, deployment: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze logging changes."""
        log_data = deployment.get("new_logs_detected", {})
        count = log_data.get("count", 0)
        files = log_data.get("files", [])

        return {
            "new_log_statements": count,
            "affected_files": files,
            "impact": self._assess_logging_impact(count),
            "notes": self._logging_notes(count),
        }

    def _assess_logging_impact(self, count: int) -> str:
        """Assess the impact of logging changes."""
        if count == 0:
            return "none"
        elif count < 5:
            return "low"
        elif count < 15:
            return "medium"
        else:
            return "high"

    def _logging_notes(self, count: int) -> List[str]:
        """Generate notes about logging changes."""
        if count == 0:
            return ["No new logging detected"]

        notes = [
            f"{count} file(s) with new logging statements",
            "Review log levels (debug/info/warn/error)",
            "Ensure sensitive data is not logged",
        ]

        if count > 10:
            notes.append("Consider log volume impact on storage and performance")

        return notes

    def _analyze_error_handling(self, deployment: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze error handling changes."""
        error_data = deployment.get("error_handling_changes", {})
        count = error_data.get("count", 0)
        files = error_data.get("files", [])

        return {
            "modified_files": count,
            "affected_files": files,
            "impact": "medium" if count > 0 else "none",
            "notes": self._error_handling_notes(count),
        }

    def _error_handling_notes(self, count: int) -> List[str]:
        """Generate notes about error handling changes."""
        if count == 0:
            return ["No error handling changes detected"]

        return [
            f"{count} file(s) with error handling modifications",
            "Verify error messages are user-friendly",
            "Ensure proper error propagation",
            "Review alerting rules for new error conditions",
        ]

    def _analyze_configuration(self, deployment: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze configuration changes."""
        config_files = deployment.get("configuration_changes", [])

        return {
            "files_changed": len(config_files),
            "files": config_files,
            "impact": "high" if config_files else "none",
            "notes": self._configuration_notes(config_files),
        }

    def _configuration_notes(self, files: List[str]) -> List[str]:
        """Generate notes about configuration changes."""
        if not files:
            return ["No configuration changes detected"]

        notes = [
            f"{len(files)} configuration file(s) modified",
            "Update deployment documentation",
            "Verify environment-specific settings",
        ]

        # Specific file type guidance
        if any("Dockerfile" in f for f in files):
            notes.append("Docker image rebuild required")
        if any(".env" in f for f in files):
            notes.append("Update environment variables in deployment targets")
        if any(".yaml" in f or ".yml" in f for f in files):
            notes.append("Review YAML syntax and apply to all environments")

        return notes

    def _analyze_infrastructure(self, deployment: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze infrastructure changes."""
        infra_files = deployment.get("infrastructure_changes", [])

        return {
            "files_changed": len(infra_files),
            "files": infra_files,
            "impact": "high" if infra_files else "none",
            "notes": self._infrastructure_notes(infra_files),
        }

    def _infrastructure_notes(self, files: List[str]) -> List[str]:
        """Generate notes about infrastructure changes."""
        if not files:
            return ["No infrastructure changes detected"]

        notes = [
            f"{len(files)} infrastructure file(s) modified",
            "Plan infrastructure changes during maintenance window",
            "Test in staging environment first",
        ]

        # Specific infrastructure type guidance
        if any("k8s" in f or "kubernetes" in f for f in files):
            notes.append("Kubernetes: Review resource limits and apply with kubectl")
        if any("helm" in f for f in files):
            notes.append("Helm: Update chart version and test upgrade path")
        if any("terraform" in f or ".tf" in f for f in files):
            notes.append("Terraform: Run plan before apply, review state changes")
        if any("github/workflows" in f or "gitlab-ci" in f for f in files):
            notes.append("CI/CD: Verify pipeline changes don't break builds")

        return notes

    def _assess_deployment_risks(
        self, deployment: Dict[str, Any], impact: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Assess deployment risks."""
        risks = []

        # Configuration risks
        config_files = deployment.get("configuration_changes", [])
        if config_files:
            risks.append(
                {
                    "level": "high",
                    "category": "configuration",
                    "description": "Configuration changes may cause runtime failures if not properly updated across environments",
                }
            )

        # Infrastructure risks
        infra_files = deployment.get("infrastructure_changes", [])
        if infra_files:
            risks.append(
                {
                    "level": "high",
                    "category": "infrastructure",
                    "description": "Infrastructure changes require careful coordination and may cause downtime",
                }
            )

        # Compatibility risks from impact section
        compat_risks = impact.get("compatibility_risks", [])
        if compat_risks:
            risks.append(
                {
                    "level": "medium",
                    "category": "compatibility",
                    "description": "; ".join(compat_risks),
                }
            )

        # Error handling risks
        error_count = deployment.get("error_handling_changes", {}).get("count", 0)
        if error_count > 5:
            risks.append(
                {
                    "level": "medium",
                    "category": "stability",
                    "description": f"{error_count} files with error handling changes may affect application stability",
                }
            )

        if not risks:
            risks.append(
                {
                    "level": "low",
                    "category": "general",
                    "description": "No significant deployment risks detected",
                }
            )

        return risks

    def _generate_recommendations(
        self,
        deployment: Dict[str, Any],
        implementation: Dict[str, Any],
        impact: Dict[str, Any],
    ) -> List[str]:
        """Generate deployment recommendations."""
        recommendations = []

        # Monitoring recommendations from deployment section
        monitoring_notes = deployment.get("monitoring_notes", [])
        recommendations.extend(monitoring_notes)

        # Dependency recommendations
        dep_changes = implementation.get("dependency_changes", [])
        if dep_changes:
            recommendations.append(
                f"Update dependencies: {', '.join(dep_changes)} - verify compatibility"
            )

        # Testing recommendations
        if impact.get("breaking_changes_detected"):
            recommendations.append(
                "Breaking changes detected - run full regression test suite"
            )

        # Complexity recommendations
        complexity = implementation.get("complexity_delta", "low")
        if complexity == "high":
            recommendations.append(
                "High complexity change - consider staged rollout or feature flags"
            )

        # Logging volume recommendation
        log_count = deployment.get("new_logs_detected", {}).get("count", 0)
        if log_count > 10:
            recommendations.append("Review log retention policies due to increased logging")

        if not recommendations:
            recommendations.append("Standard deployment process recommended")

        return recommendations

    def _generate_checklist(self, deployment: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate a deployment checklist."""
        checklist = [
            {"item": "Review all code changes", "required": True},
            {"item": "Run automated test suite", "required": True},
            {"item": "Update CHANGELOG", "required": True},
        ]

        # Add conditional items based on deployment content
        config_files = deployment.get("configuration_changes", [])
        if config_files:
            checklist.append(
                {
                    "item": f"Update configuration in all environments: {', '.join(config_files)}",
                    "required": True,
                }
            )

        infra_files = deployment.get("infrastructure_changes", [])
        if infra_files:
            checklist.append(
                {"item": "Test infrastructure changes in staging", "required": True}
            )
            checklist.append(
                {"item": "Schedule maintenance window if needed", "required": False}
            )

        log_count = deployment.get("new_logs_detected", {}).get("count", 0)
        if log_count > 0:
            checklist.append(
                {"item": "Verify log aggregation is capturing new logs", "required": False}
            )

        error_count = deployment.get("error_handling_changes", {}).get("count", 0)
        if error_count > 0:
            checklist.append(
                {"item": "Review and update alerting rules", "required": False}
            )

        checklist.extend(
            [
                {"item": "Deploy to staging environment", "required": True},
                {"item": "Monitor staging for issues", "required": True},
                {"item": "Create deployment backup/rollback plan", "required": True},
                {"item": "Deploy to production", "required": True},
                {"item": "Monitor production metrics", "required": True},
            ]
        )

        return checklist
