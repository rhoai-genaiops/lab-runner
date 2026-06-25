"""Module 4: Ready to Scale 201 - Evaluation pipeline, MinIO, DSPA, prompt promotion."""

from lab_runner.config import Config
from lab_runner import defaults
from lab_runner.modules.base import Module
from lab_runner.steps.base import Step
from lab_runner.steps.helm_step import HelmInstallStep
from lab_runner.steps.kube_step import WaitForArgoCDAppsStep, WaitForReadyStep
from lab_runner.steps.git_step import CloneAndModifyStep, CloneInsideWorkbenchStep
from lab_runner.steps.mlflow_step import CreateMLflowWebhookStep
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

        evals_el_url = f"http://el-canopy-evals-event-listener.{toolings_ns}.svc.cluster.local:8080"
        evals_el_route = f"https://canopy-evals-event-listener-{config.username}-toolings.{config.cluster_domain}"
        promotion_el_route = f"https://prompt-promotion-event-listener-{config.username}-toolings.{config.cluster_domain}"

        steps: list[Step] = []

        # 1. Install MinIO
        steps.append(HelmInstallStep(
            release_name="minio",
            chart=defaults.CHART_MINIO,
            namespace=ns,
            values=defaults.MINIO_VALUES,
            description="Install MinIO",
        ))

        # 2. Wait for MinIO
        steps.append(WaitForReadyStep(
            label="app=minio",
            namespace=ns,
            description="Wait for MinIO ready",
        ))

        # 3. Install DSPA
        steps.append(HelmInstallStep(
            release_name="dspa",
            chart=defaults.CHART_DSPA,
            namespace=ns,
            values=defaults.DSPA_VALUES,
            description="Install DSPA",
        ))

        # 4. Wait for DSPA
        steps.append(WaitForReadyStep(
            label="dspa=dspa",
            namespace=ns,
            timeout=600,
            description="Wait for DSPA ready",
        ))

        # 5. Add DSPA tooling config to genaiops-gitops
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

        # 6. Wait for DSPA ArgoCD app
        steps.append(WaitForArgoCDAppsStep(
            app_names=["dspa"],
            namespace=toolings_ns,
            timeout=300,
            description="Wait for DSPA deployed via ArgoCD",
        ))

        # 7. Add evaluation-pipeline tooling config
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
            verify_content="llmEndpoint",
            description="Add evaluation pipeline config to toolings",
        ))

        # 8. Wait for evaluation-pipeline ArgoCD app
        steps.append(WaitForArgoCDAppsStep(
            app_names=["evaluation-pipeline"],
            namespace=toolings_ns,
            timeout=300,
            description="Wait for evaluation pipeline deployed",
        ))

        # 9. Create webhook: evals → Tekton event listener
        steps.append(CreateGiteaWebhookStep(
            repo_name="evals",
            target_url=evals_el_url,
            description="Create webhook: evals → Tekton event listener",
        ))

        # 10. Create webhook: backend → Tekton event listener
        steps.append(CreateGiteaWebhookStep(
            repo_name="backend",
            target_url=evals_el_url,
            description="Create webhook: backend → Tekton event listener",
        ))

        # 11. Create MLflow webhook: new prompt version → evals pipeline
        steps.append(CreateMLflowWebhookStep(
            webhook_name=f"{config.username}-canopy-evals",
            url=evals_el_route,
            events=["prompt.created", "prompt_version.created"],
            namespace=toolings_ns,
            webhook_description="Triggers evaluation pipeline when new prompt versions are created",
            description="Create MLflow webhook: prompt version → evals pipeline",
        ))

        # 12. Add prompt-promotion-pipeline tooling config
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "toolings/prompt-promotion-pipeline/config.yaml": defaults.prompt_promotion_pipeline_config_yaml(
                    config.username, config.cluster_domain
                ),
            },
            commit_message="Add prompt-promotion-pipeline tooling config",
            verify_repo="genaiops-gitops",
            verify_file="toolings/prompt-promotion-pipeline/config.yaml",
            description="Add prompt-promotion-pipeline config to toolings",
        ))

        # 13. Wait for prompt-promotion-pipeline ArgoCD app
        steps.append(WaitForArgoCDAppsStep(
            app_names=["prompt-promotion-pipeline"],
            namespace=toolings_ns,
            timeout=300,
            description="Wait for prompt-promotion-pipeline deployed",
        ))

        # 14. Create MLflow webhook: prod alias → prompt-promotion pipeline
        steps.append(CreateMLflowWebhookStep(
            webhook_name=f"{config.username}-canopy-prompt-promotion",
            url=promotion_el_route,
            events=["prompt_alias.created"],
            namespace=toolings_ns,
            webhook_description="Triggers prompt promotion pipeline when prod alias is set",
            description="Create MLflow webhook: prod alias → prompt-promotion pipeline",
        ))

        # 15. Clone evals repo inside workbench
        steps.append(CloneInsideWorkbenchStep(
            repos=[(config.evals_repo_url, "evals")],
            namespace=ns,
            description="Clone evals repo inside workbench",
        ))

        return steps
