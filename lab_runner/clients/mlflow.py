"""MLflow client for prompt registry operations."""

import os

MLFLOW_TRACKING_URI = "https://mlflow.redhat-ods-applications.svc.cluster.local:8443"
SA_TOKEN_PATH = "/run/secrets/kubernetes.io/serviceaccount/token"
NAMESPACE_PATH = "/run/secrets/kubernetes.io/serviceaccount/namespace"


def _configure(namespace: str) -> None:
    os.environ["MLFLOW_TRACKING_AUTH"] = "kubernetes"
    os.environ["MLFLOW_TRACKING_INSECURE_TLS"] = "true"
    os.environ["MLFLOW_WORKSPACE"] = namespace

    if os.path.exists(SA_TOKEN_PATH):
        with open(SA_TOKEN_PATH) as f:
            os.environ["MLFLOW_TRACKING_TOKEN"] = f.read().strip()

    import mlflow
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)


def prompt_exists(name: str, namespace: str) -> bool:
    try:
        _configure(namespace)
        import mlflow
        mlflow.genai.load_prompt(f"prompts:/{name}@latest")
        return True
    except Exception:
        return False


def register_prompt(name: str, template: str, namespace: str, commit_message: str = "") -> int:
    """Create or update a prompt version. Returns the version number."""
    _configure(namespace)
    import mlflow
    result = mlflow.genai.register_prompt(
        name=name,
        template=template,
        commit_message=commit_message or f"Registered by lab-runner",
    )
    return result.version


def set_alias(name: str, alias: str, version: int, namespace: str) -> None:
    _configure(namespace)
    import mlflow
    mlflow.genai.set_prompt_alias(name=name, alias=alias, version=version)


def webhook_exists(webhook_name: str, namespace: str) -> bool:
    try:
        _configure(namespace)
        import mlflow
        client = mlflow.MlflowClient()
        webhooks = client.list_webhooks()
        return any(w.name == webhook_name for w in webhooks)
    except Exception:
        return False


def create_webhook(webhook_name: str, url: str, events: list[str], namespace: str, description: str = "") -> str:
    """Create an MLflow webhook. Returns the webhook_id."""
    _configure(namespace)
    import mlflow
    client = mlflow.MlflowClient()
    webhook = client.create_webhook(
        name=webhook_name,
        url=url,
        events=events,
        description=description,
    )
    return webhook.webhook_id
