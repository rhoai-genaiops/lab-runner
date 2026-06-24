"""Module 10: Model Optimization - Switch to FP8 quantized model via GitOps."""

from lab_runner.config import Config
from lab_runner import defaults
from lab_runner.modules.base import Module
from lab_runner.steps.base import Step
from lab_runner.steps.kube_step import WaitForArgoCDAppsStep
from lab_runner.steps.git_step import CloneAndModifyStep


class ModelOptimizationModule(Module):
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
        toolings_ns = config.toolings_namespace

        steps: list[Step] = []

        # 1. Add llama32-fp8 to OGX config and switch backend to fp8
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "canopy/test/ogx/config.yaml": defaults.gitops_ogx_fp8_config_yaml(),
                "canopy/test/backend/config.yaml": defaults.gitops_test_backend_fp8_config_yaml(
                    config.username, config.cluster_domain
                ),
            },
            commit_message="Switch to FP8",
            verify_repo="genaiops-gitops",
            verify_file="canopy/test/ogx/config.yaml",
            verify_content="llama32-fp8",
            description="Add llama32-fp8 to OGX and switch backend to fp8",
        ))

        # 2. Wait for backend to redeploy with fp8 model
        steps.append(WaitForArgoCDAppsStep(
            app_names=["backend-test"],
            namespace=toolings_ns,
            timeout=300,
            description="Wait for backend-test redeployed with fp8 model",
        ))

        return steps
