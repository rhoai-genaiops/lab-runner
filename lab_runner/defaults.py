"""Default values, prompts, and file templates for lab modules."""

# ── Helm chart repo paths ──────────────────────────────────────────────

HELMCHARTS_REPO = "https://github.com/rhoai-genaiops/genaiops-helmcharts.git"

CHART_CANOPY_UI = "frontend/chart"
CHART_LLAMA_STACK = "charts/llama-stack-operator-instance"
CHART_LLAMA_STACK_PLAYGROUND = "charts/llama-stack-playground"
CHART_CANOPY_BACKEND = "backend/chart"
CHART_MINIO = "charts/minio"
CHART_DSPA = "charts/dspa"
CHART_GRAFANA = "charts/grafana"
CHART_GUARDRAILS = "charts/guardrails-orchestrator"
CHART_MCP_CALENDAR = "mcp/mcp-calendar-app/helm"
CHART_MILVUS = "charts/milvus"
CHART_BOOTSTRAP = "charts/bootstrap"
CHART_EVALS_PIPELINE = "charts/canopy-evals-pipeline"
CHART_DOC_INGESTION = "charts/canopy-doc-ingestion-pipeline"

# ── Module 2: Linguistics ──────────────────────────────────────────────

SYSTEM_PROMPT = "Summarize the following text clearly and concisely."
MODEL_NAME = "llama32"

CANOPY_UI_VALUES = {
    "SYSTEM_PROMPT": SYSTEM_PROMPT,
    "MODEL_NAME": MODEL_NAME,
    "LLM_ENDPOINT": "",  # set dynamically
    "BACKEND_ENDPOINT": "",
    "image": {"name": "canopy-ui", "tag": "simple-0.2"},
}

# ── Module 3: Scale 101 ───────────────────────────────────────────────

LLAMA_STACK_VALUES: dict = {}  # chart defaults are correct

LLAMA_STACK_PLAYGROUND_VALUES = {
    "replicaCount": 1,
    "image": {
        "repository": "quay.io/rhoai-genaiops/llama-stack-playground",
        "tag": "0.3.0-fix",
    },
    "route": {"enabled": True},
    "playground": {
        "llamaStackUrl": "http://llama-stack-service:8321",
        "defaultModel": "meta-llama/Llama-3.2-3B-Instruct",
    },
}

CANOPY_BACKEND_VALUES = {
    "LLAMA_STACK_URL": "http://llama-stack-service:8321",
    "summarize": {
        "enabled": True,
        "model": "vllm-llama32/llama32",
        "prompt": SYSTEM_PROMPT,
    },
}

CANOPY_UI_UPGRADE_VALUES_M03 = {
    "SYSTEM_PROMPT": SYSTEM_PROMPT,
    "MODEL_NAME": MODEL_NAME,
    "LLM_ENDPOINT": "",  # set dynamically
    "BACKEND_ENDPOINT": "http://canopy-backend:8000",
    "image": {"name": "canopy-ui", "tag": "0.5"},
}

MINIO_VALUES = {
    "buckets": [
        {"name": "pipeline"},
        {"name": "models"},
        {"name": "test-results"},
    ],
}


# ── Git file templates ─────────────────────────────────────────────────

def appset_toolings_yaml(username: str, cluster_domain: str) -> str:
    return f"""---
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: genaiops-toolings-project
spec:
  clusterResourceWhitelist:
  - group: '*'
    kind: '*'
  destinations:
  - namespace: '*'
    server: '*'
  sourceRepos:
  - '*'
---
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: genaiops-toolings-appset
spec:
  goTemplate: true
  generators:
  - git:
      repoURL: "https://gitea-gitea.{cluster_domain}/{username}/genaiops-gitops.git"
      revision: main
      files:
      - path: toolings/**/config.yaml
  template:
    metadata:
      name: "{{{{ .path.basename }}}}"
    spec:
      destination:
        server: https://kubernetes.default.svc
        namespace: {username}-toolings
      project: genaiops-toolings-project
      sources:
        - ref: app-values
          repoURL: "https://gitea-gitea.{cluster_domain}/{username}/genaiops-gitops.git"
          targetRevision: main
        - helm:
            valueFiles:
              - $app-values/toolings/{{{{ .path.basename }}}}/config.yaml
          path: '{{{{ .chart_path }}}}'
          repoURL: '{{{{ .repo_url | default "https://github.com/rhoai-genaiops/genaiops-helmcharts.git" }}}}'
          targetRevision: '{{{{ .target_revision | default "main" }}}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - Validate=true
"""


