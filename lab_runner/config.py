"""Configuration dataclass with all derived URLs and namespaces."""

from dataclasses import dataclass, field


@dataclass
class Config:
    username: str
    password: str
    cluster_domain: str
    dry_run: bool = False
    verbose: bool = False

    # Derived properties
    @property
    def api_url(self) -> str:
        domain_parts = self.cluster_domain.split(".", 1)
        base = domain_parts[1] if len(domain_parts) > 1 else self.cluster_domain
        return f"https://api.{base}:6443"

    @property
    def namespace(self) -> str:
        return f"{self.username}-canopy"

    @property
    def test_namespace(self) -> str:
        return f"{self.username}-test"

    @property
    def prod_namespace(self) -> str:
        return f"{self.username}-prod"

    @property
    def toolings_namespace(self) -> str:
        return f"{self.username}-toolings"

    @property
    def gitea_url(self) -> str:
        return f"https://gitea-gitea.{self.cluster_domain}"

    @property
    def gitea_api_url(self) -> str:
        return f"{self.gitea_url}/api/v1"

    @property
    def argocd_url(self) -> str:
        return f"https://argocd-server-{self.username}-toolings.{self.cluster_domain}"

    @property
    def llm_endpoint(self) -> str:
        return f"https://llama32-ai501.{self.cluster_domain}"

    @property
    def gitops_repo_url(self) -> str:
        return f"{self.gitea_url}/{self.username}/genaiops-gitops.git"

    @property
    def backend_repo_url(self) -> str:
        return f"{self.gitea_url}/{self.username}/backend.git"

    @property
    def evals_repo_url(self) -> str:
        return f"{self.gitea_url}/{self.username}/evals.git"

    @property
    def experiments_repo_url(self) -> str:
        return f"{self.gitea_url}/{self.username}/experiments.git"

    @property
    def helmcharts_repo_url(self) -> str:
        return "https://github.com/rhoai-genaiops/genaiops-helmcharts.git"

    @property
    def workbench_pod_label(self) -> str:
        return "opendatahub.io/workbenches=true"

    @property
    def maas_namespace(self) -> str:
        return f"{self.username}-maas"

    @property
    def minio_endpoint(self) -> str:
        return f"http://minio.{self.namespace}.svc.cluster.local:9000"

    def route_url(self, name: str, ns: str | None = None) -> str:
        ns = ns or self.namespace
        return f"https://{name}-{ns}.{self.cluster_domain}"
