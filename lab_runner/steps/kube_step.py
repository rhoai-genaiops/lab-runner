"""Kubernetes resource steps: apply manifests, wait for readiness, create CRs."""

import yaml

from lab_runner.clients import openshift as oc
from lab_runner.config import Config
from lab_runner.steps.base import Step, StepResult


class OcLoginStep(Step):
    """Log in to OpenShift cluster."""

    description = "Log in to OpenShift cluster"
    active_description = "Logging in to OpenShift..."

    def verify(self, config: Config) -> bool:
        current_user = oc.whoami()
        return current_user == config.username

    def run(self, config: Config) -> StepResult:
        try:
            output = oc.login(config)
            return StepResult.success(output=output)
        except Exception as e:
            return StepResult.failed(f"Login failed: {e}")


class ApplyManifestStep(Step):
    """Apply a YAML manifest to the cluster."""

    def __init__(
        self,
        manifest: str,
        namespace: str | None = None,
        resource_type: str = "resource",
        resource_name: str = "",
        description: str | None = None,
    ):
        self.manifest = manifest
        self.namespace = namespace
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.description = description or f"Apply {resource_type} '{resource_name}'"
        self.active_description = f"Applying {resource_type}..."

    def verify(self, config: Config) -> bool:
        if self.resource_type and self.resource_name:
            return oc.resource_exists(self.resource_type, self.resource_name, self.namespace)
        return False

    def run(self, config: Config) -> StepResult:
        try:
            output = oc.apply(self.manifest, self.namespace)
            return StepResult.success(output=output)
        except Exception as e:
            return StepResult.failed(str(e))


class WaitForReadyStep(Step):
    """Wait for a pod/deployment to become ready."""

    def __init__(
        self,
        label: str,
        namespace: str,
        timeout: int = 300,
        description: str | None = None,
    ):
        self.label = label
        self.namespace = namespace
        self.timeout = timeout
        self.description = description or f"Wait for pod ({label}) ready"
        self.active_description = f"Waiting for {label}..."

    def verify(self, config: Config) -> bool:
        return oc.pod_is_running(self.label, self.namespace)

    def run(self, config: Config) -> StepResult:
        import time

        deadline = time.time() + self.timeout
        while time.time() < deadline:
            if oc.pod_is_running(self.label, self.namespace):
                return StepResult.success()
            time.sleep(10)
        return StepResult.failed(
            f"Timed out waiting for pod with label '{self.label}' in {self.namespace}"
        )


class WaitForRolloutStep(Step):
    """Wait for a deployment rollout to complete."""

    def __init__(
        self,
        deployment_name: str,
        namespace: str,
        timeout: int = 300,
        description: str | None = None,
    ):
        self.deployment_name = deployment_name
        self.namespace = namespace
        self.timeout = timeout
        self.description = description or f"Wait for deployment '{deployment_name}' rollout"
        self.active_description = f"Waiting for {deployment_name} rollout..."

    def verify(self, config: Config) -> bool:
        return oc.pod_is_running(f"app={self.deployment_name}", self.namespace)

    def run(self, config: Config) -> StepResult:
        ok = oc.wait_for_rollout(self.deployment_name, self.namespace, self.timeout)
        if ok:
            return StepResult.success()
        return StepResult.failed(f"Rollout timed out for {self.deployment_name}")