def appset_test_yaml(username: str, cluster_domain: str) -> str:
    return f"""---
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: canopy-test-project
spec:
  clusterResourceWhitelist:
  - group: '*'
    kind: '*'
  destinations:
  - namespace: '*'
    server: '*'
  sourceRepos:
  - '*'
---
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: canopy-test-appset
spec:
  goTemplate: true
  generators:
  - git:
      repoURL: "https://gitea-gitea.{cluster_domain}/{username}/genaiops-gitops.git"
      revision: main
      files:
      - path: canopy/test/**/config.yaml
  template:
    metadata:
      name: "{{{{ .path.basename }}}}-test"
    spec:
      destination:
        server: https://kubernetes.default.svc
        namespace: {username}-test
      project: canopy-test-project
      sources:
        - ref: app-values
          repoURL: "https://gitea-gitea.{cluster_domain}/{username}/genaiops-gitops.git"
          targetRevision: main
        - helm:
            valueFiles:
              - '{{{{ .values_file | default (printf "$app-values/canopy/test/%s/config.yaml" .path.basename) }}}}'
          path: '{{{{ .chart_path }}}}'
          repoURL: '{{{{ .repo_url | default "https://github.com/rhoai-genaiops/genaiops-helmcharts.git" }}}}'
          targetRevision: '{{{{ .target_revision | default "main" }}}}'
      syncPolicy:
        automated:
          prune: false
          selfHeal: true
        syncOptions:
          - Validate=true
"""


def appset_prod_yaml(username: str, cluster_domain: str) -> str:
    return f"""---
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: canopy-prod-project
spec:
  clusterResourceWhitelist:
  - group: '*'
    kind: '*'
  destinations:
  - namespace: '*'
    server: '*'
  sourceRepos:
  - '*'
---
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: canopy-prod-appset
spec:
  goTemplate: true
  generators:
  - git:
      repoURL: "https://gitea-gitea.{cluster_domain}/{username}/genaiops-gitops.git"
      revision: main
      files:
      - path: canopy/prod/**/config.yaml
  template:
    metadata:
      name: "{{{{ .path.basename }}}}-prod"
    spec:
      destination:
        server: https://kubernetes.default.svc
        namespace: {username}-prod
      project: canopy-prod-project
      sources:
        - ref: app-values
          repoURL: "https://gitea-gitea.{cluster_domain}/{username}/genaiops-gitops.git"
          targetRevision: main
        - helm:
            valueFiles:
              - '{{{{ .values_file | default (printf "$app-values/canopy/prod/%s/config.yaml" .path.basename) }}}}'
          path: '{{{{ .chart_path }}}}'
          repoURL: '{{{{ .repo_url | default "https://github.com/rhoai-genaiops/genaiops-helmcharts.git" }}}}'
          targetRevision: '{{{{ .target_revision | default "main" }}}}'
      syncPolicy:
        automated:
          prune: false
          selfHeal: true
        syncOptions:
          - Validate=true
"""


def bootstrap_config_yaml(username: str) -> str:
    return f"""chart_path: charts/bootstrap
bindings: &binds
  - name: {username}
    kind: User
    role: admin
namespaces:
  - name: {username}-test
    bindings: *binds
  - name: {username}-prod
    bindings: *binds
"""


def minio_toolings_config_yaml() -> str:
    return """---
chart_path: charts/minio
buckets:
  - name: pipeline
  - name: test-results
"""


def backend_values_test_yaml() -> str:
    return f"""\
LLAMA_STACK_URL: "http://llama-stack-service:8321"
summarize:
  enabled: true
  model: vllm-llama32/llama32
  temperature: 0.9
  max_tokens: 4096
  prompt: |
    {SYSTEM_PROMPT}
"""


def backend_values_prod_yaml() -> str:
    return f"""\
LLAMA_STACK_URL: "http://llama-stack-service:8321"
summarize:
  enabled: true
  model: vllm-llama32/llama32
  temperature: 0.9
  max_tokens: 4096
  prompt: |
    {SYSTEM_PROMPT}
"""


def gitops_test_frontend_config_yaml() -> str:
    return """\
repo_url: https://github.com/rhoai-genaiops/frontend.git
chart_path: chart
BACKEND_ENDPOINT: "http://canopy-backend:8000"
image:
  name: "canopy-ui"
  tag: "0.5"
"""


