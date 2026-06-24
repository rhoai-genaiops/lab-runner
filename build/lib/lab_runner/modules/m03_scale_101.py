"""Module 3: Ready to Scale 101 - LlamaStack, workbench, GitOps pipeline."""

from lab_runner.config import Config
from lab_runner import defaults
from lab_runner.modules.base import Module
from lab_runner.steps.base import Step
from lab_runner.steps.helm_step import HelmInstallStep, HelmUpgradeStep
from lab_runner.steps.kube_step import (
    ApplyManifestStep,
    CreateNotebookCRStep,
    WaitForArgoCDAppsStep,
    WaitForReadyStep,
)
from lab_runner.steps.git_step import (
    CloneAndModifyStep,
    CloneInsideWorkbenchStep,
    SetGitConfigInWorkbenchStep,
)
from lab_runner.steps.mlflow_step import CreateMLflowPromptStep
from lab_runner.steps.webhook_step import CreateGiteaWebhookStep
from lab_runner.steps.verify_step import CheckPodRunningStep


class Scale101Module(Module):
    @property
    def id(self) -> int:
        return 3

    @property
    def name(self) -> str:
        return "Ready to Scale 101"

    @property
    def dependencies(self) -> list[int]:
        return [2]

    def get_steps(self, config: Config) -> list[Step]:
        ns = config.namespace
        toolings_ns = config.toolings_namespace
        test_ns = config.test_namespace
        prod_ns = config.prod_namespace

        argocd_webhook_url = f"{config.argocd_url}/api/webhook"

        steps: list[Step] = []

        # 1. Install llama-stack
        steps.append(HelmInstallStep(
            release_name="llama-stack-operator-instance",
            chart=defaults.CHART_LLAMA_STACK,
            namespace=ns,
            values=defaults.LLAMA_STACK_VALUES,
            description="Install LlamaStack operator instance",
        ))

        # 2. Wait for llama-stack pod
        steps.append(WaitForReadyStep(
            label="app.kubernetes.io/instance=llama-stack",
            namespace=ns,
            description="Wait for LlamaStack pod ready",
        ))

        # 3. Install llama-stack-playground
        steps.append(HelmInstallStep(
            release_name="llama-stack-playground",
            chart=defaults.CHART_LLAMA_STACK_PLAYGROUND,
            namespace=ns,
            values=defaults.LLAMA_STACK_PLAYGROUND_VALUES,
            description="Install LlamaStack Playground",
        ))

        # 4. Wait for playground
        steps.append(WaitForReadyStep(
            label="app.kubernetes.io/name=llama-stack-playground",
            namespace=ns,
            description="Wait for LlamaStack Playground ready",
        ))

        # 5. Create workbench notebook CR
        steps.append(CreateNotebookCRStep(
            namespace=ns,
        ))

        # 6. Wait for workbench
        steps.append(WaitForReadyStep(
            label=f"app={ns}",
            namespace=ns,
            timeout=600,
            description="Wait for workbench pod ready",
        ))

        # 7. Install canopy-backend
        steps.append(HelmInstallStep(
            release_name="canopy-backend",
            chart=defaults.CHART_CANOPY_BACKEND,
            namespace=ns,
            values=defaults.CANOPY_BACKEND_VALUES,
            description="Install Canopy Backend",
        ))

        # 8. Wait for backend
        steps.append(WaitForReadyStep(
            label="app.kubernetes.io/name=canopy-be",
            namespace=ns,
            description="Wait for Canopy Backend ready",
        ))

        # 9. Upgrade canopy-ui with backend endpoint
        ui_values = {
            **defaults.CANOPY_UI_UPGRADE_VALUES_M03,
            "LLM_ENDPOINT": config.llm_endpoint,
        }
        steps.append(HelmUpgradeStep(
            release_name="canopy-ui",
            chart=defaults.CHART_CANOPY_UI,
            namespace=ns,
            values=ui_values,
            verify_key="image.tag",
            verify_value="0.11",
            description="Upgrade Canopy UI (add backend, image 0.11)",
        ))

        # 10. Wait for UI redeployed
        steps.append(WaitForReadyStep(
            label="app.kubernetes.io/name=canopy-ui",
            namespace=ns,
            description="Wait for Canopy UI redeployed",
        ))

        # 11. Git: update genaiops-gitops (appset-toolings + bootstrap config)
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "appset-toolings.yaml": defaults.appset_toolings_yaml(config.username, config.cluster_domain),
                "toolings/bootstrap/config.yaml": defaults.bootstrap_config_yaml(config.username),
                "toolings/minio/config.yaml": defaults.minio_toolings_config_yaml(),
            },
            commit_message="Configure toolings ApplicationSet with user values",
            verify_repo="genaiops-gitops",
            verify_file="appset-toolings.yaml",
            verify_content=config.username,
            description="Update genaiops-gitops: appset-toolings + bootstrap config",
        ))

        # 12. Apply appset-toolings.yaml
        steps.append(ApplyManifestStep(
            manifest=defaults.appset_toolings_yaml(config.username, config.cluster_domain),
            namespace=toolings_ns,
            resource_type="applicationset",
            resource_name="genaiops-toolings-appset",
            description="Apply toolings ApplicationSet",
        ))

        # 13. Wait for ArgoCD tooling apps
        steps.append(WaitForArgoCDAppsStep(
            app_names=["bootstrap", "minio"],
            namespace=toolings_ns,
            timeout=300,
            description="Wait for tooling ArgoCD apps to sync",
        ))

        # 14. Register summarization prompt in toolings MLflow (with prod alias)
        steps.append(CreateMLflowPromptStep(
            name=defaults.MLFLOW_PROMPT_NAME,
            template=defaults.SYSTEM_PROMPT,
            namespace=toolings_ns,
            aliases=["prod"],
            commit_message="Production summarization prompt",
            description=f"Register '{defaults.MLFLOW_PROMPT_NAME}' prompt in {toolings_ns} MLflow (alias: prod)",
        ))

        # 15. Git: clone backend, create values-test.yaml + values-prod.yaml
        steps.append(CloneAndModifyStep(
            repo_url=config.backend_repo_url,
            modifications={
                "chart/values-test.yaml": defaults.backend_values_test_yaml(),
                "chart/values-prod.yaml": defaults.backend_values_prod_yaml(),
            },
            commit_message="Add values-test.yaml and values-prod.yaml",
            verify_repo="backend",
            verify_file="chart/values-test.yaml",
            verify_content="summarization",
            description="Add backend values files for test and prod",
        ))

        # 16. Git: add canopy/{test,prod}/{frontend,backend}/config.yaml + appsets
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "canopy/test/frontend/config.yaml": defaults.gitops_test_frontend_config_yaml(),
                "canopy/test/backend/config.yaml": defaults.gitops_test_backend_config_yaml(config.username, config.cluster_domain),
                "canopy/prod/frontend/config.yaml": defaults.gitops_prod_frontend_config_yaml(),
                "canopy/prod/backend/config.yaml": defaults.gitops_prod_backend_config_yaml(config.username, config.cluster_domain),
                "appset-test.yaml": defaults.appset_test_yaml(config.username, config.cluster_domain),
                "appset-prod.yaml": defaults.appset_prod_yaml(config.username, config.cluster_domain),
            },
            commit_message="Add test/prod configs and ApplicationSets",
            verify_repo="genaiops-gitops",
            verify_file="appset-test.yaml",
            verify_content=config.username,
            description="Add test/prod configs and ApplicationSets to genaiops-gitops",
        ))

        # 17. Apply appset-test.yaml + appset-prod.yaml
        steps.append(ApplyManifestStep(
            manifest=defaults.appset_test_yaml(config.username, config.cluster_domain),
            namespace=toolings_ns,
            resource_type="applicationset",
            resource_name="canopy-test-appset",
            description="Apply test ApplicationSet",
        ))
        steps.append(ApplyManifestStep(
            manifest=defaults.appset_prod_yaml(config.username, config.cluster_domain),
            namespace=toolings_ns,
            resource_type="applicationset",
            resource_name="canopy-prod-appset",
            description="Apply prod ApplicationSet",
        ))

        # 18. Wait for test/prod ArgoCD apps (no llama-stack — pre-deployed platform infra)
        steps.append(WaitForArgoCDAppsStep(
            app_names=["frontend-test", "backend-test", "frontend-prod", "backend-prod"],
            namespace=toolings_ns,
            timeout=600,
            description="Wait for test/prod ArgoCD apps to sync",
        ))

        # 19. Create Gitea webhook: genaiops-gitops → ArgoCD
        steps.append(CreateGiteaWebhookStep(
            repo_name="genaiops-gitops",
            target_url=argocd_webhook_url,
            description="Create webhook: genaiops-gitops → ArgoCD",
        ))

        # 20. Create Gitea webhook: backend → ArgoCD
        steps.append(CreateGiteaWebhookStep(
            repo_name="backend",
            target_url=argocd_webhook_url,
            description="Create webhook: backend → ArgoCD",
        ))

        # 21. Clone repos inside workbench
        steps.append(CloneInsideWorkbenchStep(
            repos=[
                (config.experiments_repo_url, "experiments"),
                (config.gitops_repo_url, "genaiops-gitops"),
                (config.backend_repo_url, "backend"),
            ],
            namespace=ns,
            description="Clone repos inside workbench",
        ))

        # 22. Set git config inside workbench
        steps.append(SetGitConfigInWorkbenchStep(namespace=ns))

        # 23. Verify: all deployments healthy
        for env_ns, env_name in [(test_ns, "test"), (prod_ns, "prod")]:
            steps.append(CheckPodRunningStep(
                label="app.kubernetes.io/name=canopy-be",
                namespace=env_ns,
                description=f"Verify backend running in {env_name}",
            ))

        return steps