class CreateNotebookCRStep(Step):
    """Create a Notebook custom resource for Code Server workbench."""

    def __init__(self, namespace: str, name: str = "code-server-workbench"):
        self.namespace = namespace
        self.name = name
        self.description = f"Create Notebook CR '{namespace}'"
        self.active_description = f"Creating workbench {namespace}..."

    def verify(self, config: Config) -> bool:
        return oc.resource_exists("notebook", self.namespace, self.namespace)

    def run(self, config: Config) -> StepResult:
        ns = self.namespace
        username = config.username
        notebook_args = (
            f"--ServerApp.port=8888\n"
            f"                  --ServerApp.token=''\n"
            f"                  --ServerApp.password=''\n"
            f"                  --ServerApp.base_url=/notebook/{ns}/{ns}\n"
            f"                  --ServerApp.quit_button=False"
        )
        image = "image-registry.openshift-image-registry.svc:5000/redhat-ods-applications/ai501-custom-code-server:0.5"

        manifest = yaml.dump({
            "apiVersion": "kubeflow.org/v1",
            "kind": "Notebook",
            "metadata": {
                "name": ns,
                "namespace": ns,
                "labels": {
                    "app": ns,
                    "opendatahub.io/dashboard": "true",
                    "opendatahub.io/odh-managed": "true",
                    "opendatahub.io/user": username,
                },
                "annotations": {
                    "opendatahub.io/image-display-name": "AI501 - Custom Code Server",
                    "openshift.io/display-name": ns,
                    "openshift.io/description": "",
                    "notebooks.opendatahub.io/last-image-selection": "ai501-custom-code-server:0.5",
                    "opendatahub.io/hardware-profile-namespace": "redhat-ods-applications",
                    "opendatahub.io/username": username,
                    "opendatahub.io/hardware-profile-name": "default-profile",
                    "notebooks.opendatahub.io/inject-auth": "true",
                },
            },
            "spec": {
                "template": {
                    "spec": {
                        "enableServiceLinks": False,
                        "serviceAccountName": ns,
                        "containers": [{
                            "name": ns,
                            "image": image,
                            "imagePullPolicy": "Always",
                            "workingDir": "/opt/app-root/src",
                            "resources": {
                                "requests": {"cpu": "2", "memory": "4Gi"},
                                "limits": {"cpu": "2", "memory": "4Gi"},
                            },
                            "ports": [{"containerPort": 8888, "name": "notebook-port", "protocol": "TCP"}],
                            "readinessProbe": {
                                "httpGet": {"path": f"/notebook/{ns}/{ns}/api", "port": "notebook-port", "scheme": "HTTP"},
                                "initialDelaySeconds": 10,
                                "periodSeconds": 5,
                                "failureThreshold": 3,
                                "successThreshold": 1,
                                "timeoutSeconds": 1,
                            },
                            "livenessProbe": {
                                "httpGet": {"path": f"/notebook/{ns}/{ns}/api", "port": "notebook-port", "scheme": "HTTP"},
                                "initialDelaySeconds": 10,
                                "periodSeconds": 5,
                                "failureThreshold": 3,
                                "successThreshold": 1,
                                "timeoutSeconds": 1,
                            },
                            "env": [
                                {"name": "NOTEBOOK_ARGS", "value": notebook_args},
                                {"name": "JUPYTER_IMAGE", "value": image},
                                {"name": "PIP_CERT", "value": "/etc/pki/tls/custom-certs/ca-bundle.crt"},
                                {"name": "REQUESTS_CA_BUNDLE", "value": "/etc/pki/tls/custom-certs/ca-bundle.crt"},
                                {"name": "SSL_CERT_FILE", "value": "/etc/pki/tls/custom-certs/ca-bundle.crt"},
                                {"name": "PIPELINES_SSL_SA_CERTS", "value": "/etc/pki/tls/custom-certs/ca-bundle.crt"},
                                {"name": "KF_PIPELINES_SSL_SA_CERTS", "value": "/etc/pki/tls/custom-certs/ca-bundle.crt"},
                                {"name": "GIT_SSL_CAINFO", "value": "/etc/pki/tls/custom-certs/ca-bundle.crt"},
                            ],
                            "volumeMounts": [
                                {"name": f"{ns}-storage", "mountPath": "/opt/app-root/src/"},
                                {"name": "shm", "mountPath": "/dev/shm"},
                                {"name": "trusted-ca", "mountPath": "/etc/pki/tls/custom-certs/ca-bundle.crt", "subPath": "ca-bundle.crt", "readOnly": True},
                                {"name": "runtime-images", "mountPath": "/opt/app-root/pipeline-runtimes/"},
                            ],
                        }],
                        "volumes": [
                            {"name": f"{ns}-storage", "persistentVolumeClaim": {"claimName": f"{ns}-storage"}},
                            {"name": "shm", "emptyDir": {"medium": "Memory"}},
                            {"name": "trusted-ca", "configMap": {"name": "workbench-trusted-ca-bundle", "optional": True, "items": [{"key": "ca-bundle.crt", "path": "ca-bundle.crt"}]}},
                            {"name": "runtime-images", "configMap": {"name": "pipeline-runtime-images", "optional": True}},
                        ],
                    },
                },
            },
        })

        # Create PVC first
        pvc_manifest = yaml.dump({
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {
                "name": f"{ns}-storage",
                "namespace": ns,
            },
            "spec": {
                "accessModes": ["ReadWriteOnce"],
                "resources": {"requests": {"storage": "20Gi"}},
            },
        })

        try:
            oc.apply(pvc_manifest, self.namespace)
            output = oc.apply(manifest, self.namespace)
            return StepResult.success(output=output)
        except Exception as e:
            return StepResult.failed(str(e))


class WaitForArgoCDAppsStep(Step):
    """Wait for ArgoCD applications to become healthy."""

    def __init__(
        self,
        app_names: list[str],
        namespace: str,
        timeout: int = 300,
        description: str | None = None,
    ):
        self.app_names = app_names
        self.namespace = namespace
        self.timeout = timeout
        self.description = description or f"Wait for ArgoCD apps: {', '.join(app_names)}"
        self.active_description = "Waiting for ArgoCD sync..."

    def verify(self, config: Config) -> bool:
        for name in self.app_names:
            health = oc.get_argocd_app_health(name, self.namespace)
            if health != "Healthy":
                return False
        return True

    def run(self, config: Config) -> StepResult:
        ok = oc.wait_for_argocd_apps(self.app_names, self.namespace, self.timeout)
        if ok:
            return StepResult.success()
        return StepResult.failed(f"Timed out waiting for ArgoCD apps: {self.app_names}")
