"""Base step abstraction for lab runner."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

from lab_runner.config import Config


class StepStatus(Enum):
    PENDING = "pending"
    SKIPPED = "skipped"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class StepResult:
    status: StepStatus
    message: str = ""
    output: str = ""

    @classmethod
    def success(cls, message: str = "", output: str = "") -> "StepResult":
        return cls(status=StepStatus.SUCCESS, message=message, output=output)

    @classmethod
    def skipped(cls, message: str = "Already done") -> "StepResult":
        return cls(status=StepStatus.SKIPPED, message=message)

    @classmethod
    def failed(cls, message: str, output: str = "") -> "StepResult":
        return cls(status=StepStatus.FAILED, message=message, output=output)


class Step(ABC):
    """Base class for all automation steps."""

    description: str = "Unnamed step"
    active_description: str = "Running step..."

    def skip_if_done(self) -> bool:
        """If verify() returns True, skip run(). Default: True."""
        return True

    @abstractmethod
    def verify(self, config: Config) -> bool:
        """Return True if this step's outcome already exists (idempotency)."""

    @abstractmethod
    def run(self, config: Config) -> StepResult:
        """Execute the step. Should be idempotent."""
