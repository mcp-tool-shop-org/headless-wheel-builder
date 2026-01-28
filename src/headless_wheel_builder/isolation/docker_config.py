"""Docker configuration management."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

PlatformType = Literal["manylinux", "musllinux", "auto"]


@dataclass
class DockerConfig:
    """Configuration for Docker isolation."""

    # Platform selection
    platform: PlatformType = "auto"
    image: str | None = None  # Override specific image
    architecture: str = "x86_64"  # x86_64, aarch64, i686

    # Container settings
    network: bool = True  # Enable network for pip installs
    memory_limit: str | None = None  # e.g., "4g"
    cpu_limit: float | None = None  # e.g., 2.0 for 2 CPUs

    # Build settings
    repair_wheel: bool = True  # Run auditwheel/delocate
    strip_binaries: bool = True  # Strip debug symbols

    # Volume mounts
    extra_mounts: dict[str, str] = field(default_factory=dict)

    # Environment variables
    extra_env: dict[str, str] = field(default_factory=dict)


def build_env_vars(config: DockerConfig) -> dict[str, str]:
    """Build environment variables for Docker container."""
    env = {
        # Disable interactive prompts
        "DEBIAN_FRONTEND": "noninteractive",
        # Pip settings
        "PIP_NO_CACHE_DIR": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        # Build settings
        "PYTHONDONTWRITEBYTECODE": "1",
    }

    # Add extra env vars from config
    if config.extra_env:
        env.update(config.extra_env)

    return env
