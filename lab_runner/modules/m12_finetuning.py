"""Module 12: Fine-Tuning - Mostly notebook-driven, minimal automation."""

from lab_runner.config import Config
from lab_runner.modules.base import Module
from lab_runner.steps.base import Step
from lab_runner.steps.verify_step import CheckResourceExistsStep


class FineTuningModule(Module):
    @property
    def id(self) -> int:
        return 12

    @property
    def name(self) -> str:
        return "Fine-Tuning"

    @property
    def dependencies(self) -> list[int]:
        return [3]

    def get_steps(self, config: Config) -> list[Step]:
        steps: list[Step] = []

        # 1. Verify model registry accessible
        steps.append(CheckResourceExistsStep(
            resource_type="modelregistry",
            name="modelregistry-sample",
            namespace="rhoai-model-registries",
            description="Verify Model Registry CR exists",
        ))

        # Note: Fine-tuning exercises are notebook-driven (synthetic data gen,
        # LoRA training). This module only verifies infrastructure prerequisites.

        return steps
