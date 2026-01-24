"""Headless Wheel Builder - Universal Python wheel builder for CI/CD pipelines."""

from headless_wheel_builder.core.builder import BuildResult, build_wheel
from headless_wheel_builder.core.source import ResolvedSource, SourceSpec, SourceType

__version__ = "0.3.0"

__all__ = [
    "BuildResult",
    "ResolvedSource",
    "SourceSpec",
    "SourceType",
    "__version__",
    "build_wheel",
]


# Lazy import for optional modules to avoid import overhead when not needed
def __getattr__(name: str):
    """Lazy import optional modules."""
    if name == "github":
        from headless_wheel_builder import github

        return github
    if name == "pipeline":
        from headless_wheel_builder import pipeline

        return pipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
