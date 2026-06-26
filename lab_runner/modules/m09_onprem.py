"""Module 9: On-Prem Practicum - TinyLlama CPU deployment."""

from lab_runner.config import Config
from lab_runner import defaults
from lab_runner.modules.base import Module
from lab_runner.steps.base import Step
from lab_runner.steps.helm_step import HelmUpgradeStep
from lab_runner.steps.kube_step import ApplyManifestStep, WaitForReadyStep


class OnPremModule(Module):
    @property
    def id(self) -> int:
        return 9

    @property
    def name(self) -> str:
        return "On-Prem Practicum"

    @property
    def dependencies(self) -> list[int]:
        return [8]

    def get_steps(self, config: Config) -> list[Step]:
        ns = config.namespace

        steps: list[Step] = []

        # 1. Apply TinyLlama manifests (Secret + ServingRuntime + InferenceService)
        steps.append(ApplyManifestStep(
            manifest=defaults.tinyllama_manifests(ns),
            namespace=ns,
            resource_type="inferenceservice",
            resource_name="tinyllama",
            description="Apply TinyLlama Secret, ServingRuntime & InferenceService",
        ))

        # 2. Wait for TinyLlama predictor ready
        steps.append(WaitForReadyStep(
            label="serving.kserve.io/inferenceservice=tinyllama",
            namespace=ns,
            timeout=600,
            description="Wait for TinyLlama predictor ready",
        ))

        # 3. Upgrade llama-stack (add tinyllama model)
        steps.append(HelmUpgradeStep(
            release_name="llama-stack-operator-instance",
            chart=defaults.CHART_LLAMA_STACK,
            namespace=ns,
            values=defaults.llama_stack_onprem_values(ns),
            description="Upgrade LlamaStack (add TinyLlama model)",
        ))

        return steps
