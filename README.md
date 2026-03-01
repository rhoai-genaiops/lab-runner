# Lab Runner - AI501 GenAIOps Enablement Fast Forward

Automated lab exercise runner for the AI501 GenAIOps Enablement workshop. Deploys and configures the full Canopy AI application stack on OpenShift, module by module.

## What It Does

Lab Runner automates the hands-on steps from each workshop module: Helm installs, GitOps config pushes, webhook creation, ArgoCD syncs, and verification checks. It resolves module dependencies and runs steps in order, skipping anything already completed.

## Modules

| ID | Name | Dependencies | Steps |
|----|------|-------------|-------|
| 2 | Linguistics | — | Canopy UI + route verification |
| 3 | Ready to Scale 101 | 2 | LlamaStack, Playground, Workbench, Backend, GitOps pipeline, ArgoCD ApplicationSets |
| 4 | Ready to Scale 201 | 3 | Evals, MinIO, DSPA, Tekton pipeline, webhooks |
| 5 | Grounded AI (RAG) | 4 | Milvus, RAG config, doc ingestion pipeline, MinIO webhook, PDF upload |
| 6 | Observability | 3 | Grafana dashboard via ArgoCD |
| 7 | Guardrails | 3 | Guardrails Orchestrator, safety shields |
| 8 | Agents | 5, 7 | MCP Calendar, student-assistant agent, evals |
| 9 | On-Prem Practicum | 8 | TinyLlama CPU inference, ServingRuntime |
| 10 | Model Optimization | 8 | FP8 quantized model integration |
| 12 | Fine-Tuning | 3 | Model Registry verification (notebook-driven) |

## Quick Start

### Prerequisites

- Python 3.11+
- `oc` CLI (logged in to the target OpenShift cluster)
- `helm` CLI
- `git` CLI

### Install

```bash
cd lab-runner
pip install -e .
```

### CLI Usage

```bash
# Run a single module
lab-runner run -u <username> -p <password> -d <cluster_domain> -m 2

# Run up to module 5 (resolves dependencies: 2 → 3 → 4 → 5)
lab-runner run -u <username> -p <password> -d <cluster_domain> --up-to 5

# Check status of all modules
lab-runner status -u <username> -p <password> -d <cluster_domain>

# List available modules
lab-runner list
```

### Web UI

```bash
lab-runner-web
# or
uvicorn lab_runner.web:app --port 8080
```

Open `http://localhost:8080` in your browser. Enter your credentials, select modules, and click **Run Selected**. Progress streams in real-time via SSE.

## Container Image

```bash
podman build -t lab-runner -f Containerfile .
podman run -p 8080:8080 lab-runner
```

## Helm Chart

Deploy on OpenShift alongside the workshop infrastructure:

```bash
helm install lab-runner chart/ -n <namespace>
```

The chart creates a Deployment, Service, Route, and ServiceAccount. Configure via `chart/values.yaml`.

## Architecture

```
lab_runner/
├── cli.py              # Click CLI entry point
├── web.py              # FastAPI app (SSE streaming)
├── runner.py           # Orchestrator: dependency resolution, step execution
├── config.py           # Config object (credentials, URLs, namespaces)
├── defaults.py         # Helm values, YAML templates, git file contents
├── templates/
│   └── index.html      # Single-page web UI
├── modules/            # One file per workshop module
│   ├── base.py         # Module ABC
│   ├── m02_linguistics.py
│   ├── m03_scale_101.py
│   └── ...
├── steps/              # Reusable step types
│   ├── base.py         # Step ABC + StepResult
│   ├── helm_step.py    # HelmInstallStep, HelmUpgradeStep
│   ├── kube_step.py    # ApplyManifest, WaitForReady, WaitForArgoCD, CreateNotebook
│   ├── git_step.py     # CloneAndModify, CloneInsideWorkbench
│   ├── webhook_step.py # Gitea webhooks, MinIO webhook
│   └── verify_step.py  # Route, pod, helm release, resource checks
└── clients/            # Low-level API wrappers
    ├── openshift.py    # oc CLI wrapper
    ├── helm.py         # helm CLI wrapper + chart resolver
    └── gitea.py        # Gitea REST API client
```

Each **module** declares an ID, name, dependencies, and a list of **steps**. The runner resolves dependencies via topological sort (lower IDs first), then executes steps sequentially — skipping any that `verify()` confirms are already done.

## License

Internal use for Red Hat AI501 GenAIOps Enablement workshops.
