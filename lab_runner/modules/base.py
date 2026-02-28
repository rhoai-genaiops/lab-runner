"""Base module abstraction for lab runner."""

from abc import ABC, abstractmethod

from lab_runner.config import Config
from lab_runner.steps.base import Step


class Module(ABC):
    """Base class for all lab modules."""

    @property
    @abstractmethod
    def id(self) -> int:
        """Module number (e.g., 2, 3, 4...)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable module name."""

    @property
    @abstractmethod
    def dependencies(self) -> list[int]:
        """List of module IDs that must complete first."""

    @abstractmethod
    def get_steps(self, config: Config) -> list[Step]:
        """Return ordered list of steps for this module."""
