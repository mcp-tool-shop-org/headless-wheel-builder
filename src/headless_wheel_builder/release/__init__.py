"""Draft releases and approval workflows.

This module provides:

- Draft release creation and management
- Multi-stage approval workflows
- Release notes generation
- Automated release publishing
- Rollback support
"""

from __future__ import annotations

from headless_wheel_builder.release.manager import ReleaseManager
from headless_wheel_builder.release.models import (
    ApprovalState,
    ApprovalStep,
    DraftRelease,
    ReleaseConfig,
    ReleaseStatus,
)
from headless_wheel_builder.release.workflow import ApprovalWorkflow

__all__ = [
    "ApprovalState",
    "ApprovalStep",
    "ApprovalWorkflow",
    "DraftRelease",
    "ReleaseConfig",
    "ReleaseManager",
    "ReleaseStatus",
]
