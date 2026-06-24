"""Git steps: clone repos, modify files, push to Gitea, clone inside workbench."""

from lab_runner.clients.git import GitOps
from lab_runner.clients.gitea import GiteaClient
from lab_runner.clients import openshift as oc
from lab_runner.config import Config
from lab_runner.steps.base import Step, StepResult


class CloneAndModifyStep(Step):
    """Clone a Gitea repo, apply file modifications, commit, and push."""

    def __init__(
        self,
        repo_url: str,
        modifications: dict[str, str],
        commit_message: str,
        verify_repo: str | None = None,
        verify_file: str | None = None,
        verify_content: str | None = None,
        description: str | None = None,
    ):
        """
        Args:
            repo_url: Full HTTPS URL to the repo (.git)
            modifications: dict of {relative_path: file_content}
            commit_message: Git commit message
            verify_repo: repo name for verify check (e.g., "genaiops-gitops")
            verify_file: file path in repo to check existence
            verify_content: optional substring that must exist in the file
        """
        self.repo_url = repo_url
        self.modifications = modifications
        self.commit_message = commit_message
        self.verify_repo = verify_repo
        self.verify_file = verify_file
        self.verify_content = verify_content
        self.description = description or f"Update files in {_repo_name(repo_url)}"
        self.active_description = f"Updating {_repo_name(repo_url)}..."

    def verify(self, config: Config) -> bool:
        if not self.verify_repo or not self.verify_file:
            return False
        client = GiteaClient(config.gitea_url, config.username, config.password)
        content = client.get_file(config.username, self.verify_repo, self.verify_file)
        if content is None:
            return False
        if self.verify_content:
            return self.verify_content in content
        return True

    def run(self, config: Config) -> StepResult:
        git = GitOps(self.repo_url, config.username, config.password)
        try:
            git.clone()
            for path, content in self.modifications.items():
                git.write_file(path, content)
            result = git.commit_and_push(self.commit_message)
            return StepResult.success(output=result)
        except Exception as e:
            return StepResult.failed(str(e))
        finally:
            git.cleanup()


class MergeAndModifyStep(Step):
    """Clone a repo, read existing files, apply partial updates (merge), commit, push.

    Useful when you need to modify an existing file rather than overwrite it entirely.
    """

    def __init__(
        self,
        repo_url: str,
        file_path: str,
        updater: "callable",
        commit_message: str,
        verify_repo: str | None = None,
        verify_content: str | None = None,
        description: str | None = None,
    ):
        """
        Args:
            updater: callable(existing_content: str | None) -> str returning the new content
        """
        self.repo_url = repo_url
        self.file_path = file_path
        self.updater = updater
        self.commit_message = commit_message
        self.verify_repo = verify_repo
        self.verify_content = verify_content
        self.description = description or f"Update {file_path} in {_repo_name(repo_url)}"
        self.active_description = f"Updating {file_path}..."

    def verify(self, config: Config) -> bool:
        if not self.verify_repo or not self.verify_content:
            return False
        client = GiteaClient(config.gitea_url, config.username, config.password)
        content = client.get_file(config.username, self.verify_repo, self.file_path)
        if content is None:
            return False
        return self.verify_content in content

    def run(self, config: Config) -> StepResult:
        git = GitOps(self.repo_url, config.username, config.password)
        try:
            git.clone()
            existing = git.read_file(self.file_path)
            new_content = self.updater(existing)
            git.write_file(self.file_path, new_content)
            result = git.commit_and_push(self.commit_message)
            return StepResult.success(output=result)
        except Exception as e:
            return StepResult.failed(str(e))
        finally:
            git.cleanup()


class CloneInsideWorkbenchStep(Step):
    """Clone repos inside the workbench pod via oc exec."""

    def __init__(
        self,
        repos: list[tuple[str, str]],
        namespace: str,
        pod_label: str = "opendatahub.io/workbenches=true",
        description: str | None = None,
    ):
        """
        Args:
            repos: list of (clone_url, directory_name) tuples
        """
        self.repos = repos
        self.namespace = namespace
        self.pod_label = pod_label
        repo_names = ", ".join(name for _, name in repos)
        self.description = description or f"Clone repos inside workbench: {repo_names}"
        self.active_description = "Cloning repos in workbench..."

    def verify(self, config: Config) -> bool:
        try:
            for _, dir_name in self.repos:
                r = oc.exec_in_pod(
                    self.pod_label, self.namespace,
                    ["test", "-d", f"/opt/app-root/src/{dir_name}"],
                )
                if r.returncode != 0:
                    return False
            return True
        except Exception:
            return False

    def run(self, config: Config) -> StepResult:
        try:
            for clone_url, dir_name in self.repos:
                # Insert credentials
                auth_url = clone_url.replace("https://", f"https://{config.username}:{config.password}@")
                r = oc.exec_in_pod(
                    self.pod_label, self.namespace,
                    ["bash", "-c",
                     f"cd /opt/app-root/src && "
                     f"GIT_SSL_NO_VERIFY=true git clone {auth_url} {dir_name} 2>&1 || "
                     f"echo 'Already exists'"],
                )
                if r.returncode != 0 and "Already exists" not in r.stdout:
                    return StepResult.failed(f"Failed to clone {dir_name}: {r.stderr}")
            return StepResult.success()
        except Exception as e:
            return StepResult.failed(str(e))


class SetGitConfigInWorkbenchStep(Step):
    """Set git user config inside the workbench pod."""

    def __init__(self, namespace: str, pod_label: str = "opendatahub.io/workbenches=true"):
        self.namespace = namespace
        self.pod_label = pod_label
        self.description = "Set git config inside workbench"
        self.active_description = "Configuring git in workbench..."

    def verify(self, config: Config) -> bool:
        try:
            r = oc.exec_in_pod(
                self.pod_label, self.namespace,
                ["git", "config", "--global", "user.name"],
            )
            return r.returncode == 0 and r.stdout.strip() != ""
        except Exception:
            return False

    def run(self, config: Config) -> StepResult:
        try:
            oc.exec_in_pod(
                self.pod_label, self.namespace,
                ["git", "config", "--global", "user.name", config.username],
            )
            oc.exec_in_pod(
                self.pod_label, self.namespace,
                ["git", "config", "--global", "user.email", f"{config.username}@lab-runner"],
            )
            oc.exec_in_pod(
                self.pod_label, self.namespace,
                ["git", "config", "--global", "http.sslVerify", "false"],
            )
            return StepResult.success()
        except Exception as e:
            return StepResult.failed(str(e))


def _repo_name(url: str) -> str:
    """Extract repo name from URL."""
    return url.rstrip("/").rsplit("/", 1)[-1].replace(".git", "")