def gitops_prod_frontend_config_yaml() -> str:
    return """\
repo_url: https://github.com/rhoai-genaiops/frontend.git
chart_path: chart
BACKEND_ENDPOINT: "http://canopy-backend:8000"
image:
  name: "canopy-ui"
  tag: "0.5"
"""


def gitops_test_backend_config_yaml(username: str, cluster_domain: str) -> str:
    return f"""\
repo_url: https://gitea-gitea.{cluster_domain}/{username}/backend
chart_path: chart
values_file: values-test.yaml
"""


def gitops_prod_backend_config_yaml(username: str, cluster_domain: str) -> str:
    return f"""\
repo_url: https://gitea-gitea.{cluster_domain}/{username}/backend
chart_path: chart
values_file: values-prod.yaml
"""


def gitops_test_llama_stack_config_yaml() -> str:
    return """\
chart_path: charts/llama-stack-operator-instance
models:
  - name: "llama32"
    url: "http://llama-32-predictor.ai501.svc.cluster.local:8080/v1"
"""


def gitops_prod_llama_stack_config_yaml() -> str:
    return """\
chart_path: charts/llama-stack-operator-instance
models:
  - name: "llama32"
    url: "http://llama-32-predictor.ai501.svc.cluster.local:8080/v1"
"""


# ── Module 4: Scale 201 ───────────────────────────────────────────────

LLAMA_STACK_EVAL_VALUES = {
    **LLAMA_STACK_VALUES,
    "eval": {"enabled": True},
}

DSPA_VALUES: dict = {}

def dspa_toolings_config_yaml() -> str:
    return """---
chart_path: charts/dspa
"""


def evals_pipeline_config_yaml(username: str, cluster_domain: str) -> str:
    return f"""---
chart_path: charts/canopy-evals-pipeline
CLUSTER_DOMAIN: {cluster_domain}
USER_NAME: {username}
kfp:
  llsUrl: "http://llama-stack-service.{username}-test.svc.cluster.local:8321"
  backendUrl: "http://canopy-backend.{username}-test.svc.cluster.local:8000"
  endpointPath: "/summarize"
secrets:
  s3:
    name: "test-results"
testing:
  enableUnitTests: false
  llamaStackUrl: "http://llama-stack-service.{username}-test.svc.cluster.local:8321"
  vectorDbId: "latest"
  mcpCalendarUrl: "http://canopy-mcp-calendar-mcp-server.{username}-test.svc.cluster.local:8080/sse"
"""


def gitops_test_llama_stack_eval_config_yaml() -> str:
    return """---
chart_path: charts/llama-stack-operator-instance
eval:
  enabled: true
"""


# ── Module 5: RAG ─────────────────────────────────────────────────────

LLAMA_STACK_RAG_VALUES = {
    **LLAMA_STACK_VALUES,
    "eval": {"enabled": True},
    "rag": {"enabled": True, "milvus": {"service": "milvus-test"}},
}

def milvus_config_yaml(env: str) -> str:
    return f"""---
chart_path: charts/milvus
"""


def gitops_llama_stack_rag_config_yaml(env: str) -> str:
    service = f"milvus-{env}"
    return f"""---
chart_path: charts/llama-stack-operator-instance
rag:
  enabled: true
  milvus:
    service: "{service}"
eval:
  enabled: true
"""


def minio_documents_config_yaml() -> str:
    return """---
chart_path: charts/minio
buckets:
  - name: pipeline
  - name: test-results
  - name: documents
"""


def backend_values_test_rag_yaml() -> str:
    return f"""\
LLAMA_STACK_URL: "http://llama-stack-service:8321"
summarize:
  enabled: true
  model: vllm-llama32/llama32
  temperature: 0.9
  max_tokens: 4096
  prompt: |
    {SYSTEM_PROMPT}
information-search:
  enabled: true
  vector_db_id: latest
  model: vllm-llama32/llama32
  prompt: |
    You are a helpful assistant specializing in document intelligence and academic content analysis.
"""


def doc_ingestion_pipeline_config_yaml(username: str, cluster_domain: str) -> str:
    return f"""---
chart_path: charts/canopy-doc-ingestion-pipeline
username: {username}
cluster_domain: {cluster_domain}
"""


