"""Gitea REST API client."""

import requests
import urllib3

# Suppress insecure request warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class GiteaClient:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/api/v1"
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.verify = False
        self.session.headers["Content-Type"] = "application/json"

    def repo_exists(self, owner: str, repo: str) -> bool:
        r = self.session.get(f"{self.api_url}/repos/{owner}/{repo}")
        return r.status_code == 200

    def get_file(self, owner: str, repo: str, path: str, ref: str = "main") -> str | None:
        r = self.session.get(
            f"{self.api_url}/repos/{owner}/{repo}/raw/{path}",
            params={"ref": ref},
        )
        if r.status_code == 200:
            return r.text
        return None

    def file_exists(self, owner: str, repo: str, path: str, ref: str = "main") -> bool:
        return self.get_file(owner, repo, path, ref) is not None

    def list_webhooks(self, owner: str, repo: str) -> list[dict]:
        r = self.session.get(f"{self.api_url}/repos/{owner}/{repo}/hooks")
        r.raise_for_status()
        return r.json()

    def webhook_exists(self, owner: str, repo: str, target_url: str) -> bool:
        hooks = self.list_webhooks(owner, repo)
        return any(h.get("config", {}).get("url") == target_url for h in hooks)

    def create_webhook(
        self,
        owner: str,
        repo: str,
        target_url: str,
        content_type: str = "json",
        events: list[str] | None = None,
        active: bool = True,
    ) -> dict:
        payload = {
            "type": "gitea",
            "config": {
                "url": target_url,
                "content_type": content_type,
            },
            "events": events or ["push"],
            "active": active,
        }
        r = self.session.post(
            f"{self.api_url}/repos/{owner}/{repo}/hooks",
            json=payload,
        )
        r.raise_for_status()
        return r.json()
