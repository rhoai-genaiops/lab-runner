"""Seed an MLflow trace by calling the Canopy backend once."""

import json
import time

from lab_runner.clients import openshift as oc
from lab_runner.config import Config
from lab_runner.steps.base import Step, StepResult

# Short enough for a quick model response, long enough to look like the
# summarization the next lesson asks the student to open.
SMOKE_PROMPT = (
    "Canopy is the educational assistant for Redwood Digital University. "
    "Students use it to summarize readings and prepare for class."
)

_BACKEND_LABEL = "app.kubernetes.io/name=canopy-be"

# Runs inside the backend pod, which can reach MLflow and already has the client.
_TRACE_CHECK = """
import os
from pathlib import Path
os.environ.setdefault("MLFLOW_TRACKING_URI", "https://mlflow.redhat-ods-applications.svc.cluster.local:8443")
os.environ.setdefault("MLFLOW_TRACKING_INSECURE_TLS", "true")
os.environ.setdefault("MLFLOW_TRACKING_AUTH", "kubernetes")
token = Path("/var/run/secrets/kubernetes.io/serviceaccount/token")
if not token.exists():
    token = Path("/run/secrets/kubernetes.io/serviceaccount/token")
if token.exists():
    os.environ["MLFLOW_TRACKING_TOKEN"] = token.read_text()
ns = Path("/var/run/secrets/kubernetes.io/serviceaccount/namespace")
if not ns.exists():
    ns = Path("/run/secrets/kubernetes.io/serviceaccount/namespace")
if ns.exists() and not os.environ.get("MLFLOW_WORKSPACE"):
    os.environ["MLFLOW_WORKSPACE"] = ns.read_text().strip()
import mlflow
mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
client = mlflow.MlflowClient()
exp = client.get_experiment_by_name("summarization")
if exp is None:
    raise SystemExit("missing")
if hasattr(client, "search_traces"):
    traces = client.search_traces(experiment_ids=[exp.experiment_id], max_results=1)
else:
    traces = mlflow.search_traces(experiment_ids=[exp.experiment_id], max_results=1)
if traces is None or len(traces) == 0:
    raise SystemExit("empty")
print("ok")
"""


def _request_script(prompt: str) -> str:
    body = json.dumps({"prompt": prompt})
    return f"""
import urllib.request
req = urllib.request.Request(
    "http://127.0.0.1:8000/summarization",
    data={body!r}.encode(),
    headers={{"Content-Type": "application/json"}},
)
with urllib.request.urlopen(req, timeout=180) as resp:
    raw = resp.read().decode(errors="replace")
if '"delta"' not in raw:
    raise SystemExit(raw[:800])
print("ok")
"""


class SeedSummarizationTraceStep(Step):
    """POST one summarization so the canopy project has a summarization experiment."""

    def __init__(self, namespace: str, description: str | None = None):
        self.namespace = namespace
        self.description = description or f"Seed summarization trace in {namespace}"
        self.active_description = "Sending a summarization so MLflow records a trace..."

    def verify(self, config: Config) -> bool:
        try:
            result = oc.exec_in_pod(
                _BACKEND_LABEL,
                self.namespace,
                ["python3", "-c", _TRACE_CHECK],
                timeout=60,
            )
        except Exception:
            return False
        return result.returncode == 0

    def run(self, config: Config) -> StepResult:
        try:
            result = oc.exec_in_pod(
                _BACKEND_LABEL,
                self.namespace,
                ["python3", "-c", _request_script(SMOKE_PROMPT)],
                timeout=240,
            )
        except Exception as e:
            return StepResult.failed(str(e))

        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            return StepResult.failed(f"Summarization request failed: {detail}")

        deadline = time.time() + 60
        while time.time() < deadline:
            if self.verify(config):
                return StepResult.success(output="summarization experiment has a trace")
            time.sleep(3)
        return StepResult.failed(
            f"Summarization request finished but no trace appeared in {self.namespace}"
        )