# Eval test files for information-search
def evals_information_search_test_yaml() -> str:
    return """---
description: "Information Search - RAG Evaluation"
providers:
  - id: "llama-stack"
    config:
      llamaStackUrl: "{{LLAMA_STACK_URL}}"
prompts:
  - "What is the main topic of the document?"
  - "Summarize the key points."
tests:
  - vars:
      question: "What is the main topic?"
    assert:
      - type: "contains"
        value: "topic"
"""


def evals_information_search_judge_prompt() -> str:
    return """You are evaluating the quality of a RAG-based information search response.
Score the response from 1 to 5 based on relevance and accuracy.

Question: {{question}}
Response: {{response}}

Score:"""


# ── Module 6: Observability ───────────────────────────────────────────

def grafana_config_yaml() -> str:
    return """---
chart_path: charts/grafana
operator: false
ignoreHelmHooks: true
"""


# ── Module 7: Guardrails ──────────────────────────────────────────────

GUARDRAILS_VALUES = {
    "orchestrator_gateway": {"enabled": True},
}

LLAMA_STACK_GUARDRAILS_VALUES = {
    **LLAMA_STACK_VALUES,
    "eval": {"enabled": True},
    "rag": {"enabled": True, "milvus": {"service": "milvus-test"}},
    "guardrails": {
        "enabled": True,
        "regex": {"enabled": True, "filter": ["(?i).*fight club.*"]},
        "hap": {"enabled": True},
        "prompt_injection": {"enabled": True},
        "language_detection": {"enabled": True},
    },
}

def guardrails_config_yaml() -> str:
    return """---
chart_path: charts/guardrails-orchestrator
orchestrator_gateway:
  enabled: true
"""


def gitops_llama_stack_guardrails_config_yaml(env: str) -> str:
    service = f"milvus-{env}"
    return f"""---
chart_path: charts/llama-stack-operator-instance
eval:
  enabled: true
guardrails:
  enabled: true
  regex:
    enabled: true
    filter:
      - "(?i).*fight club.*"
  hap:
    enabled: true
  prompt_injection:
    enabled: true
  language_detection:
    enabled: true
"""


def backend_values_test_shields_yaml() -> str:
    return f"""\
LLAMA_STACK_URL: "http://llama-stack-service:8321"
summarize:
  enabled: true
  model: vllm-llama32/llama32
  temperature: 0.9
  max_tokens: 4096
  prompt: |
    {SYSTEM_PROMPT}
information-search:
  enabled: true
  vector_db_id: latest
  model: vllm-llama32/llama32
  prompt: |
    You are a helpful assistant specializing in document intelligence and academic content analysis.
shields:
  enabled: true
  input_shields:
    - hap
    - language_detection
    - prompt_injection
  output_shields: []
"""


# ── Module 8: Agents ──────────────────────────────────────────────────

MCP_CALENDAR_VALUES = {
    "calendarApi": {"enabled": True},
    "calendarFrontend": {"enabled": True},
    "calendarMcpServer": {"enabled": True},
}

LLAMA_STACK_MCP_VALUES = {
    **LLAMA_STACK_VALUES,
    "eval": {"enabled": True},
    "rag": {"enabled": True, "milvus": {"service": "milvus-test"}},
    "guardrails": {
        "enabled": True,
        "regex": {"enabled": True, "filter": ["(?i).*fight club.*"]},
        "hap": {"enabled": True},
        "prompt_injection": {"enabled": True},
        "language_detection": {"enabled": True},
    },
    "mcp": {"enabled": True},
}


def gitops_test_llama_stack_mcp_config_yaml() -> str:
    return """---
chart_path: charts/llama-stack-operator-instance
models:
  - name: "llama32"
    url: "http://llama-32-predictor.ai501.svc.cluster.local:8080/v1"
eval:
  enabled: true
rag:
  enabled: true
  milvus:
    service: "milvus-test"
guardrails:
  enabled: true
  hap:
    enabled: true
  language_detection:
    enabled: true
  prompt_injection:
    enabled: true
  regex:
    enabled: true
    filter:
      - (?i).*fight club.*
mcp:
  enabled: true
"""


def calendar_mcp_config_yaml() -> str:
    return """---
repo_url: https://github.com/rhoai-genaiops/mcp.git
chart_path: mcp-calendar-app/helm
fullnameOverride: canopy-mcp-calendar
"""


