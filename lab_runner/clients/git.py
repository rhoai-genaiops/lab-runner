"""Local git operations: clone to tmpdir, modify, commit, push."""

import os
import tempfile
from pathlib import Path

from git import Repo


class GitOps:
    """Manage a local clone of a Gitea repo for file modifications."""

    def __init__(self, repo_url: str, username: str, password: str, branch: str = "main"):
        self.repo_url = repo_url
        self.username = username
        self.password = password
        self.branch = branch
        self._tmpdir: tempfile.TemporaryDirectory | None = None
        self._repo: Repo | None = None

    @property
    def auth_url(self) -> str:
        """Insert credentials into the URL for push."""
        # https://gitea.example.com/user/repo.git → https://user:pass@gitea.example.com/user/repo.git
        prefix = "https://"
        rest = self.repo_url[len(prefix):]
        return f"{prefix}{self.username}:{self.password}@{rest}"

    @property
    def workdir(self) -> Path:
        if self._repo is None:
            raise RuntimeError("Repo not cloned yet. Call clone() first.")
        return Path(self._repo.working_dir)

    def clone(self) -> Path:
        """Clone the repo to a temporary directory."""
        self._tmpdir = tempfile.TemporaryDirectory(prefix="labrunner-")
        env = {"GIT_SSL_NO_VERIFY": "true"}
        self._repo = Repo.clone_from(
            self.auth_url,
            self._tmpdir.name,
            branch=self.branch,
            env=env,
        )
        # Configure git for commits
        self._repo.config_writer().set_value("user", "name", self.username).release()
        self._repo.config_writer().set_value("user", "email", f"{self.username}@lab-runner").release()
        self._repo.config_writer().set_value("http", "sslVerify", "false").release()
        return self.workdir

    def write_file(self, rel_path: str, content: str) -> Path:
        """Write or overwrite a file relative to the repo root."""
        full = self.workdir / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content)
        return full

    def read_file(self, rel_path: str) -> str | None:
        """Read a file from the working directory."""
        full = self.workdir / rel_path
        if full.exists():
            return full.read_text()
        return None

    def file_exists(self, rel_path: str) -> bool:
        return (self.workdir / rel_path).exists()

    def commit_and_push(self, message: str) -> str:
        """Stage all changes, commit, and push."""
        self._repo.git.add(A=True)
        # Check if there are changes to commit
        if not self._repo.is_dirty() and not self._repo.untracked_files:
            return "No changes to commit"
        self._repo.index.commit(message)
        origin = self._repo.remote("origin")
        env = {"GIT_SSL_NO_VERIFY": "true"}
        push_info = origin.push(env=env)
        return str(push_info)

    def cleanup(self) -> None:
        """Remove the temporary directory."""
        if self._tmpdir:
            self._tmpdir.cleanup()
            self._tmpdir = None
            self._repo = None
