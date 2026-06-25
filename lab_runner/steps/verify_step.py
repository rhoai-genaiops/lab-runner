"""Verification-only steps: route checks, pod checks, health checks."""

import requests
import urllib3

from lab_runner.clients import openshift as oc
from lab_runner.config import Config
from lab_runner.steps.base import Step, StepResult

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CheckRouteAccessibleStep(Step):
    """Verify that an OpenShift route is accessible via HTTP(S)."""

    def __init__(
        self,
        url: str,
        expected_status: int = 200,
        retries: int = 6,
        description: str | None = None,
    ):
        self.url = url
        self.expected_status = expected_status
        self.retries = retries
        self.description = description or f"Verify route accessible: {url}"
        self.active_description = f"Checking {url}..."

    def verify(self, config: Config) -> bool:
        return self._check()

    def run(self, config: Config) -> StepResult:
        import time

        last_status = None
        for attempt in range(self.retries):
            try:
                r = requests.get(self.url, timeout=15, verify=False, allow_redirects=True)
                if r.status_code == self.expected_status:
                    return StepResult.success()
                last_status = r.status_code
            except Exception as e:
                last_status = str(e)
            if attempt < self.retries - 1:
                time.sleep(10)
        return StepResult.failed(
            f"Route {self.url} not accessible after retries (last: {last_status}, expected {self.expected_status})"
        )

    def _check(self) -> bool:
        try:
            r = requests.get(self.url, timeout=15, verify=False, allow_redirects=True)
            return r.status_code == self.expected_status
        except Exception:
            return False

    def skip_if_done(self) -> bool:
        return False  # Always run verification


class CheckPodRunningStep(Step):
    """Verify that a pod with a given label is running, with retries."""

    def __init__(self, label: str, namespace: str, timeout: int = 300, description: str | None = None):
        self.label = label
        self.namespace = namespace
        self.timeout = timeout
        self.description = description or f"Verify pod running: {label}"
        self.active_description = f"Checking pod {label}..."

    def verify(self, config: Config) -> bool:
        return oc.pod_is_running(self.label, self.namespace)

    def run(self, config: Config) -> StepResult:
        import time

        deadline = time.time() + self.timeout
        while time.time() < deadline:
            if oc.pod_is_running(self.label, self.namespace):
                return StepResult.success()
            time.sleep(10)
        return StepResult.failed(f"No running pod with label '{self.label}' in {self.namespace} after {self.timeout}s")

    def skip_if_done(self) -> bool:
        return False


class CheckAllPodsRunningStep(Step):
    """Verify that all pods matching a label are running, with retries."""

    def __init__(self, label: str, namespace: str, min_count: int = 1, timeout: int = 300, description: str | None = None):
        self.label = label
        self.namespace = namespace
        self.min_count = min_count
        self.timeout = timeout
        self.description = description or f"Verify all pods running: {label}"
        self.active_description = f"Checking pods {label}..."

    def verify(self, config: Config) -> bool:
        return oc.all_pods_running(self.label, self.namespace, self.min_count)

    def run(self, config: Config) -> StepResult:
        import time

        deadline = time.time() + self.timeout
        while time.time() < deadline:
            if oc.all_pods_running(self.label, self.namespace, self.min_count):
                return StepResult.success()
            time.sleep(10)
        return StepResult.failed(f"Not all pods with label '{self.label}' running in {self.namespace} after {self.timeout}s")

    def skip_if_done(self) -> bool:
        return False


class CheckHelmReleaseStep(Step):
    """Verify that a Helm release exists."""

    def __init__(self, release_name: str, namespace: str, description: str | None = None):
        self.release_name = release_name
        self.namespace = namespace
        self.description = description or f"Verify Helm release: {release_name}"
        self.active_description = f"Checking release {release_name}..."

    def verify(self, config: Config) -> bool:
        from lab_runner.clients import helm
        return helm.release_exists(self.release_name, self.namespace)

    def run(self, config: Config) -> StepResult:
        if self.verify(config):
            return StepResult.success()
        return StepResult.failed(f"Helm release '{self.release_name}' not found in {self.namespace}")

    def skip_if_done(self) -> bool:
        return False


class CheckResourceExistsStep(Step):
    """Verify that a Kubernetes resource exists."""

    def __init__(
        self,
        resource_type: str,
        name: str,
        namespace: str | None = None,
        description: str | None = None,
    ):
        self.resource_type = resource_type
        self.name = name
        self.namespace = namespace
        self.description = description or f"Verify {resource_type}/{name} exists"
        self.active_description = f"Checking {resource_type}/{name}..."

    def verify(self, config: Config) -> bool:
        return oc.resource_exists(self.resource_type, self.name, self.namespace)

    def run(self, config: Config) -> StepResult:
        if self.verify(config):
            return StepResult.success()
        return StepResult.failed(f"{self.resource_type}/{self.name} not found")

    def skip_if_done(self) -> bool:
        return False
