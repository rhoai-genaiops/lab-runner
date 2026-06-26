"""Module 5: Grounded AI (RAG) - Milvus, OGX, document ingestion."""

from lab_runner.config import Config
from lab_runner import defaults
from lab_runner.modules.base import Module
from lab_runner.steps.base import Step
from lab_runner.steps.kube_step import ApplyManifestStep, WaitForArgoCDAppsStep, WaitForReadyStep
from lab_runner.steps.git_step import CloneAndModifyStep
from lab_runner.steps.webhook_step import ConfigureMinIOWebhookStep, UploadDocumentToMinIOStep
from lab_runner.steps.verify_step import CheckPodRunningStep
from lab_runner.steps.mlflow_step import CreateMLflowPromptStep
from lab_runner.steps.helm_step import HelmInstallStep


class RAGModule(Module):
    @property
    def id(self) -> int:
        return 5

    @property
    def name(self) -> str:
        return "Grounded AI (RAG)"

    @property
    def dependencies(self) -> list[int]:
        return [4]

    def get_steps(self, config: Config) -> list[Step]:
        ns = config.namespace
        toolings_ns = config.toolings_namespace
        test_ns = config.test_namespace

        steps: list[Step] = []

        # 1. Add Milvus configs for test and prod
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "canopy/test/milvus/config.yaml": defaults.milvus_config_yaml("test"),
                "canopy/prod/milvus/config.yaml": defaults.milvus_config_yaml("prod"),
            },
            commit_message="Add Milvus test & prod vector databases",
            verify_repo="genaiops-gitops",
            verify_file="canopy/test/milvus/config.yaml",
            description="Add Milvus configs for test and prod",
        ))

        # 2. Wait for Milvus ArgoCD apps
        steps.append(WaitForArgoCDAppsStep(
            app_names=["milvus-test", "milvus-prod"],
            namespace=toolings_ns,
            timeout=600,
            description="Wait for Milvus deployed in test and prod",
        ))

        # 3. Create ExternalName service so milvus-test resolves across namespaces
        steps.append(ApplyManifestStep(
            manifest=defaults.milvus_externalname_manifest("milvus-test", test_ns),
            namespace=ns,
            resource_type="service",
            resource_name="milvus-test",
            description="Create Milvus ExternalName service in canopy",
        ))

        # 4. Install llama-stack (OGX) in userX-canopy
        steps.append(HelmInstallStep(
            release_name="llama-stack-operator-instance",
            chart=defaults.CHART_LLAMA_STACK,
            namespace=ns,
            values=defaults.LLAMA_STACK_RAG_VALUES,
            description="Install LlamaStack (OGX) in canopy namespace",
        ))

        # 5. Wait for llama-stack ready
        steps.append(WaitForReadyStep(
            label="app=llama-stack",
            namespace=ns,
            description="Wait for LlamaStack ready in canopy",
        ))

        # 3. Add OGX (llama-stack-operator-instance) configs for test and prod
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "canopy/test/ogx/config.yaml": defaults.gitops_ogx_config_yaml("test", config.username),
                "canopy/prod/ogx/config.yaml": defaults.gitops_ogx_config_yaml("prod", config.username),
            },
            commit_message="Add Open GenAI Stack instances",
            verify_repo="genaiops-gitops",
            verify_file="canopy/test/ogx/config.yaml",
            verify_content="rag",
            description="Add OGX (llama-stack) configs for test and prod",
        ))

        # 4. Wait for OGX ArgoCD apps
        steps.append(WaitForArgoCDAppsStep(
            app_names=["ogx-test", "ogx-prod"],
            namespace=toolings_ns,
            timeout=600,
            description="Wait for OGX deployed in test and prod",
        ))

        # 5. Add documents bucket to MinIO tooling config
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "toolings/minio/config.yaml": defaults.minio_documents_config_yaml(),
            },
            commit_message="Add document bucket",
            verify_repo="genaiops-gitops",
            verify_file="toolings/minio/config.yaml",
            verify_content="documents",
            description="Add documents bucket to MinIO tooling config",
        ))

        # 6. Enable information-search in test and prod backend gitops config
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "canopy/test/backend/config.yaml": defaults.gitops_test_backend_rag_config_yaml(
                    config.username, config.cluster_domain
                ),
                "canopy/prod/backend/config.yaml": defaults.gitops_prod_backend_rag_config_yaml(
                    config.username, config.cluster_domain
                ),
            },
            commit_message="Add RAG feature to test and prod",
            verify_repo="genaiops-gitops",
            verify_file="canopy/test/backend/config.yaml",
            verify_content="information-search",
            description="Enable information-search in test and prod backend gitops config",
        ))

        # 7. Create evals/information-search test files
        steps.append(CloneAndModifyStep(
            repo_url=config.evals_repo_url,
            modifications={
                "information-search/information_search_tests.yaml": defaults.evals_information_search_test_yaml(),
                "information-search/judge_prompt.txt": defaults.evals_information_search_judge_prompt(),
            },
            commit_message="RAG eval added",
            verify_repo="evals",
            verify_file="information-search/information_search_tests.yaml",
            description="Add information-search eval test files",
        ))

        # 8. Add doc-ingestion-pipeline tooling config
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "toolings/doc-ingestion-pipeline/config.yaml": defaults.doc_ingestion_pipeline_config_yaml(
                    config.username, config.cluster_domain
                ),
            },
            commit_message="RAG doc ingestion pipeline added",
            verify_repo="genaiops-gitops",
            verify_file="toolings/doc-ingestion-pipeline/config.yaml",
            description="Add doc ingestion pipeline to toolings",
        ))

        # 9. Wait for doc-ingestion-pipeline ArgoCD app
        steps.append(WaitForArgoCDAppsStep(
            app_names=["doc-ingestion-pipeline"],
            namespace=toolings_ns,
            timeout=300,
            description="Wait for doc ingestion pipeline deployed",
        ))

        # 9.5 Wait for doc-ingestion EventListener pod to be ready
        steps.append(CheckPodRunningStep(
            label="eventlistener=canopy-doc-ingestion-event-listener",
            namespace=toolings_ns,
            description="Wait for doc-ingestion EventListener pod ready",
        ))

        # 10. Configure MinIO webhook: documents bucket → doc ingestion Tekton pipeline
        doc_ingestion_el_url = (
            f"http://el-canopy-doc-ingestion-event-listener"
            f".{toolings_ns}.svc.cluster.local:8080"
        )
        steps.append(ConfigureMinIOWebhookStep(
            bucket="documents",
            webhook_id="doc-ingestion-webhook",
            endpoint_url=doc_ingestion_el_url,
            events=["put"],
            description="Configure MinIO webhook: documents → doc ingestion pipeline",
        ))

        # 11. Upload sample document to MinIO to trigger ingestion pipeline
        steps.append(UploadDocumentToMinIOStep(
            bucket="documents",
            doc_filename="biotechnology-syllabus-240-ects.pdf",
            description="Upload PDF to MinIO documents bucket",
        ))

        # 12. Register information-search prompt in toolings MLflow (with prod alias)
        steps.append(CreateMLflowPromptStep(
            name=defaults.INFORMATION_SEARCH_PROMPT_NAME,
            template=defaults.INFORMATION_SEARCH_PROMPT,
            namespace=toolings_ns,
            aliases=["prod"],
            commit_message="Production information-search prompt",
            description=f"Register '{defaults.INFORMATION_SEARCH_PROMPT_NAME}' prompt in {toolings_ns} MLflow (alias: prod)",
        ))

        # 13. Verify Milvus running in test
        steps.append(CheckPodRunningStep(
            label="app.kubernetes.io/name=milvus",
            namespace=test_ns,
            description="Verify Milvus running in test",
        ))

        return steps
