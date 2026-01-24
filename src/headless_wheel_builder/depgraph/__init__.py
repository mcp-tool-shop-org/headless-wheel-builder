"""Dependency graph analysis.

This module provides:

- Dependency tree visualization
- Circular dependency detection
- License compliance checking
- Version conflict analysis
- Build order optimization
"""

from __future__ import annotations

from headless_wheel_builder.depgraph.analyzer import DependencyAnalyzer
from headless_wheel_builder.depgraph.models import (
    ConflictInfo,
    DependencyGraph,
    DependencyNode,
    LicenseInfo,
)
from headless_wheel_builder.depgraph.resolver import DependencyResolver

__all__ = [
    "ConflictInfo",
    "DependencyAnalyzer",
    "DependencyGraph",
    "DependencyNode",
    "DependencyResolver",
    "LicenseInfo",
]
