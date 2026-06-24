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
MLFLOW_PROMPT_NAME = "summarization"
INFORMATION_SEARCH_PROMPT = "You are a helpful assistant specializing in document intelligence and academic content analysis."
INFORMATION_SEARCH_PROMPT_NAME = "information-search"
MODEL_NAME = "llama32"

CANOPY_UI_VALUES = {
    "MLFLOW_PROMPT_NAME": MLFLOW_PROMPT_NAME,
    "MODEL_NAME": MODEL_NAME,
    "LLM_ENDPOINT": "",  # set dynamically
    "image": {"name": "canopy-ui", "tag": "simple-0.5"},
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
    "summarization": {
        "enabled": True,
        "model": "llama32",
        "endpoint": "http://llama-32-predictor.ai501.svc.cluster.local:8080/v1",
        "mlflow_prompt": MLFLOW_PROMPT_NAME,
        "mlflow_prompt_version": "latest",
    },
}

CANOPY_UI_UPGRADE_VALUES_M03 = {
    "MLFLOW_PROMPT_NAME": MLFLOW_PROMPT_NAME,
    "MODEL_NAME": MODEL_NAME,
    "LLM_ENDPOINT": "",  # set dynamically
    "BACKEND_ENDPOINT": "http://canopy-backend:8000",
    "image": {"name": "canopy-ui", "tag": "0.10"},
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
summarization:
  enabled: true
  model: llama32
  endpoint: "http://llama-32-predictor.ai501.svc.cluster.local:8080/v1"
  mlflow_prompt: {MLFLOW_PROMPT_NAME}
  mlflow_prompt_version: latest
"""


def backend_values_prod_yaml() -> str:
    return f"""\
summarization:
  enabled: true
  model: llama32
  endpoint: "http://llama-32-predictor.ai501.svc.cluster.local:8080/v1"
  mlflow_prompt: {MLFLOW_PROMPT_NAME}
  mlflow_prompt_version: prod
"""


def gitops_test_frontend_config_yaml() -> str:
    return """\
repo_url: https://github.com/rhoai-genaiops/frontend.git
chart_path: chart
BACKEND_ENDPOINT: "http://canopy-backend:8000"
image:
  name: "canopy-ui"
  tag: "0.10"
"""


def gitops_prod_frontend_config_yaml() -> str:
    return """\
repo_url: https://github.com/rhoai-genaiops/frontend.git
chart_path: chart
BACKEND_ENDPOINT: "http://canopy-backend:8000"
image:
  name: "canopy-ui"
  tag: "0.10"
"""


def gitops_test_backend_config_yaml(username: str, cluster_domain: str) -> str:
    return f"""\
repo_url: https://gitea-gitea.{cluster_domain}/{username}/backend
chart_path: chart
summarization:
  enabled: true
  model: llama32
  endpoint: "http://llama-32-predictor.ai501.svc.cluster.local:8080/v1"
  mlflow_prompt: {MLFLOW_PROMPT_NAME}
  mlflow_prompt_version: latest
"""


def gitops_prod_backend_config_yaml(username: str, cluster_domain: str) -> str:
    return f"""\
repo_url: https://gitea-gitea.{cluster_domain}/{username}/backend
chart_path: chart
summarization:
  enabled: true
  model: llama32
  endpoint: "http://llama-32-predictor.ai501.svc.cluster.local:8080/v1"
  mlflow_prompt: {MLFLOW_PROMPT_NAME}
  mlflow_prompt_version: prod
"""


def gitops_test_backend_rag_config_yaml(username: str, cluster_domain: str) -> str:
    """Backend config for test env with RAG (information-search) enabled."""
    return f"""\
repo_url: https://gitea-gitea.{cluster_domain}/{username}/backend
chart_path: chart
summarization:
  enabled: true
  model: llama32
  endpoint: "http://llama-32-predictor.ai501.svc.cluster.local:8080/v1"
  mlflow_prompt: {MLFLOW_PROMPT_NAME}
  mlflow_prompt_version: latest
information-search:
  enabled: true
  endpoint: "http://llama-stack-service:8321/v1"
  model: vllm-llama32/llama32
  vector_db_id: latest
  mlflow_prompt: information-search
  mlflow_prompt_version: latest
"""


def gitops_test_backend_feedback_config_yaml(username: str, cluster_domain: str) -> str:
    """Backend config for test env with feedback collection enabled."""
    return f"""\
repo_url: https://gitea-gitea.{cluster_domain}/{username}/backend
chart_path: chart
summarization:
  enabled: true
  model: llama32
  endpoint: "http://llama-32-predictor.ai501.svc.cluster.local:8080/v1"
  mlflow_prompt: {MLFLOW_PROMPT_NAME}
  mlflow_prompt_version: latest
information-search:
  enabled: true
  endpoint: "http://llama-stack-service:8321/v1"
  model: vllm-llama32/llama32
  vector_db_id: latest
  mlflow_prompt: information-search
  mlflow_prompt_version: latest
feedback:
  enabled: true
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
USER_NAME: {username}
CLUSTER_DOMAIN: {cluster_domain}
kfp:
  backendUrl: "http://canopy-backend.{username}-test.svc.cluster.local:8000"
  llmEndpoint: "http://llama-32-predictor.ai501.svc.cluster.local:8080"
"""


def prompt_promotion_pipeline_config_yaml(username: str, cluster_domain: str) -> str:
    return f"""---
chart_path: charts/prompt-promotion-pipeline
USER_NAME: {username}
CLUSTER_DOMAIN: {cluster_domain}
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


def gitops_ogx_config_yaml(env: str) -> str:
    service = f"milvus-{env}"
    return f"""---
chart_path: charts/llama-stack-operator-instance
models:
  - name: "llama32"
    url: "http://llama-32-predictor.ai501.svc.cluster.local:8080/v1"
rag:
  enabled: true
  milvus:
    service: "{service}"
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
    return """\
name: information_search_tests
description: Tests for the information-search prompts of the Llama 3.2 3B model.
usecase: information-search
endpoint: /information-search
scorers:
  - answer_quality
  - retrieval_relevance
  - retrieval_groundedness
judge_prompt: judge_prompt.txt
tests:
  - inputs:
      prompt: "Describe the main learning outcomes for students completing the Advanced Generative AI Systems course."
    expectations:
      expected_result: "Students will learn to design GenAI applications, engineer prompts with evaluation, build production systems with CI/CD, implement RAG pipelines, secure LLM apps with guardrails, integrate multi-modal models, optimize models via quantization, instrument monitoring systems, orchestrate agents with tool-calling, and operate MaaS with APIs and governance."
  - inputs:
      prompt: "What are the key modules covered in weeks 5-8 of the AI501 curriculum?"
    expectations:
      expected_result: "Week 5 covers RAG Foundations (embeddings, chunking, ingestion pipelines), Week 6 covers Guardrails (safety taxonomies, filters, jailbreak defense), Week 7 covers Observability (tracing, metrics, logs, SLI/SLO), and Week 8 covers Tool-Calling & Agents (function calling, MCP, planner/critic loops)."
  - inputs:
      prompt: "What assessment components make up the AI501 course evaluation and what are their weightings?"
    expectations:
      expected_result: "Assessment includes Prompting & Eval Harness (10%), RAG Mini-System (15%), Guardrails & Red-Team (10%), Observability Pack (10%), Optimization Lab (10%), Agent with Tools (10%), Capstone (30%), and Participation (5%)."
  - inputs:
      prompt: "Explain what RAG implementation involves according to the course syllabus."
    expectations:
      expected_result: "RAG implementation involves building pipelines for ingestion, indexing, and retrieval with citations and provenance. Students learn embeddings, chunking strategies, ingestion pipelines, and create ETL→vector DB→retrieval→generation systems with citations."
  - inputs:
      prompt: "What technologies and platforms are used in the AI501 course infrastructure?"
    expectations:
      expected_result: "The course uses AI/ML platforms like Llama Stack and Hugging Face; development tools including Python, PyTorch, LangChain, Docker, and Kubernetes; infrastructure with GPU clusters and vector databases like Pinecone and Weaviate; plus security and monitoring tools for guardrails and observability."
  - inputs:
      prompt: "What are the four practical implementation tracks available in AI501?"
    expectations:
      expected_result: "The four tracks are: Production AI Systems (Llama Stack, GitOps, CI/CD), Knowledge Grounding (RAG design, vector DBs, doc pipelines), AI Safety & Security (Guardrails, red-teaming, observability), and Advanced Applications (Agents/tool-calling, multi-modal, model optimization)."
"""


def evals_information_search_judge_prompt() -> str:
    return """\
You are an expert evaluator judging the quality of a generated answer to a question.

Your task is to decide whether the GENERATED_ANSWER correctly and faithfully answers the QUESTION, compared against the EXPECTED_ANSWER.

A high-quality answer must satisfy ALL of the following criteria:
- It correctly addresses the QUESTION
- Its key facts and claims are consistent with the EXPECTED_ANSWER
- It does not contradict or misrepresent information present in the EXPECTED_ANSWER
- It is coherent and directly useful as a standalone answer

INPUT:
{{ inputs }}

GENERATED_ANSWER:
{{ outputs }}

EXPECTED_ANSWER:
{{ expectations }}

Answer "yes" if the GENERATED_ANSWER meets all of the criteria above.
Answer "no" if it gives incorrect information, contradicts the expected answer, or fails to address the question.

Respond with only "yes" or "no"."""


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

def nemo_guardrails_config_yaml() -> str:
    return """---
chart_path: charts/nemo-guardrails-orchestrator
"""


def gitops_ogx_guardrails_config_yaml(env: str) -> str:
    service = f"milvus-{env}"
    return f"""---
chart_path: charts/llama-stack-operator-instance
models:
  - name: "llama32"
    url: "http://llama-32-predictor.ai501.svc.cluster.local:8080/v1"
rag:
  enabled: true
  milvus:
    service: "{service}"
guardrails:
  enabled: true
"""


def gitops_test_backend_guardrails_config_yaml(username: str, cluster_domain: str) -> str:
    """Backend config for test env with NeMo guardrails (shields) enabled."""
    return f"""\
repo_url: https://gitea-gitea.{cluster_domain}/{username}/backend
chart_path: chart
summarization:
  enabled: true
  endpoint: "http://llama-stack-service:8321/v1"
  mlflow_prompt: {MLFLOW_PROMPT_NAME}
  mlflow_prompt_version: latest
  model: vllm-llama32/llama32
information-search:
  enabled: true
  endpoint: "http://llama-stack-service:8321/v1"
  model: vllm-llama32/llama32
  vector_db_id: latest
  mlflow_prompt: information-search
  mlflow_prompt_version: latest
feedback:
  enabled: true
shields:
  enabled: true
  endpoint: http://canopy-guardrails/v1
  model: llama32
  config: canopy-guardrails
"""


# ── Module 8: Agents ──────────────────────────────────────────────────

STUDENT_ASSISTANT_PROMPT = """\
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


def gitops_ogx_mcp_config_yaml(env: str) -> str:
    service = f"milvus-{env}"
    return f"""---
chart_path: charts/llama-stack-operator-instance
models:
  - name: "llama32"
    url: "http://llama-32-predictor.ai501.svc.cluster.local:8080/v1"
rag:
  enabled: true
  milvus:
    service: "{service}"
guardrails:
  enabled: true
mcp:
  enabled: true
"""


def calendar_mcp_config_yaml() -> str:
    return """---
repo_url: https://github.com/rhoai-genaiops/mcp.git
chart_path: mcp-calendar-app/helm
fullnameOverride: canopy-mcp-calendar
"""


def gitops_test_backend_agents_config_yaml(username: str, cluster_domain: str) -> str:
    """Backend config for test env with student-assistant (agents) enabled."""
    return f"""\
repo_url: https://gitea-gitea.{cluster_domain}/{username}/backend
chart_path: chart
summarization:
  enabled: true
  endpoint: "http://llama-stack-service:8321/v1"
  mlflow_prompt: {MLFLOW_PROMPT_NAME}
  mlflow_prompt_version: latest
  model: vllm-llama32/llama32
information-search:
  enabled: true
  endpoint: "http://llama-stack-service:8321/v1"
  model: vllm-llama32/llama32
  vector_db_id: latest
  mlflow_prompt: information-search
  mlflow_prompt_version: latest
feedback:
  enabled: true
shields:
  enabled: true
  endpoint: http://canopy-guardrails/v1
  model: llama32
  config: canopy-guardrails
student-assistant:
  enabled: true
  model: vllm-llama32/llama32
  temperature: 0.1
  vector_db_id: latest
  mcp_calendar_url: "http://canopy-mcp-calendar-mcp-server:8080/sse"
  mlflow_prompt: student-assistant
  mlflow_prompt_version: latest
"""


def evals_student_assistant_judge_prompt() -> str:
    return """\
You are an expert evaluator judging the quality of a generated answer to a question.

Your task is to decide whether the GENERATED_ANSWER correctly and faithfully answers the QUESTION, compared against the EXPECTED_ANSWER.

A high-quality answer must satisfy ALL of the following criteria:
- It correctly addresses the QUESTION
- Its key facts and claims are consistent with the EXPECTED_ANSWER
- It does not contradict or misrepresent information present in the EXPECTED_ANSWER
- It is coherent and directly useful as a standalone answer

INPUT:
{{ inputs }}

GENERATED_ANSWER:
{{ outputs }}

EXPECTED_ANSWER:
{{ expectations }}

Answer "yes" if the GENERATED_ANSWER meets all of the criteria above.
Answer "no" if it gives incorrect information, contradicts the expected answer, or fails to address the question.

Respond with only "yes" or "no"."""


def evals_student_assistant_test_yaml() -> str:
    return """\
name: student_assistant_tests
description: End-to-end tests for the student assistant agent with tool choice validation
usecase: student-assistant
endpoint: /student-assistant
scorers:
  - answer_quality
  - tool_call_correctness
  - tool_call_efficiency
judge_prompt: judge_prompt.txt
tests:
  - inputs:
      prompt: "What is a forest canopy?"
    expectations:
      expected_result: "A forest canopy is the upper layer of a forest, formed by the crowns of trees. It's an important ecosystem component that provides habitat for many species and plays a crucial role in photosynthesis and the forest's overall health."
      expected_tools:
        - search_knowledge_base
  - inputs:
      prompt: "Who can help me with machine learning?"
    expectations:
      expected_result: "Dr. Sarah Chen from the Computer Science department can help you with machine learning. She specializes in Machine Learning, Neural Networks, AI Ethics, and Agentic Workflows. You can reach her at s.chen@university.edu."
      expected_tools:
        - find_professors_by_expertise
"""


def evals_pipeline_unit_tests_config_yaml(username: str, cluster_domain: str) -> str:
    return f"""---
chart_path: charts/canopy-evals-pipeline
USER_NAME: {username}
CLUSTER_DOMAIN: {cluster_domain}
kfp:
  backendUrl: "http://canopy-backend.{username}-test.svc.cluster.local:8000"
  llmEndpoint: "http://llama-32-predictor.ai501.svc.cluster.local:8080"
testing:
  enableUnitTests: true
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


def gitops_ogx_fp8_config_yaml() -> str:
    """OGX config with both llama32 and llama32-fp8 models."""
    return """---
chart_path: charts/llama-stack-operator-instance
models:
  - name: "llama32"
    url: "http://llama-32-predictor.ai501.svc.cluster.local:8080/v1"
  - name: "llama32-fp8"
    url: "http://llama-32-fp8-predictor.ai501.svc.cluster.local:8080/v1"
rag:
  enabled: true
  milvus:
    service: "milvus-test"
guardrails:
  enabled: true
mcp:
  enabled: true
"""


def gitops_test_backend_fp8_config_yaml(username: str, cluster_domain: str) -> str:
    """Backend config for test env switched to llama32-fp8."""
    return f"""\
repo_url: https://gitea-gitea.{cluster_domain}/{username}/backend
chart_path: chart
summarization:
  enabled: true
  endpoint: "http://llama-stack-service:8321/v1"
  mlflow_prompt: {MLFLOW_PROMPT_NAME}
  mlflow_prompt_version: latest
  model: vllm-llama32-fp8/llama32-fp8
information-search:
  enabled: true
  endpoint: "http://llama-stack-service:8321/v1"
  model: vllm-llama32-fp8/llama32-fp8
  vector_db_id: latest
  mlflow_prompt: information-search
  mlflow_prompt_version: latest
feedback:
  enabled: true
shields:
  enabled: true
  endpoint: http://canopy-guardrails/v1
  model: llama32
  config: canopy-guardrails
student-assistant:
  enabled: true
  model: vllm-llama32-fp8/llama32-fp8
  temperature: 0.1
  vector_db_id: latest
  mcp_calendar_url: "http://canopy-mcp-calendar-mcp-server:8080/sse"
  mlflow_prompt: student-assistant
  mlflow_prompt_version: latest
"""