def backend_values_test_agents_yaml() -> str:
    return f"""\
LLAMA_STACK_URL: "http://llama-stack-service:8321"
summarize:
  enabled: true
  model: vllm-llama32/llama32
  temperature: 0.9
  max_tokens: 4096
  prompt: |
    {SYSTEM_PROMPT}
information-search:
  enabled: true
  vector_db_id: latest
  model: vllm-llama32/llama32
  prompt: |-
    You are a helpful assistant specializing in document intelligence and academic content analysis.
shields:
  enabled: true
  input_shields:
    - hap
    - language_detection
    - prompt_injection
  output_shields: []
student-assistant:
  enabled: true
  model: vllm-llama32/llama32
  temperature: 0.1
  vector_db_id: latest
  mcp_calendar_url: "http://canopy-mcp-calendar-mcp-server:8080/sse"
  prompt: |
    You are a helpful assistant that helps students with their calendar and studies.

    Your workflow:

    1. If student asks about their schedule ("What lectures do I have?"):
      - Call get_upcoming_events
      - Show them the results
      - DONE (don't modify anything)

    2. If student asks a question about a topic ("I need help understanding X"):
      - First: call search_knowledge_base with the topic
      - If knowledge base has relevant information: answer their question with that information, DONE
      - If knowledge base has NO relevant information:
        a) Call find_professors_by_expertise to find an expert
        b) Call get_events_by_date to check for scheduling conflicts
        c) Call create_event to schedule a meeting with the professor at a free time
        d) Tell the student you scheduled the meeting

    When scheduling with create_event:
    - Pick a reasonable time that's free (check with get_events_by_date first)
    - Use these parameters: name, category, level, start_time, end_time, content
    - Do NOT include sid, status, or creation_time
"""


def evals_student_assistant_test_yaml() -> str:
    return """---
description: "Student Assistant - Agent Evaluation"
providers:
  - id: "llama-stack"
    config:
      llamaStackUrl: "{{LLAMA_STACK_URL}}"
prompts:
  - "What events do I have today?"
  - "Schedule a meeting for tomorrow at 2pm."
tests:
  - vars:
      question: "What events do I have today?"
    assert:
      - type: "contains"
        value: "calendar"
"""


def evals_pipeline_unit_tests_config_yaml(username: str, cluster_domain: str) -> str:
    return f"""---
chart_path: charts/canopy-evals-pipeline
CLUSTER_DOMAIN: {cluster_domain}
USER_NAME: {username}
kfp:
  llsUrl: "http://llama-stack-service.{username}-test.svc.cluster.local:8321"
  backendUrl: "http://canopy-backend.{username}-test.svc.cluster.local:8000"
  endpointPath: "/summarize"
secrets:
  s3:
    name: "test-results"
testing:
  enableUnitTests: true
  llamaStackUrl: "http://llama-stack-service.{username}-test.svc.cluster.local:8321"
  vectorDbId: "latest"
  mcpCalendarUrl: "http://canopy-mcp-calendar-mcp-server.{username}-test.svc.cluster.local:8080/sse"
"""


# ── Module 9: On-Prem ─────────────────────────────────────────────────

def tinyllama_manifests(namespace: str) -> str:
    return f"""---
kind: Secret
apiVersion: v1
metadata:
  annotations:
    opendatahub.io/connection-type-protocol: uri
    opendatahub.io/connection-type-ref: uri-v1
    openshift.io/display-name: secret-tinyllama
  name: secret-tinyllama
  namespace: {namespace}
  labels:
    opendatahub.io/dashboard: 'false'
data:
  URI: b2NpOi8vcXVheS5pby9yaC1haXNlcnZpY2VzLWJ1L3RpbnlsbGFtYToxLjA=
type: Opaque
---
apiVersion: serving.kserve.io/v1alpha1
kind: ServingRuntime
metadata:
  annotations:
    opendatahub.io/accelerator-name: ''
    opendatahub.io/apiProtocol: REST
    opendatahub.io/recommended-accelerators: ''
    opendatahub.io/serving-runtime-scope: global
    opendatahub.io/template-display-name: CUSTOM - vLLM Serving Runtime for CPU
    opendatahub.io/template-name: vllm-cpu-template
    openshift.io/display-name: CUSTOM - vLLM Serving Runtime for CPU
  name: tinyllama
  namespace: {namespace}
  labels:
    opendatahub.io/dashboard: 'true'
spec:
  builtInAdapter:
    modelLoadingTimeoutMillis: 90000
  containers:
    - args:
        - '--model'
        - /mnt/models
        - '--port'
        - '8080'
        - '--max-model-len'
        - '2048'
        - '--served-model-name'
        - tinyllama
      image: 'quay.io/rh-aiservices-bu/vllm-cpu-openai-ubi9:0.3'
      name: kserve-container
      ports:
        - containerPort: 8080
          name: http1
          protocol: TCP
  multiModel: false
  supportedModelFormats:
    - autoSelect: true
      name: vLLM
---
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  annotations:
    security.opendatahub.io/enable-auth: 'false'
    openshift.io/description: ''
    openshift.io/display-name: tinyllama
    serving.kserve.io/deploymentMode: RawDeployment
    opendatahub.io/hardware-profile-namespace: redhat-ods-applications
    opendatahub.io/hardware-profile-name: default-profile
    opendatahub.io/connections: secret-tinyllama
    opendatahub.io/model-type: generative
  name: tinyllama
  namespace: {namespace}
  labels:
    opendatahub.io/dashboard: 'true'
spec:
  predictor:
    automountServiceAccountToken: false
    deploymentStrategy:
      type: RollingUpdate
    maxReplicas: 1
    minReplicas: 1
    model:
      modelFormat:
        name: vLLM
      name: ''
      resources:
        limits:
          cpu: '4'
          memory: 8Gi
        requests:
          cpu: '3'
          memory: 6Gi
      runtime: tinyllama
      storageUri: 'oci://quay.io/rh-aiservices-bu/tinyllama:1.0'
"""

