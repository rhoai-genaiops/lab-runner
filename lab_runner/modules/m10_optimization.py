"""Module 10: Model Optimization - FP8 quantized model."""

from lab_runner.config import Config
from lab_runner import defaults
from lab_runner.modules.base import Module
from lab_runner.steps.base import Step
from lab_runner.steps.helm_step import HelmUpgradeStep
from lab_runner.steps.kube_step import WaitForArgoCDAppsStep
from lab_runner.steps.git_step import CloneAndModifyStep
from lab_runner.steps.verify_step import CheckRouteAccessibleStep


class OptimizationModule(Module):
    @property
    def id(self) -> int:
        return 10

    @property
    def name(self) -> str:
        return "Model Optimization"

    @property
    def dependencies(self) -> list[int]:
        return [8]

    def get_steps(self, config: Config) -> list[Step]:
        ns = config.namespace
        toolings_ns = config.toolings_namespace

        steps: list[Step] = []

        # 1. Upgrade llama-stack (add llama32-fp8 model)
        steps.append(HelmUpgradeStep(
            release_name="llama-stack-operator-instance",
            chart=defaults.CHART_LLAMA_STACK,
            namespace=ns,
            values=defaults.LLAMA_STACK_FP8_VALUES,
            description="Upgrade LlamaStack (add FP8 model)",
        ))

        # 2. Update test llama-stack config (add fp8 model)
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "canopy/test/llama-stack/config.yaml": defaults.gitops_test_llama_stack_fp8_config_yaml(),
            },
            commit_message="Add FP8 model to test llama-stack config",
            verify_repo="genaiops-gitops",
            verify_file="canopy/test/llama-stack/config.yaml",
            verify_content="llama32-fp8",
            description="Add FP8 model to test llama-stack config",
        ))

        # 3. Update backend values-test.yaml (switch to fp8 model)
        steps.append(CloneAndModifyStep(
            repo_url=config.backend_repo_url,
            modifications={
                "chart/values-test.yaml": defaults.backend_values_test_fp8_yaml(),
            },
            commit_message="Switch backend to FP8 model",
            verify_repo="backend",
            verify_file="chart/values-test.yaml",
            verify_content="llama32-fp8",
            description="Switch backend to FP8 model in test values",
        ))

        # 4. Wait for ArgoCD sync
        steps.append(WaitForArgoCDAppsStep(
            app_names=["llama-stack-test", "backend-test"],
            namespace=toolings_ns,
            timeout=300,
            description="Wait for ArgoCD sync after FP8 model update",
        ))

        # 5. Verify FP8 model responding
        steps.append(CheckRouteAccessibleStep(
            url=f"https://llama32-fp8-ai501.{config.cluster_domain}/v1/models",
            description="Verify FP8 model responding",
        ))

        return steps
