"""Multi-repository operations for Headless Wheel Builder.

This module provides functionality for managing multiple repositories
from a single configuration, including:

- Batch builds across repositories
- Coordinated releases
- Dependency-aware ordering
- Parallel execution
"""

from __future__ import annotations

from headless_wheel_builder.multirepo.config import (
    MultiRepoConfig,
    RepoConfig,
    load_config,
    save_config,
)
from headless_wheel_builder.multirepo.manager import (
    BatchResult,
    MultiRepoManager,
    RepoResult,
)

__all__ = [
    "BatchResult",
    "MultiRepoConfig",
    "MultiRepoManager",
    "RepoConfig",
    "RepoResult",
    "load_config",
    "save_config",
]
