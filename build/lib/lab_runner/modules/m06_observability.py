"""Module 6: Observability - Grafana, feedback collection."""

from lab_runner.config import Config
from lab_runner import defaults
from lab_runner.modules.base import Module
from lab_runner.steps.base import Step
from lab_runner.steps.kube_step import WaitForArgoCDAppsStep
from lab_runner.steps.git_step import CloneAndModifyStep
from lab_runner.steps.verify_step import CheckRouteAccessibleStep


class ObservabilityModule(Module):
    @property
    def id(self) -> int:
        return 6

    @property
    def name(self) -> str:
        return "Observability"

    @property
    def dependencies(self) -> list[int]:
        return [5]

    def get_steps(self, config: Config) -> list[Step]:
        toolings_ns = config.toolings_namespace

        steps: list[Step] = []

        # 1. Add Grafana config to toolings
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "toolings/grafana/config.yaml": defaults.grafana_config_yaml(),
            },
            commit_message="Grafana added",
            verify_repo="genaiops-gitops",
            verify_file="toolings/grafana/config.yaml",
            description="Add Grafana config to toolings",
        ))

        # 2. Wait for Grafana deployed via ArgoCD
        steps.append(WaitForArgoCDAppsStep(
            app_names=["grafana"],
            namespace=toolings_ns,
            timeout=300,
            description="Wait for Grafana deployed via ArgoCD",
        ))

        # 3. Verify Grafana route accessible (returns 403 when auth required)
        steps.append(CheckRouteAccessibleStep(
            url=config.route_url("canopy-grafana-route", toolings_ns),
            expected_status=403,
            description="Verify Grafana route accessible",
        ))

        # 4. Enable feedback collection in test backend config
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "canopy/test/backend/config.yaml": defaults.gitops_test_backend_feedback_config_yaml(
                    config.username, config.cluster_domain
                ),
            },
            commit_message="Enable feedback collection",
            verify_repo="genaiops-gitops",
            verify_file="canopy/test/backend/config.yaml",
            verify_content="feedback",
            description="Enable feedback collection in test backend config",
        ))

        return steps
