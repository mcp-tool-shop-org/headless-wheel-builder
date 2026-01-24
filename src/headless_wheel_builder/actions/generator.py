"""Workflow generator for GitHub Actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from headless_wheel_builder.actions.templates import (
    WorkflowTemplate,
    get_template,
)


@dataclass
class WorkflowConfig:
    """Configuration for workflow generation.

    Attributes:
        template: Template name or WorkflowTemplate object
        output_dir: Output directory for workflow files
        python_version: Python version to use
        python_versions: Multiple Python versions for matrix
        platforms: OS platforms for matrix
        generate_changelog: Generate changelog in release
        use_trusted_publishing: Use PyPI trusted publishing
        custom_vars: Additional template variables
    """

    template: str | WorkflowTemplate
    output_dir: str | Path = ".github/workflows"
    python_version: str = "3.12"
    python_versions: list[str] = field(default_factory=lambda: ["3.10", "3.11", "3.12"])
    platforms: list[str] = field(default_factory=lambda: ["ubuntu-latest"])
    generate_changelog: bool = True
    use_trusted_publishing: bool = True
    custom_vars: dict[str, Any] = field(default_factory=lambda: {})


def generate_workflow(
    config: WorkflowConfig | None = None,
    *,
    template: str | WorkflowTemplate | None = None,
    output_dir: str | Path = ".github/workflows",
    python_version: str = "3.12",
    **kwargs: Any,
) -> str:
    """Generate a GitHub Actions workflow file.

    Args:
        config: Full configuration (overrides other args)
        template: Template name or object
        output_dir: Output directory
        python_version: Python version
        **kwargs: Additional template variables

    Returns:
        Generated workflow YAML content
    """
    if config is None:
        if template is None:
            raise ValueError("Either config or template must be provided")
        config = WorkflowConfig(
            template=template,
            output_dir=output_dir,
            python_version=python_version,
            custom_vars=kwargs,
        )

    # Get template
    tmpl: WorkflowTemplate | None
    if isinstance(config.template, str):
        tmpl = get_template(config.template)
        if tmpl is None:
            raise ValueError(f"Unknown template: {config.template}")
    else:
        tmpl = config.template

    # Build variables for substitution
    variables: dict[str, Any] = {
        "python_version": config.python_version,
        "python_versions": config.python_versions,
        "platforms": config.platforms,
        "generate_changelog": config.generate_changelog,
        "use_trusted_publishing": config.use_trusted_publishing,
        **config.custom_vars,
    }

    # Add derived variables
    if config.generate_changelog:
        variables["changelog_flag"] = "--changelog"
    else:
        variables["changelog_flag"] = ""

    # Render template
    content = tmpl.content

    # Simple string substitution for basic variables
    for key, value in variables.items():
        placeholder = "{" + key + "}"
        if placeholder in content:
            if isinstance(value, list):
                # Format list as YAML array - cast to list[object] for type safety
                items = cast("list[object]", value)
                formatted = repr([str(item) for item in items])
                content = content.replace(placeholder, formatted)
            else:
                content = content.replace(placeholder, str(value))

    return content


def write_workflow(
    config: WorkflowConfig,
    content: str | None = None,
) -> Path:
    """Write workflow file to disk.

    Args:
        config: Workflow configuration
        content: Pre-generated content (generates if not provided)

    Returns:
        Path to written file
    """
    if content is None:
        content = generate_workflow(config)

    # Get template for filename
    tmpl: WorkflowTemplate | None
    if isinstance(config.template, str):
        tmpl = get_template(config.template)
        if tmpl is None:
            raise ValueError(f"Unknown template: {config.template}")
    else:
        tmpl = config.template

    # Ensure output directory exists
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write file
    output_path = output_dir / tmpl.filename
    output_path.write_text(content, encoding="utf-8")

    return output_path


def init_workflows(
    output_dir: str | Path = ".github/workflows",
    templates: list[str] | None = None,
    python_version: str = "3.12",
) -> list[Path]:
    """Initialize multiple workflow files.

    Args:
        output_dir: Output directory
        templates: Template names to generate (default: release, ci, publish)
        python_version: Python version to use

    Returns:
        List of paths to created files
    """
    if templates is None:
        templates = ["release", "ci", "publish"]

    created: list[Path] = []
    for template_name in templates:
        tmpl = get_template(template_name)
        if tmpl is None:
            continue

        config = WorkflowConfig(
            template=tmpl,
            output_dir=output_dir,
            python_version=python_version,
        )

        path = write_workflow(config)
        created.append(path)

    return created
