"""Module 8: Agents - MCP calendar, OGX MCP, student-assistant via GitOps."""

from lab_runner.config import Config
from lab_runner import defaults
from lab_runner.modules.base import Module
from lab_runner.steps.base import Step
from lab_runner.steps.kube_step import WaitForArgoCDAppsStep
from lab_runner.steps.git_step import CloneAndModifyStep
from lab_runner.steps.mlflow_step import CreateMLflowPromptStep
from lab_runner.steps.verify_step import CheckPodRunningStep, CheckAllPodsRunningStep


class AgentsModule(Module):
    @property
    def id(self) -> int:
        return 8

    @property
    def name(self) -> str:
        return "Agents"

    @property
    def dependencies(self) -> list[int]:
        return [7]

    def get_steps(self, config: Config) -> list[Step]:
        toolings_ns = config.toolings_namespace
        test_ns = config.test_namespace

        steps: list[Step] = []

        # 1. Register student-assistant prompt in toolings MLflow
        steps.append(CreateMLflowPromptStep(
            name="student-assistant",
            template=defaults.STUDENT_ASSISTANT_PROMPT,
            namespace=config.toolings_namespace,
            commit_message="Initial student-assistant prompt",
            description="Register 'student-assistant' prompt in toolings MLflow",
        ))

        # 3. Enable MCP in OGX + add calendar-mcp + enable student-assistant in backend
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "canopy/test/ogx/config.yaml": defaults.gitops_ogx_mcp_config_yaml("test", config.username),
                "canopy/test/calendar-mcp/config.yaml": defaults.calendar_mcp_config_yaml(),
                "canopy/test/backend/config.yaml": defaults.gitops_test_backend_agents_config_yaml(
                    config.username, config.cluster_domain
                ),
            },
            commit_message="Agent feature and Calendar MCP added",
            verify_repo="genaiops-gitops",
            verify_file="canopy/test/ogx/config.yaml",
            verify_content="mcp",
            description="Enable MCP in OGX and add calendar-mcp + student-assistant",
        ))

        # 4. Wait for calendar-mcp and backend ArgoCD apps to sync
        steps.append(WaitForArgoCDAppsStep(
            app_names=["calendar-mcp-test", "backend-test"],
            namespace=toolings_ns,
            timeout=300,
            description="Wait for calendar-mcp and backend deployed",
        ))

        # 5. Enable unit tests in evaluation pipeline config
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "toolings/evaluation-pipeline/config.yaml": defaults.evals_pipeline_unit_tests_config_yaml(
                    config.username, config.cluster_domain
                ),
            },
            commit_message="Enabled unit tests",
            verify_repo="genaiops-gitops",
            verify_file="toolings/evaluation-pipeline/config.yaml",
            verify_content="enableUnitTests",
            description="Enable unit tests in evaluation pipeline config",
        ))

        # 6. Add student-assistant E2E eval test files
        steps.append(CloneAndModifyStep(
            repo_url=config.evals_repo_url,
            modifications={
                "student-assistant/student_assistant_tests.yaml": defaults.evals_student_assistant_test_yaml(),
                "student-assistant/judge_prompt.txt": defaults.evals_student_assistant_judge_prompt(),
            },
            commit_message="Agent E2E tests added",
            verify_repo="evals",
            verify_file="student-assistant/student_assistant_tests.yaml",
            description="Add student-assistant eval test files",
        ))

        # 7. Verify all MCP Calendar pods running in test
        steps.append(CheckAllPodsRunningStep(
            label="app.kubernetes.io/name=canopy-mcp-calendar",
            namespace=test_ns,
            min_count=3,
            description="Verify MCP Calendar pods running in test",
        ))

        return steps
