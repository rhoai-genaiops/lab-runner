"""Module 4: Ready to Scale 201 - Evaluation pipeline, MinIO, DSPA."""

from lab_runner.config import Config
from lab_runner import defaults
from lab_runner.modules.base import Module
from lab_runner.steps.base import Step
from lab_runner.steps.helm_step import HelmInstallStep, HelmUpgradeStep
from lab_runner.steps.kube_step import WaitForArgoCDAppsStep, WaitForReadyStep
from lab_runner.steps.git_step import CloneAndModifyStep, CloneInsideWorkbenchStep
from lab_runner.steps.webhook_step import CreateGiteaWebhookStep


class Scale201Module(Module):
    @property
    def id(self) -> int:
        return 4

    @property
    def name(self) -> str:
        return "Ready to Scale 201"

    @property
    def dependencies(self) -> list[int]:
        return [3]

    def get_steps(self, config: Config) -> list[Step]:
        ns = config.namespace
        toolings_ns = config.toolings_namespace
        tekton_el_url = f"http://el-canopy-evals-event-listener.{toolings_ns}.svc.cluster.local:8080"

        steps: list[Step] = []

        # 1. Upgrade llama-stack (enable evals)
        steps.append(HelmUpgradeStep(
            release_name="llama-stack-operator-instance",
            chart=defaults.CHART_LLAMA_STACK,
            namespace=ns,
            values=defaults.LLAMA_STACK_EVAL_VALUES,
            verify_key="eval.enabled",
            verify_value=True,
            description="Upgrade LlamaStack (enable evals)",
        ))

        # 2. Install MinIO
        steps.append(HelmInstallStep(
            release_name="minio",
            chart=defaults.CHART_MINIO,
            namespace=ns,
            values=defaults.MINIO_VALUES,
            description="Install MinIO",
        ))

        # 3. Wait for MinIO
        steps.append(WaitForReadyStep(
            label="app=minio",
            namespace=ns,
            description="Wait for MinIO ready",
        ))

        # 4. Install DSPA
        steps.append(HelmInstallStep(
            release_name="dspa",
            chart=defaults.CHART_DSPA,
            namespace=ns,
            values=defaults.DSPA_VALUES,
            description="Install DSPA",
        ))

        # 5. Wait for DSPA
        steps.append(WaitForReadyStep(
            label="dspa=dspa",
            namespace=ns,
            timeout=600,
            description="Wait for DSPA ready",
        ))

        # 6. Clone evals repo locally (handled inside git steps)
        # 7. Add toolings/dspa/config.yaml
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "toolings/dspa/config.yaml": defaults.dspa_toolings_config_yaml(),
            },
            commit_message="Add DSPA tooling config",
            verify_repo="genaiops-gitops",
            verify_file="toolings/dspa/config.yaml",
            description="Add DSPA config to genaiops-gitops toolings",
        ))

        # 8. Wait for DSPA in toolings via ArgoCD
        steps.append(WaitForArgoCDAppsStep(
            app_names=["dspa"],
            namespace=toolings_ns,
            timeout=300,
            description="Wait for DSPA deployed via ArgoCD",
        ))

        # 9. Update test llama-stack config (enable eval)
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "canopy/test/llama-stack/config.yaml": defaults.gitops_test_llama_stack_eval_config_yaml(),
            },
            commit_message="Enable eval in test llama-stack config",
            verify_repo="genaiops-gitops",
            verify_file="canopy/test/llama-stack/config.yaml",
            verify_content="eval",
            description="Enable eval in test llama-stack config",
        ))

        # 10. Add evaluation-pipeline tooling config
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "toolings/evaluation-pipeline/config.yaml": defaults.evals_pipeline_config_yaml(
                    config.username, config.cluster_domain
                ),
            },
            commit_message="Add evaluation pipeline tooling config",
            verify_repo="genaiops-gitops",
            verify_file="toolings/evaluation-pipeline/config.yaml",
            description="Add evaluation pipeline config to toolings",
        ))

        # 11. Wait for Tekton pipeline deployed
        steps.append(WaitForArgoCDAppsStep(
            app_names=["evaluation-pipeline"],
            namespace=toolings_ns,
            timeout=300,
            description="Wait for evaluation pipeline deployed",
        ))

        # 12. Create webhook: evals → Tekton event listener
        steps.append(CreateGiteaWebhookStep(
            repo_name="evals",
            target_url=tekton_el_url,
            description="Create webhook: evals → Tekton event listener",
        ))

        # 13. Create webhook: backend → Tekton event listener
        steps.append(CreateGiteaWebhookStep(
            repo_name="backend",
            target_url=tekton_el_url,
            description="Create webhook: backend → Tekton event listener",
        ))

        # 14. Clone evals repo inside workbench
        steps.append(CloneInsideWorkbenchStep(
            repos=[(config.evals_repo_url, "evals")],
            namespace=ns,
            description="Clone evals repo inside workbench",
        ))

        return steps
