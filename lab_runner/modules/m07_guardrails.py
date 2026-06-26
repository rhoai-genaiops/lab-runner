"""Module 7: Guardrails (Honor Code) - NeMo guardrails via GitOps."""

from lab_runner.config import Config
from lab_runner import defaults
from lab_runner.modules.base import Module
from lab_runner.steps.base import Step
from lab_runner.steps.kube_step import WaitForArgoCDAppsStep
from lab_runner.steps.git_step import CloneAndModifyStep
from lab_runner.steps.verify_step import CheckPodRunningStep


class GuardrailsModule(Module):
    @property
    def id(self) -> int:
        return 7

    @property
    def name(self) -> str:
        return "Guardrails"

    @property
    def dependencies(self) -> list[int]:
        return [6]

    def get_steps(self, config: Config) -> list[Step]:
        toolings_ns = config.toolings_namespace
        test_ns = config.test_namespace

        steps: list[Step] = []

        # 1. Add NeMo Guardrails orchestrator configs for test and prod
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "canopy/test/nemo-guardrails-orchestrator/config.yaml": defaults.nemo_guardrails_config_yaml(),
                "canopy/prod/nemo-guardrails-orchestrator/config.yaml": defaults.nemo_guardrails_config_yaml(),
                "canopy/test/ogx/config.yaml": defaults.gitops_ogx_guardrails_config_yaml("test", config.username),
                "canopy/prod/ogx/config.yaml": defaults.gitops_ogx_guardrails_config_yaml("prod", config.username),
                "canopy/test/backend/config.yaml": defaults.gitops_test_backend_guardrails_config_yaml(
                    config.username, config.cluster_domain
                ),
            },
            commit_message="NeMo Guardrails added",
            verify_repo="genaiops-gitops",
            verify_file="canopy/test/nemo-guardrails-orchestrator/config.yaml",
            description="Add NeMo guardrails and enable shields in test/prod",
        ))

        # 2. Wait for NeMo guardrails ArgoCD apps
        steps.append(WaitForArgoCDAppsStep(
            app_names=["nemo-guardrails-orchestrator-test", "nemo-guardrails-orchestrator-prod"],
            namespace=toolings_ns,
            timeout=600,
            description="Wait for NeMo Guardrails deployed in test and prod",
        ))

        # 3. Verify guardrails running in test
        steps.append(CheckPodRunningStep(
            label="app=canopy-guardrails",
            namespace=test_ns,
            description="Verify NeMo Guardrails Orchestrator running in test",
        ))

        return steps
