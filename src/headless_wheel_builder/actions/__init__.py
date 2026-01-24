"""GitHub Actions workflow generator."""

from headless_wheel_builder.actions.generator import (
    WorkflowConfig,
    WorkflowTemplate,
    generate_workflow,
)
from headless_wheel_builder.actions.templates import (
    TEMPLATES,
    get_template,
    list_templates,
)

__all__ = [
    "TEMPLATES",
    "WorkflowConfig",
    "WorkflowTemplate",
    "generate_workflow",
    "get_template",
    "list_templates",
]
