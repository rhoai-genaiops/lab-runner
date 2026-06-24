"""OpenShift (oc) CLI wrapper."""

import json
import subprocess

from lab_runner.config import Config


def _run(args: list[str], check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        capture_output=capture,
        text=True,
        check=check,
        timeout=300,
    )


def login(config: Config) -> str:
    r = _run([
        "oc", "login", config.api_url,
        "-u", config.username,
        "-p", config.password,
        "--insecure-skip-tls-verify=true",
    ])
    return r.stdout


def whoami() -> str | None:
    try:
        r = _run(["oc", "whoami"], check=False)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def apply(manifest: str, namespace: str | None = None) -> str:
    cmd = ["oc", "apply", "-f", "-"]
    if namespace:
        cmd.extend(["-n", namespace])
    r = subprocess.run(
        cmd, input=manifest, capture_output=True, text=True, check=False, timeout=120,
    )
    if r.returncode != 0:
        detail = (r.stderr or r.stdout or "").strip()
        raise RuntimeError(f"oc apply failed: {detail}")
    return r.stdout


def apply_file(path: str, namespace: str | None = None) -> str:
    cmd = ["oc", "apply", "-f", path]
    if namespace:
        cmd.extend(["-n", namespace])
    r = _run(cmd)
    return r.stdout


def get_json(resource: str, name: str, namespace: str | None = None) -> dict | None:
    cmd = ["oc", "get", resource, name, "-o", "json"]
    if namespace:
        cmd.extend(["-n", namespace])
    r = _run(cmd, check=False)
    if r.returncode != 0:
        return None
    return json.loads(r.stdout)


def resource_exists(resource: str, name: str, namespace: str | None = None) -> bool:
    return get_json(resource, name, namespace) is not None


def get_secret_value(name: str, key: str, namespace: str | None = None) -> str | None:
    """Read a decoded value from a Kubernetes secret."""
    import base64
    data = get_json("secret", name, namespace)
    if data is None:
        return None
    encoded = data.get("data", {}).get(key)
    if encoded is None:
        return None
    return base64.b64decode(encoded).decode("utf-8")


def wait_for_ready(
    resource: str,
    name: str,
    namespace: str | None = None,
    timeout: int = 300,
    condition: str = "Ready",
) -> bool:
    cmd = [
        "oc", "wait", f"{resource}/{name}",
        f"--for=condition={condition}",
        f"--timeout={timeout}s",
    ]
    if namespace:
        cmd.extend(["-n", namespace])
    r = _run(cmd, check=False)
    return r.returncode == 0


def wait_for_rollout(
    name: str, namespace: str | None = None, timeout: int = 300,
) -> bool:
    cmd = ["oc", "rollout", "status", f"deployment/{name}", f"--timeout={timeout}s"]
    if namespace:
        cmd.extend(["-n", namespace])
    r = _run(cmd, check=False)
    return r.returncode == 0


def get_pods(label: str, namespace: str | None = None) -> list[dict]:
    cmd = ["oc", "get", "pods", "-l", label, "-o", "json"]
    if namespace:
        cmd.extend(["-n", namespace])
    r = _run(cmd, check=False)
    if r.returncode != 0:
        return []
    data = json.loads(r.stdout)
    return data.get("items", [])


def pod_is_running(label: str, namespace: str | None = None) -> bool:
    pods = get_pods(label, namespace)
    for p in pods:
        if p.get("status", {}).get("phase") != "Running":
            continue
        containers = p.get("status", {}).get("containerStatuses", [])
        if containers and all(c.get("ready", False) for c in containers):
            return True
    return False


def exec_in_pod(
    pod_label: str,
    namespace: str,
    command: list[str],
    timeout: int = 120,
) -> subprocess.CompletedProcess:
    # Find the pod name first
    pods = get_pods(pod_label, namespace)
    running = [
        p["metadata"]["name"]
        for p in pods
        if p.get("status", {}).get("phase") == "Running"
    ]
    if not running:
        raise RuntimeError(f"No running pod with label {pod_label} in {namespace}")
    pod_name = running[0]

    cmd = ["oc", "exec", pod_name, "-n", namespace, "--"] + command
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def get_route_host(name: str, namespace: str | None = None) -> str | None:
    data = get_json("route", name, namespace)
    if data is None:
        return None
    return data.get("spec", {}).get("host")


def get_argocd_app_health(name: str, namespace: str) -> str | None:
    data = get_json("application.argoproj.io", name, namespace)
    if data is None:
        return None
    return data.get("status", {}).get("health", {}).get("status")


def wait_for_argocd_apps(
    app_names: list[str], namespace: str, timeout: int = 300,
) -> bool:
    """Wait for ArgoCD applications to be Healthy."""
    import time

    deadline = time.time() + timeout
    while time.time() < deadline:
        all_healthy = True
        for name in app_names:
            health = get_argocd_app_health(name, namespace)
            if health != "Healthy":
                all_healthy = False
                break
        if all_healthy:
            return True
        time.sleep(10)
    return False
