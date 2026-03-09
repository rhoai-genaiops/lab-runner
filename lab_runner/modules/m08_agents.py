"""Module 8: Agents - MCP calendar, tool use, agent endpoint."""

from lab_runner.config import Config
from lab_runner import defaults
from lab_runner.modules.base import Module
from lab_runner.steps.base import Step
from lab_runner.steps.helm_step import HelmInstallStep, HelmUpgradeStep
from lab_runner.steps.kube_step import WaitForArgoCDAppsStep, WaitForReadyStep
from lab_runner.steps.git_step import CloneAndModifyStep
from lab_runner.steps.verify_step import CheckPodRunningStep


class AgentsModule(Module):
    @property
    def id(self) -> int:
        return 8

    @property
    def name(self) -> str:
        return "Agents"

    @property
    def dependencies(self) -> list[int]:
        return [5, 7]

    def get_steps(self, config: Config) -> list[Step]:
        ns = config.namespace
        toolings_ns = config.toolings_namespace

        steps: list[Step] = []

        # 1. Install MCP calendar
        steps.append(HelmInstallStep(
            release_name="canopy-mcp-calendar",
            chart=defaults.CHART_MCP_CALENDAR,
            namespace=ns,
            values=defaults.MCP_CALENDAR_VALUES,
            description="Install MCP Calendar",
        ))

        # 2. Wait for calendar pods
        steps.append(WaitForReadyStep(
            label="app.kubernetes.io/instance=canopy-mcp-calendar",
            namespace=ns,
            description="Wait for MCP Calendar pods ready",
        ))

        # 3. Upgrade llama-stack (enable MCP)
        steps.append(HelmUpgradeStep(
            release_name="llama-stack-operator-instance",
            chart=defaults.CHART_LLAMA_STACK,
            namespace=ns,
            values=defaults.LLAMA_STACK_MCP_VALUES,
            verify_key="mcp.enabled",
            verify_value=True,
            description="Upgrade LlamaStack (enable MCP)",
        ))

        # 4. Update test llama-stack config (enable MCP)
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "canopy/test/llama-stack/config.yaml": defaults.gitops_test_llama_stack_mcp_config_yaml(),
            },
            commit_message="Enable MCP in test llama-stack config",
            verify_repo="genaiops-gitops",
            verify_file="canopy/test/llama-stack/config.yaml",
            verify_content="mcp",
            description="Enable MCP in test llama-stack config",
        ))

        # 5. Add calendar-mcp config for test
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "canopy/test/calendar-mcp/config.yaml": defaults.calendar_mcp_config_yaml(),
            },
            commit_message="Add calendar MCP config for test",
            verify_repo="genaiops-gitops",
            verify_file="canopy/test/calendar-mcp/config.yaml",
            description="Add calendar MCP config for test environment",
        ))

        # 6. Enable student-assistant in backend
        steps.append(CloneAndModifyStep(
            repo_url=config.backend_repo_url,
            modifications={
                "chart/values-test.yaml": defaults.backend_values_test_agents_yaml(),
            },
            commit_message="Enable student-assistant feature in backend",
            verify_repo="backend",
            verify_file="chart/values-test.yaml",
            verify_content="student-assistant",
            description="Enable student-assistant in backend test values",
        ))

        # 7. Create evals/student-assistant test files
        steps.append(CloneAndModifyStep(
            repo_url=config.evals_repo_url,
            modifications={
                "student-assistant/student_assistant_tests.yaml": defaults.evals_student_assistant_test_yaml(),
                "student-assistant/e2e_judge_prompt.txt": defaults.evals_student_assistant_e2e_judge_prompt(),
            },
            commit_message="Add student-assistant evaluation tests",
            verify_repo="evals",
            verify_file="student-assistant/student_assistant_tests.yaml",
            description="Add student-assistant eval test files",
        ))

        # 8. Enable unit tests in evaluation-pipeline config
        steps.append(CloneAndModifyStep(
            repo_url=config.gitops_repo_url,
            modifications={
                "toolings/evaluation-pipeline/config.yaml": defaults.evals_pipeline_unit_tests_config_yaml(
                    config.username, config.cluster_domain
                ),
            },
            commit_message="Enable unit tests in evaluation pipeline",
            verify_repo="genaiops-gitops",
            verify_file="toolings/evaluation-pipeline/config.yaml",
            verify_content="enableUnitTests: true",
            description="Enable unit tests in evaluation pipeline config",
        ))

        # 9. Wait for ArgoCD apps synced
        steps.append(WaitForArgoCDAppsStep(
            app_names=["calendar-mcp-test"],
            namespace=toolings_ns,
            timeout=300,
            description="Wait for ArgoCD apps synced",
        ))

        # 10. Verify calendar API pods
        steps.append(CheckPodRunningStep(
            label="app.kubernetes.io/instance=canopy-mcp-calendar",
            namespace=ns,
            description="Verify MCP Calendar pods running",
        ))

        return steps
