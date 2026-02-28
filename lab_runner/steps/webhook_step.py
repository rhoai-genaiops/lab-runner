"""Gitea and MinIO webhook creation steps."""

import time

import requests as req
import urllib3

from lab_runner.clients.gitea import GiteaClient
from lab_runner.config import Config
from lab_runner.steps.base import Step, StepResult

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CreateGiteaWebhookStep(Step):
    """Create a webhook on a Gitea repository."""

    def __init__(
        self,
        repo_name: str,
        target_url: str,
        events: list[str] | None = None,
        description: str | None = None,
    ):
        self.repo_name = repo_name
        self.target_url = target_url
        self.events = events or ["push"]
        self.description = description or f"Create webhook on '{repo_name}'"
        self.active_description = f"Creating webhook on {repo_name}..."

    def verify(self, config: Config) -> bool:
        client = GiteaClient(config.gitea_url, config.username, config.password)
        return client.webhook_exists(config.username, self.repo_name, self.target_url)

    def run(self, config: Config) -> StepResult:
        client = GiteaClient(config.gitea_url, config.username, config.password)
        try:
            if client.webhook_exists(config.username, self.repo_name, self.target_url):
                return StepResult.skipped("Webhook already exists")
            result = client.create_webhook(
                config.username,
                self.repo_name,
                self.target_url,
                events=self.events,
            )
            return StepResult.success(output=str(result))
        except Exception as e:
            return StepResult.failed(str(e))


class ConfigureMinIOWebhookStep(Step):
    """Configure a MinIO webhook notification for bucket events via the Console API.

    Steps performed:
      1. Login to MinIO Console
      2. Add a webhook event destination (notify_webhook:<webhook_id>)
      3. Restart MinIO so the new config takes effect
      4. Subscribe the bucket to PUT events on the webhook ARN
    """

    MINIO_PASSWORD = "thisisthepassword"

    def __init__(
        self,
        bucket: str,
        webhook_id: str,
        endpoint_url: str,
        events: list[str] | None = None,
        description: str | None = None,
    ):
        self.bucket = bucket
        self.webhook_id = webhook_id
        self.endpoint_url = endpoint_url
        self.events = events or ["put"]
        self.description = description or (
            f"Configure MinIO webhook '{webhook_id}' on '{bucket}'"
        )
        self.active_description = f"Configuring MinIO webhook {webhook_id}..."

    def _console_url(self, config: Config) -> str:
        return f"https://minio-ui-{config.toolings_namespace}.{config.cluster_domain}"

    def _login(self, console_url: str, username: str) -> req.Session | None:
        session = req.Session()
        resp = session.post(
            f"{console_url}/api/v1/login",
            json={"accessKey": username, "secretKey": self.MINIO_PASSWORD},
            verify=False,
        )
        if resp.status_code not in (200, 204):
            return None
        return session

    def verify(self, config: Config) -> bool:
        return False  # Always run — cheap and idempotent

    def run(self, config: Config) -> StepResult:
        console = self._console_url(config)

        # 1. Login
        session = self._login(console, config.username)
        if not session:
            return StepResult.failed("MinIO Console login failed")

        # 2. Add webhook event destination
        resp = session.put(
            f"{console}/api/v1/configs/notify_webhook:{self.webhook_id}",
            json={
                "key_values": [
                    {"key": "endpoint", "value": self.endpoint_url},
                    {"key": "enable", "value": "on"},
                ]
            },
            verify=False,
        )
        if resp.status_code not in (200, 204):
            return StepResult.failed(
                f"Add webhook endpoint failed: {resp.status_code} {resp.text}"
            )

        # 3. Restart MinIO to apply config
        session.post(f"{console}/api/v1/service/restart", verify=False)
        time.sleep(15)

        # 4. Re-login after restart (retry a few times while MinIO restarts)
        session = None
        for _ in range(6):
            session = self._login(console, config.username)
            if session:
                break
            time.sleep(5)
        if not session:
            return StepResult.failed("MinIO Console login failed after restart")

        # 5. Subscribe bucket to events
        resp = session.post(
            f"{console}/api/v1/buckets/{self.bucket}/events",
            json={
                "configuration": {
                    "arn": f"arn:minio:sqs::{self.webhook_id}:webhook",
                    "events": self.events,
                    "prefix": "",
                    "suffix": "",
                },
                "ignoreExisting": True,
            },
            verify=False,
        )
        if resp.status_code not in (200, 201, 204):
            return StepResult.failed(
                f"Subscribe bucket events failed: {resp.status_code} {resp.text}"
            )

        return StepResult.success()
