"""MLflow prompt registry and webhook steps."""

from lab_runner.config import Config
from lab_runner.steps.base import Step, StepResult


class CreateMLflowPromptStep(Step):
    """Register a prompt in MLflow and optionally set aliases."""

    def __init__(
        self,
        name: str,
        template: str,
        namespace: str,
        aliases: list[str] | None = None,
        commit_message: str = "",
        description: str | None = None,
    ):
        self.name = name
        self.template = template
        self.namespace = namespace
        self.aliases = aliases or []
        self.commit_message = commit_message
        self.description = description or f"Register MLflow prompt '{name}' in {namespace}"
        self.active_description = f"Registering prompt '{name}'..."

    def verify(self, config: Config) -> bool:
        from lab_runner.clients import mlflow as mlflow_client
        try:
            exists = mlflow_client.prompt_exists(self.name, self.namespace)
            if not exists:
                return False
            # If aliases are required, check they exist too (best-effort)
            if self.aliases:
                import mlflow as _mlflow
                mlflow_client._configure(self.namespace)
                for alias in self.aliases:
                    _mlflow.genai.load_prompt(f"prompts:/{self.name}@{alias}")
            return True
        except Exception:
            return False

    def run(self, config: Config) -> StepResult:
        from lab_runner.clients import mlflow as mlflow_client
        try:
            version = mlflow_client.register_prompt(
                name=self.name,
                template=self.template,
                namespace=self.namespace,
                commit_message=self.commit_message,
            )
            for alias in self.aliases:
                mlflow_client.set_alias(
                    name=self.name,
                    alias=alias,
                    version=version,
                    namespace=self.namespace,
                )
            aliases_str = f" (aliases: {', '.join(self.aliases)})" if self.aliases else ""
            return StepResult.success(output=f"Registered '{self.name}' v{version}{aliases_str}")
        except Exception as e:
            return StepResult.failed(str(e))


class CreateMLflowWebhookStep(Step):
    """Create an MLflow webhook to trigger a URL on specified events."""

    def __init__(
        self,
        webhook_name: str,
        url: str,
        events: list[str],
        namespace: str,
        webhook_description: str = "",
        description: str | None = None,
    ):
        self.webhook_name = webhook_name
        self.url = url
        self.events = events
        self.namespace = namespace
        self.webhook_description = webhook_description
        self.description = description or f"Create MLflow webhook '{webhook_name}'"
        self.active_description = f"Creating webhook '{webhook_name}'..."

    def verify(self, config: Config) -> bool:
        from lab_runner.clients import mlflow as mlflow_client
        try:
            return mlflow_client.webhook_exists(self.webhook_name, self.namespace)
        except Exception:
            return False

    def run(self, config: Config) -> StepResult:
        from lab_runner.clients import mlflow as mlflow_client
        try:
            webhook_id = mlflow_client.create_webhook(
                webhook_name=self.webhook_name,
                url=self.url,
                events=self.events,
                namespace=self.namespace,
                description=self.webhook_description,
            )
            return StepResult.success(output=f"Created webhook '{self.webhook_name}' (id: {webhook_id})")
        except Exception as e:
            return StepResult.failed(str(e))
