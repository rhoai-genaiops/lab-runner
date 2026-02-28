"""Module 7: Guardrails (Honor Code) - Safety filters and detectors."""

from lab_runner.config import Config
from lab_runner import defaults
from lab_runner.modules.base import Module
from lab_runner.steps.base import Step
from lab_runner.steps.helm_step import HelmInstallStep, HelmUpgradeStep
from lab_runner.steps.kube_step import WaitForReadyStep
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
        return [3]

    def get_steps(self, config: Config) -> list[Step]:
        ns = config.namespace

        steps: list[Step] = []

        # 1. Install guardrails-orchestrator
        steps.append(HelmInstallStep(
            release_name="guardrails-orchestrator",
            chart=defaults.CHART_GUARDRAILS,
            namespace=ns,
            values=defaults.GUARDRAILS_VALUES,
            description="Install Guardrails Orchestrator",
        ))

        # 2. Upgrade llama-stack (enable guardrails + detectors)
        steps.append(HelmUpgradeStep(
            release_name="llama-stack-operator-instance",
            chart=defaults.CHART_LLAMA_STACK,
            namespace=ns,
            values=defaults.LLAMA_STACK_GUARDRAILS_VALUES,
            verify_key="guardrails.enabled",
            verify_value=True,
            description="Upgrade LlamaStack (enable guardrails)",
        ))

        # 3. Wait for guardrails pods
        steps.append(WaitForReadyStep(
            label="app.kubernetes.io/name=guardrails-orchestrator",
            namespace=ns,
            timeout=600,
            description="Wait for Guardrails Orchestrator ready",
        ))

        # 4. Add guardrails config for test/prod
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "canopy/test/guardrails-orchestrator/config.yaml": defaults.guardrails_config_yaml(),
                "canopy/prod/guardrails-orchestrator/config.yaml": defaults.guardrails_config_yaml(),
            },
            commit_message="Add guardrails orchestrator configs for test/prod",
            verify_repo="genaiops-gitops",
            verify_file="canopy/test/guardrails-orchestrator/config.yaml",
            description="Add guardrails configs for test and prod",
        ))

        # 5. Update test/prod llama-stack configs (enable guardrails)
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "canopy/test/llama-stack/config.yaml": defaults.gitops_llama_stack_guardrails_config_yaml("test"),
                "canopy/prod/llama-stack/config.yaml": defaults.gitops_llama_stack_guardrails_config_yaml("prod"),
            },
            commit_message="Enable guardrails in test/prod llama-stack configs",
            verify_repo="genaiops-gitops",
            verify_file="canopy/test/llama-stack/config.yaml",
            verify_content="guardrails",
            description="Enable guardrails in test/prod llama-stack configs",
        ))

        # 6. Enable shields in backend
        steps.append(CloneAndModifyStep(
            repo_url=config.backend_repo_url,
            modifications={
                "chart/values-test.yaml": defaults.backend_values_test_shields_yaml(),
            },
            commit_message="Enable shields in backend test values",
            verify_repo="backend",
            verify_file="chart/values-test.yaml",
            verify_content="shields",
            description="Enable shields in backend test values",
        ))

        # 7. Verify guardrails running
        steps.append(CheckPodRunningStep(
            label="app.kubernetes.io/name=guardrails-orchestrator",
            namespace=ns,
            description="Verify Guardrails Orchestrator running",
        ))

        return steps
