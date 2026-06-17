"""Module 2: Linguistics - First deployment of Canopy UI."""

from lab_runner.config import Config
from lab_runner.defaults import CANOPY_UI_VALUES, CHART_CANOPY_UI, MLFLOW_PROMPT_NAME, SYSTEM_PROMPT
from lab_runner.modules.base import Module
from lab_runner.steps.base import Step
from lab_runner.steps.helm_step import HelmInstallStep
from lab_runner.steps.kube_step import OcLoginStep, WaitForReadyStep
from lab_runner.steps.mlflow_step import CreateMLflowPromptStep
from lab_runner.steps.verify_step import CheckRouteAccessibleStep


class LinguisticsModule(Module):
    @property
    def id(self) -> int:
        return 2

    @property
    def name(self) -> str:
        return "Linguistics"

    @property
    def dependencies(self) -> list[int]:
        return []

    def get_steps(self, config: Config) -> list[Step]:
        ns = config.namespace
        values = {
            **CANOPY_UI_VALUES,
            "LLM_ENDPOINT": config.llm_endpoint,
        }

        return [
            OcLoginStep(),
            CreateMLflowPromptStep(
                name=MLFLOW_PROMPT_NAME,
                template=SYSTEM_PROMPT,
                namespace=ns,
                commit_message="Initial summarization prompt",
                description=f"Register '{MLFLOW_PROMPT_NAME}' prompt in {ns} MLflow",
            ),
            HelmInstallStep(
                release_name="canopy-ui",
                chart=CHART_CANOPY_UI,
                namespace=ns,
                values=values,
                description="Install Canopy UI Helm release",
            ),
            WaitForReadyStep(
                label="app.kubernetes.io/name=canopy-ui",
                namespace=ns,
                description="Wait for canopy-ui pod ready",
            ),
            CheckRouteAccessibleStep(
                url=config.route_url("canopy-ui"),
                description="Verify canopy-ui route accessible",
            ),
        ]
