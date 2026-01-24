"""Base classes for build isolation strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path


@dataclass
class BuildEnvironment:
    """An isolated build environment."""

    python_path: Path
    site_packages: Path
    env_vars: dict[str, str]
    _cleanup: Callable[[], Awaitable[None]] | None = field(default=None, repr=False)

    async def cleanup(self) -> None:
        """Clean up the environment."""
        if self._cleanup:
            await self._cleanup()

    async def __aenter__(self) -> BuildEnvironment:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.cleanup()


@runtime_checkable
class IsolationStrategy(Protocol):
    """Protocol for build isolation strategies."""

    async def create_environment(
        self,
        python_version: str,
        build_requirements: list[str],
    ) -> BuildEnvironment:
        """
        Create an isolated build environment.

        Args:
            python_version: Python version to use (e.g., "3.12")
            build_requirements: List of packages to install

        Returns:
            BuildEnvironment ready for building
        """
        ...

    async def check_available(self) -> bool:
        """Check if this isolation strategy is available."""
        ...


class BaseIsolation(ABC):
    """Base class for isolation strategies."""

    @abstractmethod
    async def create_environment(
        self,
        python_version: str,
        build_requirements: list[str],
    ) -> BuildEnvironment:
        """Create an isolated build environment."""
        ...

    @abstractmethod
    async def check_available(self) -> bool:
        """Check if this isolation strategy is available."""
        ...
