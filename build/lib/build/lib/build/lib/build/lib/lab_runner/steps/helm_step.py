"""Helm install and upgrade steps."""

import subprocess

from lab_runner.clients import helm
from lab_runner.config import Config
from lab_runner.steps.base import Step, StepResult


def _error_message(e: Exception) -> tuple[str, str]:
    """Extract message and output from an exception."""
    if isinstance(e, subprocess.CalledProcessError):
        return str(e), (e.stderr or e.output or "")
    return str(e), ""


class HelmInstallStep(Step):
    """Install a Helm chart if not already installed."""

    def __init__(
        self,
        release_name: str,
        chart: str,
        namespace: str,
        values: dict | None = None,
        create_namespace: bool = False,
        description: str | None = None,
    ):
        self.release_name = release_name
        self.chart = chart
        self.namespace = namespace
        self.values = values
        self.create_namespace = create_namespace
        self.description = description or f"Install Helm release '{release_name}'"
        self.active_description = f"Installing {release_name}..."

    def verify(self, config: Config) -> bool:
        return helm.release_exists(self.release_name, self.namespace)

    def run(self, config: Config) -> StepResult:
        try:
            output = helm.install(
                self.release_name,
                self.chart,
                self.namespace,
                values=self.values,
                create_namespace=self.create_namespace,
            )
            return StepResult.success(output=output)
        except Exception as e:
            msg, output = _error_message(e)
            return StepResult.failed(msg, output=output)


class HelmUpgradeStep(Step):
    """Upgrade (or install) a Helm release with new values."""

    def __init__(
        self,
        release_name: str,
        chart: str,
        namespace: str,
        values: dict | None = None,
        verify_key: str | None = None,
        verify_value: object = None,
        description: str | None = None,
    ):
        self.release_name = release_name
        self.chart = chart
        self.namespace = namespace
        self.values = values
        self.verify_key = verify_key
        self.verify_value = verify_value
        self.description = description or f"Upgrade Helm release '{release_name}'"
        self.active_description = f"Upgrading {release_name}..."

    def verify(self, config: Config) -> bool:
        if not helm.release_exists(self.release_name, self.namespace):
            return False
        if self.verify_key is not None:
            current = helm.get_values(self.release_name, self.namespace)
            return _nested_get(current, self.verify_key) == self.verify_value
        # No verify_key means always run the upgrade (idempotent)
        return False

    def run(self, config: Config) -> StepResult:
        try:
            output = helm.upgrade(
                self.release_name,
                self.chart,
                self.namespace,
                values=self.values,
                install=True,
            )
            return StepResult.success(output=output)
        except Exception as e:
            msg, output = _error_message(e)
            return StepResult.failed(msg, output=output)


def _nested_get(d: dict, key: str) -> object:
    """Get a dotted key from a nested dict. E.g., 'rag.enabled' -> d['rag']['enabled']."""
    parts = key.split(".")
    current = d
    for p in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(p)
    return current
