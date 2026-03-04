"""Module 5: Grounded AI (RAG) - Milvus, RAG, document ingestion."""

from lab_runner.config import Config
from lab_runner import defaults
from lab_runner.modules.base import Module
from lab_runner.steps.base import Step
from lab_runner.steps.helm_step import HelmUpgradeStep
from lab_runner.steps.kube_step import WaitForArgoCDAppsStep, WaitForReadyStep
from lab_runner.steps.git_step import CloneAndModifyStep
from lab_runner.steps.webhook_step import ConfigureMinIOWebhookStep, UploadDocumentToMinIOStep
from lab_runner.steps.verify_step import CheckPodRunningStep


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
        prod_ns = config.prod_namespace

        steps: list[Step] = []

        # 1. Upgrade llama-stack (enable RAG)
        steps.append(HelmUpgradeStep(
            release_name="llama-stack-operator-instance",
            chart=defaults.CHART_LLAMA_STACK,
            namespace=ns,
            values=defaults.LLAMA_STACK_RAG_VALUES,
            verify_key="rag.enabled",
            verify_value=True,
            description="Upgrade LlamaStack (enable RAG)",
        ))

        # 2. Add milvus configs for test and prod
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "canopy/test/milvus/config.yaml": defaults.milvus_config_yaml("test"),
                "canopy/prod/milvus/config.yaml": defaults.milvus_config_yaml("prod"),
            },
            commit_message="Add Milvus configs for test and prod",
            verify_repo="genaiops-gitops",
            verify_file="canopy/test/milvus/config.yaml",
            description="Add Milvus configs for test and prod",
        ))

        # 3. Wait for Milvus pods
        steps.append(WaitForArgoCDAppsStep(
            app_names=["milvus-test", "milvus-prod"],
            namespace=toolings_ns,
            timeout=600,
            description="Wait for Milvus deployed in test and prod",
        ))

        # 4. Update test/prod llama-stack configs (enable RAG)
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "canopy/test/llama-stack/config.yaml": defaults.gitops_llama_stack_rag_config_yaml("test"),
                "canopy/prod/llama-stack/config.yaml": defaults.gitops_llama_stack_rag_config_yaml("prod"),
            },
            commit_message="Enable RAG in test/prod llama-stack configs",
            verify_repo="genaiops-gitops",
            verify_file="canopy/test/llama-stack/config.yaml",
            verify_content="rag",
            description="Enable RAG in test/prod llama-stack configs",
        ))

        # 5. Add documents bucket to toolings/minio config
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "toolings/minio/config.yaml": defaults.minio_documents_config_yaml(),
            },
            commit_message="Add documents bucket to MinIO config",
            verify_repo="genaiops-gitops",
            verify_file="toolings/minio/config.yaml",
            verify_content="documents",
            description="Add documents bucket to MinIO tooling config",
        ))

        # 6. Upload sample documents to MinIO (skipped - requires MinIO API with content)
        # This would normally upload PDFs/docs. Skipping as there's no content to upload.

        # 7. Enable information-search in backend values-test.yaml
        steps.append(CloneAndModifyStep(
            repo_url=config.backend_repo_url,
            modifications={
                "chart/values-test.yaml": defaults.backend_values_test_rag_yaml(),
            },
            commit_message="Enable information-search feature in backend",
            verify_repo="backend",
            verify_file="chart/values-test.yaml",
            verify_content="information-search",
            description="Enable information-search in backend test values",
        ))

        # 8. Create evals/information-search test files
        steps.append(CloneAndModifyStep(
            repo_url=config.evals_repo_url,
            modifications={
                "information-search/information_search_tests.yaml": defaults.evals_information_search_test_yaml(),
                "information-search/judge_prompt.txt": defaults.evals_information_search_judge_prompt(),
            },
            commit_message="Add information-search evaluation tests",
            verify_repo="evals",
            verify_file="information-search/information_search_tests.yaml",
            description="Add information-search eval test files",
        ))

        # 9. Add doc-ingestion-pipeline config
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "toolings/doc-ingestion-pipeline/config.yaml": defaults.doc_ingestion_pipeline_config_yaml(
                    config.username, config.cluster_domain
                ),
            },
            commit_message="Add doc ingestion pipeline config",
            verify_repo="genaiops-gitops",
            verify_file="toolings/doc-ingestion-pipeline/config.yaml",
            description="Add doc ingestion pipeline to toolings",
        ))

        # 10. Wait for doc ingestion pipeline deployed
        steps.append(WaitForArgoCDAppsStep(
            app_names=["doc-ingestion-pipeline"],
            namespace=toolings_ns,
            timeout=300,
            description="Wait for doc ingestion pipeline deployed",
        ))

        # 11. Configure MinIO webhook for document uploads → Tekton
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

        # 12. Upload a document to MinIO to trigger ingestion pipeline
        steps.append(UploadDocumentToMinIOStep(
            bucket="documents",
            doc_filename="biotechnology-syllabus-240-ects.pdf",
            description="Upload PDF to MinIO documents bucket",
        ))

        # 13. Verify: Milvus, pods healthy
        steps.append(CheckPodRunningStep(
            label="app.kubernetes.io/name=milvus",
            namespace=test_ns,
            description="Verify Milvus running in test",
        ))

        return steps
