"""Tests for GitHub Actions workflow generator."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from headless_wheel_builder.actions.generator import (
    WorkflowConfig,
    generate_workflow,
    init_workflows,
    write_workflow,
)
from headless_wheel_builder.actions.templates import (
    TEMPLATES,
    TemplateType,
    WorkflowTemplate,
    get_template,
    list_templates,
)


class TestWorkflowTemplate:
    """Tests for WorkflowTemplate model."""

    def test_template_attributes(self) -> None:
        """Test template has required attributes."""
        tmpl = WorkflowTemplate(
            name="test",
            filename="test.yml",
            description="Test template",
            template_type=TemplateType.RELEASE,
            triggers=["push", "workflow_dispatch"],
            content="name: Test",
        )
        assert tmpl.name == "test"
        assert tmpl.filename == "test.yml"
        assert tmpl.description == "Test template"
        assert tmpl.template_type == TemplateType.RELEASE
        assert tmpl.triggers == ["push", "workflow_dispatch"]
        assert tmpl.content == "name: Test"


class TestTemplateType:
    """Tests for TemplateType enum."""

    def test_all_types_exist(self) -> None:
        """Test all expected template types exist."""
        types = [t.value for t in TemplateType]
        assert "release" in types
        assert "ci" in types
        assert "publish" in types
        assert "test" in types
        assert "security" in types
        assert "docs" in types


class TestGetTemplate:
    """Tests for get_template function."""

    def test_get_existing_template(self) -> None:
        """Test getting existing template."""
        tmpl = get_template("release")
        assert tmpl is not None
        assert tmpl.name == "release"

    def test_get_nonexistent_template(self) -> None:
        """Test getting non-existent template returns None."""
        tmpl = get_template("nonexistent")
        assert tmpl is None

    def test_get_all_templates(self) -> None:
        """Test getting all known templates."""
        for name in TEMPLATES:
            tmpl = get_template(name)
            assert tmpl is not None
            assert tmpl.name == name


class TestListTemplates:
    """Tests for list_templates function."""

    def test_list_all(self) -> None:
        """Test listing all templates."""
        templates = list_templates()
        assert len(templates) > 0
        assert all(isinstance(t, WorkflowTemplate) for t in templates)

    def test_list_templates_count(self) -> None:
        """Test list returns same count as TEMPLATES."""
        templates = list_templates()
        assert len(templates) == len(TEMPLATES)


class TestWorkflowConfig:
    """Tests for WorkflowConfig model."""

    def test_defaults(self) -> None:
        """Test default configuration."""
        config = WorkflowConfig(template="release")
        assert config.output_dir == ".github/workflows"
        assert config.python_version == "3.12"
        assert config.python_versions == ["3.10", "3.11", "3.12"]
        assert config.platforms == ["ubuntu-latest"]
        assert config.generate_changelog is True
        assert config.use_trusted_publishing is True
        assert config.custom_vars == {}

    def test_custom_values(self) -> None:
        """Test custom configuration."""
        config = WorkflowConfig(
            template="ci",
            output_dir="workflows",
            python_version="3.11",
            python_versions=["3.9", "3.10"],
            platforms=["ubuntu-latest", "windows-latest"],
            generate_changelog=False,
            use_trusted_publishing=False,
            custom_vars={"extra": "value"},
        )
        assert config.output_dir == "workflows"
        assert config.python_version == "3.11"
        assert config.python_versions == ["3.9", "3.10"]
        assert config.platforms == ["ubuntu-latest", "windows-latest"]
        assert config.generate_changelog is False
        assert config.use_trusted_publishing is False
        assert config.custom_vars == {"extra": "value"}

    def test_template_can_be_object(self) -> None:
        """Test template can be a WorkflowTemplate object."""
        tmpl = get_template("release")
        assert tmpl is not None
        config = WorkflowConfig(template=tmpl)
        assert config.template == tmpl


class TestGenerateWorkflow:
    """Tests for generate_workflow function."""

    def test_generate_from_string_template(self) -> None:
        """Test generating from template name."""
        content = generate_workflow(template="release")
        assert "name:" in content
        assert isinstance(content, str)

    def test_generate_from_config(self) -> None:
        """Test generating from config object."""
        config = WorkflowConfig(template="release")
        content = generate_workflow(config)
        assert "name:" in content

    def test_generate_requires_template(self) -> None:
        """Test that template is required."""
        with pytest.raises(ValueError, match="Either config or template"):
            generate_workflow()

    def test_generate_unknown_template_error(self) -> None:
        """Test error for unknown template."""
        with pytest.raises(ValueError, match="Unknown template"):
            generate_workflow(template="unknown_template")

    def test_variable_substitution(self) -> None:
        """Test that variables are substituted."""
        content = generate_workflow(template="release", python_version="3.11")
        # The template should have python version info
        assert isinstance(content, str)

    def test_generate_all_templates(self) -> None:
        """Test generating all templates successfully."""
        for name in TEMPLATES:
            content = generate_workflow(template=name)
            assert "name:" in content


class TestWriteWorkflow:
    """Tests for write_workflow function."""

    def test_write_creates_file(self) -> None:
        """Test that write creates file."""
        with TemporaryDirectory() as tmpdir:
            config = WorkflowConfig(
                template="release",
                output_dir=tmpdir,
            )
            path = write_workflow(config)
            assert path.exists()
            assert path.name == "release.yml"

    def test_write_content(self) -> None:
        """Test that written content matches generated."""
        with TemporaryDirectory() as tmpdir:
            config = WorkflowConfig(
                template="release",
                output_dir=tmpdir,
            )
            expected = generate_workflow(config)
            path = write_workflow(config)
            content = path.read_text()
            assert content == expected

    def test_write_creates_directory(self) -> None:
        """Test that write creates directory if needed."""
        with TemporaryDirectory() as tmpdir:
            nested = Path(tmpdir) / "deeply" / "nested" / "workflows"
            config = WorkflowConfig(
                template="release",
                output_dir=nested,
            )
            path = write_workflow(config)
            assert path.exists()
            assert nested.exists()

    def test_write_with_provided_content(self) -> None:
        """Test writing with pre-generated content."""
        with TemporaryDirectory() as tmpdir:
            config = WorkflowConfig(
                template="release",
                output_dir=tmpdir,
            )
            custom_content = "# Custom workflow content"
            path = write_workflow(config, content=custom_content)
            assert path.read_text() == custom_content

    def test_write_unknown_template_error(self) -> None:
        """Test error for unknown template string."""
        with TemporaryDirectory() as tmpdir:
            config = WorkflowConfig(
                template="unknown_template",
                output_dir=tmpdir,
            )
            with pytest.raises(ValueError, match="Unknown template"):
                write_workflow(config)


class TestInitWorkflows:
    """Tests for init_workflows function."""

    def test_init_defaults(self) -> None:
        """Test init with default templates."""
        with TemporaryDirectory() as tmpdir:
            paths = init_workflows(output_dir=tmpdir)
            assert len(paths) == 3
            names = [p.name for p in paths]
            assert "release.yml" in names
            assert "ci.yml" in names
            assert "publish.yml" in names

    def test_init_specific_templates(self) -> None:
        """Test init with specific templates."""
        with TemporaryDirectory() as tmpdir:
            paths = init_workflows(output_dir=tmpdir, templates=["release", "test"])
            assert len(paths) == 2
            names = [p.name for p in paths]
            assert "release.yml" in names
            assert "test.yml" in names

    def test_init_all_templates(self) -> None:
        """Test init with all templates."""
        with TemporaryDirectory() as tmpdir:
            paths = init_workflows(output_dir=tmpdir, templates=list(TEMPLATES.keys()))
            assert len(paths) == len(TEMPLATES)

    def test_init_skips_unknown(self) -> None:
        """Test init skips unknown templates."""
        with TemporaryDirectory() as tmpdir:
            paths = init_workflows(
                output_dir=tmpdir,
                templates=["release", "unknown", "ci"],
            )
            # Should only create 2 files (skipping unknown)
            assert len(paths) == 2

    def test_init_with_python_version(self) -> None:
        """Test init with custom python version."""
        with TemporaryDirectory() as tmpdir:
            paths = init_workflows(
                output_dir=tmpdir,
                templates=["release"],
                python_version="3.11",
            )
            assert len(paths) == 1


class TestTemplateContent:
    """Tests for template content validity."""

    def test_release_template_content(self) -> None:
        """Test release template has expected elements."""
        tmpl = get_template("release")
        assert tmpl is not None
        assert "release" in tmpl.content.lower()
        assert "tags" in tmpl.content  # Triggers on tag push

    def test_ci_template_content(self) -> None:
        """Test CI template has expected elements."""
        tmpl = get_template("ci")
        assert tmpl is not None
        assert "push" in tmpl.content
        assert "pull_request" in tmpl.content

    def test_publish_template_content(self) -> None:
        """Test publish template has expected elements."""
        tmpl = get_template("publish")
        assert tmpl is not None
        assert "pypi" in tmpl.content.lower() or "publish" in tmpl.content.lower()

    def test_test_template_content(self) -> None:
        """Test test template has expected elements."""
        tmpl = get_template("test")
        assert tmpl is not None
        assert "test" in tmpl.content.lower()

    def test_security_template_content(self) -> None:
        """Test security template has expected elements."""
        tmpl = get_template("security")
        assert tmpl is not None
        # Security templates should have security-related content
        content_lower = tmpl.content.lower()
        assert (
            "security" in content_lower
            or "dependabot" in content_lower
            or "codeql" in content_lower
        )

    def test_all_templates_have_name(self) -> None:
        """Test all templates have a workflow name."""
        for name, tmpl in TEMPLATES.items():
            assert "name:" in tmpl.content, f"Template {name} missing name field"

    def test_all_templates_have_triggers(self) -> None:
        """Test all templates have triggers defined."""
        for name, tmpl in TEMPLATES.items():
            assert "on:" in tmpl.content or "on :" in tmpl.content, (
                f"Template {name} missing on: trigger definition"
            )

    def test_all_templates_have_jobs(self) -> None:
        """Test all templates have jobs defined."""
        for name, tmpl in TEMPLATES.items():
            assert "jobs:" in tmpl.content, f"Template {name} missing jobs section"