def llama_stack_onprem_values(namespace: str) -> dict:
    return {
        **LLAMA_STACK_VALUES,
        "eval": {"enabled": True},
        "rag": {"enabled": True, "milvus": {"service": "milvus-test"}},
        "guardrails": {
            "enabled": True,
            "regex": {"enabled": True, "filter": ["(?i).*fight club.*"]},
            "hap": {"enabled": True},
            "prompt_injection": {"enabled": True},
            "language_detection": {"enabled": True},
        },
        "mcp": {"enabled": True},
        "models": [
            {"name": "llama32", "url": "http://llama-32-predictor.ai501.svc.cluster.local:8080/v1"},
            {"name": "tinyllama", "url": f"http://tinyllama-predictor.{namespace}.svc.cluster.local:8080/v1"},
        ],
    }


# ── Module 10: Optimization ───────────────────────────────────────────

LLAMA_STACK_FP8_VALUES = {
    **LLAMA_STACK_VALUES,
    "eval": {"enabled": True},
    "rag": {"enabled": True, "milvus": {"service": "milvus-test"}},
    "guardrails": {
        "enabled": True,
        "regex": {"enabled": True, "filter": ["(?i).*fight club.*"]},
        "hap": {"enabled": True},
        "prompt_injection": {"enabled": True},
        "language_detection": {"enabled": True},
    },
    "mcp": {"enabled": True},
    "models": [
        {"name": "llama32", "url": "http://llama-32-predictor.ai501.svc.cluster.local:8080/v1"},
        {"name": "llama32-fp8", "url": "http://llama-32-fp8-predictor.ai501.svc.cluster.local:8080/v1"},
    ],
}


def gitops_test_llama_stack_fp8_config_yaml() -> str:
    return """---
chart_path: charts/llama-stack-operator-instance
models:
  - name: "llama32"
    url: "http://llama-32-predictor.ai501.svc.cluster.local:8080/v1"
  - name: "llama32-fp8"
    url: "http://llama-32-fp8-predictor.ai501.svc.cluster.local:8080/v1"
eval:
  enabled: true
rag:
  enabled: true
mcp:
  enabled: true
"""


def backend_values_test_fp8_yaml() -> str:
    return f"""\
LLAMA_STACK_URL: "http://llama-stack-service:8321"
summarize:
  enabled: true
  model: vllm-llama32-fp8/llama32-fp8
  temperature: 0.9
  max_tokens: 4096
  prompt: |
    {SYSTEM_PROMPT}
information-search:
  enabled: true
  vector_db_id: latest
  model: vllm-llama32-fp8/llama32-fp8
  prompt: |
    You are a helpful assistant specializing in document intelligence and academic content analysis.
shields:
  enabled: true
  input_shields:
    - hap
    - language_detection
    - prompt_injection
  output_shields: []
student-assistant:
  enabled: true
  model: vllm-llama32-fp8/llama32-fp8
  temperature: 0.1
  vector_db_id: latest
  mcp_calendar_url: "http://canopy-mcp-calendar-mcp-server:8080/sse"
  prompt: |
    You are a helpful assistant that helps students with their calendar and studies.
"""
