"""Helm CLI wrapper."""

import json
import subprocess
import tempfile as _tempfile
from pathlib import Path

import yaml
from git import Repo

_GITHUB_ORG = "https://github.com/rhoai-genaiops"
_repo_cache: dict[str, str] = {}


def _clone_repo(repo_name: str) -> str:
    """Clone a repo from the rhoai-genaiops org (cached per process)."""
    if repo_name in _repo_cache and Path(_repo_cache[repo_name]).exists():
        return _repo_cache[repo_name]
    tmpdir = _tempfile.mkdtemp(prefix=f"labrunner-{repo_name}-")
    url = f"{_GITHUB_ORG}/{repo_name}.git"
    Repo.clone_from(url, tmpdir, depth=1)
    _repo_cache[repo_name] = tmpdir
    return tmpdir


def resolve_chart(chart: str) -> str:
    """Resolve a chart path like 'frontend/chart' or 'charts/minio'.

    Chart paths use the convention '<repo-or-prefix>/<subdir>'.
    - 'charts/...' lives in the 'genaiops-helmcharts' repo.
    - Other prefixes (frontend, backend, mcp, ...) are standalone repos.
    """
    if Path(chart).is_absolute() or chart.startswith("oci://") or "/" not in chart:
        return chart

    parts = chart.split("/", 1)
    prefix, subdir = parts[0], parts[1]

    if prefix == "charts":
        repo_name = "genaiops-helmcharts"
        subdir = chart  # keep full path: charts/minio
    else:
        repo_name = prefix  # e.g. 'frontend', 'backend', 'mcp'

    repo_dir = _clone_repo(repo_name)
    local = Path(repo_dir) / subdir
    if local.is_dir():
        return str(local)
    return chart


def _run(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    r = subprocess.run(args, capture_output=True, text=True, check=False, timeout=300)
    if check and r.returncode != 0:
        detail = (r.stderr or r.stdout or "").strip()
        raise subprocess.CalledProcessError(
            r.returncode, args, output=r.stdout, stderr=detail,
        )
    return r


def release_exists(name: str, namespace: str) -> bool:
    r = _run(["helm", "list", "-n", namespace, "-o", "json"], check=False)
    if r.returncode != 0:
        return False
    releases = json.loads(r.stdout)
    return any(rel["name"] == name for rel in releases)


def install(
    name: str,
    chart: str,
    namespace: str,
    values: dict | None = None,
    values_files: list[str] | None = None,
    create_namespace: bool = False,
    wait: bool = False,
) -> str:
    chart = resolve_chart(chart)
    cmd = ["helm", "install", name, chart, "-n", namespace]
    if create_namespace:
        cmd.append("--create-namespace")
    if wait:
        cmd.append("--wait")
    if values:
        import tempfile, os
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        yaml.dump(values, f)
        f.close()
        cmd.extend(["-f", f.name])
    if values_files:
        for vf in values_files:
            cmd.extend(["-f", vf])

    r = _run(cmd)
    # Clean up temp file
    if values:
        os.unlink(f.name)
    return r.stdout


def upgrade(
    name: str,
    chart: str,
    namespace: str,
    values: dict | None = None,
    values_files: list[str] | None = None,
    install: bool = True,
    wait: bool = False,
) -> str:
    chart = resolve_chart(chart)
    cmd = ["helm", "upgrade", name, chart, "-n", namespace]
    if install:
        cmd.append("--install")
    if wait:
        cmd.append("--wait")
    if values:
        import tempfile, os
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        yaml.dump(values, f)
        f.close()
        cmd.extend(["-f", f.name])
    if values_files:
        for vf in values_files:
            cmd.extend(["-f", vf])

    r = _run(cmd)
    if values:
        os.unlink(f.name)
    return r.stdout


def get_values(name: str, namespace: str) -> dict:
    r = _run(["helm", "get", "values", name, "-n", namespace, "-o", "json"], check=False)
    if r.returncode != 0:
        return {}
    return json.loads(r.stdout)


def uninstall(name: str, namespace: str) -> str:
    r = _run(["helm", "uninstall", name, "-n", namespace], check=False)
    return r.stdout
