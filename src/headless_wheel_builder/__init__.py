"""Headless Wheel Builder - Universal Python wheel builder for CI/CD pipelines."""

from headless_wheel_builder.core.builder import BuildResult, build_wheel
from headless_wheel_builder.core.source import ResolvedSource, SourceSpec, SourceType

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "build_wheel",
    "BuildResult",
    "SourceSpec",
    "SourceType",
    "ResolvedSource",
]
