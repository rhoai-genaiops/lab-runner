"""Module 11: MaaS - Deploy LiteMaaS."""

import tempfile
from pathlib import Path

from git import Repo

from lab_runner.config import Config
from lab_runner.modules.base import Module
from lab_runner.steps.base import Step, StepResult
from lab_runner.steps.helm_step import HelmInstallStep
from lab_runner.steps.kube_step import WaitForReadyStep
from lab_runner.steps.verify_step import CheckRouteAccessibleStep

LITEMAAS_REPO = "https://github.com/rh-aiservices-bu/litemaas.git"


class CreateProjectStep(Step):
    """Create an OpenShift project (namespace) if it doesn't exist."""

    def __init__(self, project: str, description: str | None = None):
        self.project = project
        self.description = description or f"Create project '{project}'"
        self.active_description = f"Creating project {project}..."

    def verify(self, config: Config) -> bool:
        from lab_runner.clients import openshift as oc
        return oc.resource_exists("namespace", self.project)

    def run(self, config: Config) -> StepResult:
        import subprocess
        r = subprocess.run(
            ["oc", "new-project", self.project],
            capture_output=True, text=True, check=False, timeout=30,
        )
        if r.returncode != 0:
            # Project may already exist
            if "already exists" in (r.stderr or ""):
                return StepResult.skipped("Project already exists")
            return StepResult.failed(r.stderr or r.stdout or "Failed to create project")
        return StepResult.success(output=r.stdout)


class LiteMaaSInstallStep(Step):
    """Clone litemaas repo and install via Helm."""

    def __init__(self, namespace: str, description: str | None = None):
        self.namespace = namespace
        self.description = description or "Install LiteMaaS via Helm"
        self.active_description = "Installing LiteMaaS..."

    def verify(self, config: Config) -> bool:
        from lab_runner.clients import helm
        return helm.release_exists("litemaas", self.namespace)

    def run(self, config: Config) -> StepResult:
        from lab_runner.clients import helm

        # Clone the litemaas repo
        tmpdir = tempfile.mkdtemp(prefix="labrunner-litemaas-")
        try:
            Repo.clone_from(LITEMAAS_REPO, tmpdir, depth=1)
        except Exception as e:
            return StepResult.failed(f"Failed to clone litemaas repo: {e}")

        chart_path = str(Path(tmpdir) / "deployment" / "helm" / "litemaas")
        if not Path(chart_path).is_dir():
            return StepResult.failed(f"Chart path not found: {chart_path}")

        values = {
            "route": {"enabled": True},
            "backend": {"nodeTlsRejectUnauthorized": "0"},
        }

        try:
            output = helm.install(
                "litemaas",
                chart_path,
                self.namespace,
                values=values,
            )
            return StepResult.success(output=output)
        except Exception as e:
            return StepResult.failed(str(e))


class MaaSModule(Module):
    @property
    def id(self) -> int:
        return 11

    @property
    def name(self) -> str:
        return "MaaS"

    @property
    def dependencies(self) -> list[int]:
        return [9, 10]

    def get_steps(self, config: Config) -> list[Step]:
        maas_ns = config.maas_namespace

        steps: list[Step] = []

        # 1. Create MaaS project
        steps.append(CreateProjectStep(
            project=maas_ns,
            description=f"Create project '{maas_ns}'",
        ))

        # 2. Install LiteMaaS via Helm
        steps.append(LiteMaaSInstallStep(
            namespace=maas_ns,
            description="Install LiteMaaS via Helm",
        ))

        # 3. Wait for LiteMaaS pods ready
        steps.append(WaitForReadyStep(
            label="app.kubernetes.io/instance=litemaas",
            namespace=maas_ns,
            timeout=300,
            description="Wait for LiteMaaS pods ready",
        ))

        # 4. Verify LiteMaaS route accessible
        steps.append(CheckRouteAccessibleStep(
            url=f"https://litemaas-{maas_ns}.{config.cluster_domain}",
            retries=12,
            description="Verify LiteMaaS UI accessible",
        ))

        return steps
