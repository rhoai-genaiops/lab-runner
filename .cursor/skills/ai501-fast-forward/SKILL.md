---
name: ai501-fast-forward
description: >-
  Fast-forward an AI501 GenAIOps (rhoai-genaiops) lab environment to a lesson
  by calling the in-cluster lab-runner. Use when the user asks to run, replay,
  or fast-forward AI501 modules, lessons, or sections, or mentions lab-runner,
  Canopy, or a virgin/baseline GenAIOps cluster.
---

# AI501 lab fast-forward

Advance one student from a baseline `deploy-lab` cluster to the end of selected lab-runner modules. Run the runner that is already installed in the cluster. Do not clone this repo, do not `oc login` on the laptop, and do not install Helm locally.

## Defaults

- Student: `oc whoami`. Override only if the user names someone else (`user2`, …).
- Modules: the ids the user asked for. "Up to 5" means modules whose id is `<= 5`. "Start lesson 5" means run through 4 only.
- One student per run. The runner pod has a single kubeconfig; a second run replaces the login.

## Cluster facts that are not in the local kubeconfig

- `oc whoami` is a token. Lab-runner ignores it and runs `oc login` inside its pod.
- The password is the `password` key of secret `git-auth` in `{user}-canopy` (same value in `{user}-toolings`). Username is the `username` key. That value is this cluster's `common_password`.
- The example `thisisthepassword` in the public `deploy-lab` values file is not this cluster's password. Do not try it.
- Decode `git-auth` only inside the process that calls the API. Never print it, log it, or echo it. If a safety check blocks that read, ask for approval of the same command. Do not hunt other secrets.
- `{user}` cannot list ingresses, all namespaces, or routes in `gitea` / `redhat-ods-applications`. Visible projects are usually `ai501`, `{user}-canopy`, and `{user}-toolings`. `{user}-test` and `{user}-prod` appear during module 3.
- Apps domain is the suffix of a route host after the first dot. From `lab-runner-ai501.apps.ocp.example.opentlc.com` the domain is `apps.ocp.example.opentlc.com`. The runner strips the first label and calls `https://api.<rest>:6443`. A wrong domain logs in to the wrong API.
- `oc` from the default sandbox returns Forbidden. Run cluster commands with unrestricted network access.

## Modules

Registry on the live runner is `GET /api/modules`. Dependencies below are what the code runs. The table in the README can lag behind.

| ID | Depends on | Run leaves the cluster here |
|----|------------|-----------------------------|
| 2 | — | Canopy UI in `{user}-canopy`, MLflow prompt `summarization` |
| 3 | 2 | Workbench, backend, GitOps, test and prod Canopy, one summarization trace in `{user}-canopy` |
| 4 | 3 | MinIO, DSPA, eval and prompt-promotion pipelines |
| 5 | 4 | Milvus, Llama Stack, doc ingestion |
| 6 | 5 | Grafana, feedback on the test backend |
| 7 | 6 | NeMo Guardrails in test and prod |
| 8 | 7 | Calendar MCP and student-assistant |
| 9 | 8 | TinyLlama InferenceService |
| 10 | 8 | Test backend on the FP8 model |
| 11 | 10 | LiteMaaS in `{user}-maas`. Does not include 9 |
| 12 | 3 | Model-registry check only. Does not include 4–11 |

`modules: [11]` runs 2–8, 10, 11. `modules: [12]` runs 2, 3, 12. `up_to: 12` runs every id `<= 12`. Module 1 is not in the runner. Notebooks, extra credit, and the LiteMaaS admin lessons are not automated.

## Run

```bash
USER=$(oc whoami)
HOST=$(oc get route lab-runner -n ai501 -o jsonpath='{.spec.host}')
DOMAIN=${HOST#*.}

# Password stays in this process. Redact it if an error string contains `-p`.
python3 - << PY
import base64, json, subprocess, urllib.request
user = "$USER"
raw = subprocess.check_output(["oc","get","secret","git-auth","-n",f"{user}-canopy","-o","json"], text=True)
data = json.loads(raw)["data"]
password = base64.b64decode(data["password"]).decode().strip()
body = {
    "username": base64.b64decode(data["username"]).decode().strip(),
    "password": password,
    "cluster_domain": "$DOMAIN",
    "modules": [2, 3],  # or "up_to": N
}
req = urllib.request.Request(
    "https://$HOST/api/run",
    data=json.dumps(body).encode(),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=3600) as resp:
    for line in resp:
        print(line.decode(errors="replace").replace(password, "***"), end="")
PY
```

Set `modules` or `up_to` from the request. Stream until `{"type":"complete"}`. A module stops on the first failed step. Workbench and Argo CD waits are normal; modules 2 and 3 took about five minutes.

Confirm with the cluster, not only the stream:

```bash
helm list -n "$USER-canopy"
oc get pods,routes -n "$USER-canopy"
oc get applications.argoproj.io -n "$USER-toolings"
oc get pods -n "$USER-test"
oc get pods -n "$USER-prod"
```

Use `applications.argoproj.io`. `oc get applications` asks for the wrong API group and returns Forbidden.

## When the route is down

Only then use the CLI from this repo. The flag is `-c` / `--cluster-domain`, not `-d`. It needs Python 3.11, Helm 3, `oc`, and `git`. Helm 4 on the laptop breaks `helm list -o json`. MLflow's default URL is in-cluster (`mlflow.redhat-ods-applications.svc.cluster.local:8443`); outside the cluster set `MLFLOW_TRACKING_URI` and `MLFLOW_TRACKING_TOKEN=$(oc whoami -t)`.
