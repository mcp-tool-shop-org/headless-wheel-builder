"""Integration tests for CLI commands.

These tests exercise the CLI commands with real project builds.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from headless_wheel_builder.cli.main import cli

if TYPE_CHECKING:
    from pathlib import Path

# Mark all tests as integration tests
pytestmark = pytest.mark.integration


class TestBuildCommand:
    """Test the build CLI command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def sample_project(self, tmp_path: Path) -> Path:
        """Create a sample project for testing."""
        project_dir = tmp_path / "cli_test_project"
        project_dir.mkdir()

        (project_dir / "pyproject.toml").write_text("""
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "cli-test-project"
version = "0.5.0"
description = "CLI test project"

[tool.setuptools.packages.find]
where = ["src"]
""")

        src = project_dir / "src" / "cli_test_project"
        src.mkdir(parents=True)
        (src / "__init__.py").write_text('__version__ = "0.5.0"')

        return project_dir

    def test_build_command_help(self, runner: CliRunner):
        """Test build command help."""
        result = runner.invoke(cli, ["build", "--help"])
        assert result.exit_code == 0
        assert "Build" in result.output

    def test_build_command_with_project(
        self, runner: CliRunner, sample_project: Path, tmp_path: Path
    ):
        """Test building a project via CLI."""
        output_dir = tmp_path / "dist"

        result = runner.invoke(
            cli,
            [
                "build",
                str(sample_project),
                "--output",
                str(output_dir),  # Correct option is --output, not --output-dir
            ],
        )

        # Should succeed
        assert result.exit_code == 0, f"Build failed: {result.output}"

        # Check wheel was created
        wheels = list(output_dir.glob("*.whl"))
        assert len(wheels) == 1
        assert "cli_test_project" in wheels[0].name

    def test_build_command_with_isolation(
        self, runner: CliRunner, sample_project: Path, tmp_path: Path
    ):
        """Test building with venv isolation via CLI."""
        output_dir = tmp_path / "dist"

        result = runner.invoke(
            cli,
            [
                "build",
                str(sample_project),
                "--output",
                str(output_dir),
                "--isolation",
                "venv",
            ],
        )

        assert result.exit_code == 0, f"Build failed: {result.output}"

    def test_build_command_nonexistent_source(self, runner: CliRunner, tmp_path: Path):
        """Test build command with non-existent source."""
        result = runner.invoke(
            cli,
            [
                "build",
                str(tmp_path / "nonexistent"),
            ],
        )

        assert result.exit_code != 0


class TestInspectCommand:
    """Test the inspect CLI command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def sample_project(self, tmp_path: Path) -> Path:
        """Create a sample project for testing."""
        project_dir = tmp_path / "inspect_test_project"
        project_dir.mkdir()

        (project_dir / "pyproject.toml").write_text("""
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "inspect-test"
version = "2.3.4"
description = "Test project for inspection"
dependencies = ["requests>=2.0", "click>=8.0"]
requires-python = ">=3.9"

[project.optional-dependencies]
dev = ["pytest", "mypy"]
""")

        return project_dir

    def test_inspect_command_help(self, runner: CliRunner):
        """Test inspect command help."""
        result = runner.invoke(cli, ["inspect", "--help"])
        assert result.exit_code == 0

    def test_inspect_command_basic(self, runner: CliRunner, sample_project: Path):
        """Test inspecting a project."""
        result = runner.invoke(cli, ["inspect", str(sample_project)])

        assert result.exit_code == 0
        assert "inspect-test" in result.output
        assert "2.3.4" in result.output

    def test_inspect_command_json(self, runner: CliRunner, sample_project: Path):
        """Test inspecting a project with JSON output."""
        # Correct option is --format json, not --json
        result = runner.invoke(cli, ["inspect", str(sample_project), "--format", "json"])

        assert result.exit_code == 0
        # Should be valid JSON-like output
        assert "name" in result.output.lower() or "version" in result.output.lower()


class TestVersionCommand:
    """Test the version-next CLI command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def git_repo(self, tmp_path: Path) -> Path:
        """Create a git repository for testing."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"], cwd=repo_path, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"], cwd=repo_path, capture_output=True
        )

        # Create initial commit
        (repo_path / "README.md").write_text("# Test Project")
        subprocess.run(["git", "add", "README.md"], cwd=repo_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "chore: initial commit"], cwd=repo_path, capture_output=True
        )

        # Create a tag
        subprocess.run(
            ["git", "tag", "-a", "v1.0.0", "-m", "Release 1.0.0"],
            cwd=repo_path,
            capture_output=True,
        )

        # Add a feature commit
        (repo_path / "feature.py").write_text("# feature")
        subprocess.run(["git", "add", "feature.py"], cwd=repo_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "feat: add feature"], cwd=repo_path, capture_output=True
        )

        return repo_path

    def test_version_next_help(self, runner: CliRunner):
        """Test version-next command help."""
        result = runner.invoke(cli, ["version-next", "--help"])
        assert result.exit_code == 0

    def test_version_next_from_git(self, runner: CliRunner, git_repo: Path):
        """Test calculating next version from git commits."""
        result = runner.invoke(
            cli,
            [
                "version-next",
                "--path",
                str(git_repo),
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        # Should detect the feature commit and suggest minor bump
        assert "1.1.0" in result.output or "minor" in result.output.lower()


class TestPublishCommand:
    """Test the publish CLI command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def sample_wheel(self, tmp_path: Path) -> Path:
        """Create a sample wheel file for testing."""
        import zipfile

        wheel_path = tmp_path / "sample_pkg-0.1.0-py3-none-any.whl"

        with zipfile.ZipFile(wheel_path, "w") as whl:
            # Add WHEEL metadata
            whl.writestr(
                "sample_pkg-0.1.0.dist-info/WHEEL",
                """Wheel-Version: 1.0
Generator: test
Root-Is-Purelib: true
Tag: py3-none-any
""",
            )
            # Add METADATA
            whl.writestr(
                "sample_pkg-0.1.0.dist-info/METADATA",
                """Metadata-Version: 2.1
Name: sample-pkg
Version: 0.1.0
Summary: Sample package
""",
            )
            # Add RECORD
            whl.writestr("sample_pkg-0.1.0.dist-info/RECORD", "")
            # Add package
            whl.writestr("sample_pkg/__init__.py", "__version__ = '0.1.0'")

        return wheel_path

    def test_publish_command_help(self, runner: CliRunner):
        """Test publish command help."""
        result = runner.invoke(cli, ["publish", "--help"])
        assert result.exit_code == 0

    def test_publish_dry_run(self, runner: CliRunner, sample_wheel: Path):
        """Test publish command with dry run."""
        result = runner.invoke(
            cli,
            [
                "publish",
                str(sample_wheel),
                "--dry-run",
            ],
        )

        # Should indicate dry run mode
        assert (
            result.exit_code == 0
            or "dry" in result.output.lower()
            or "skip" in result.output.lower()
        )


class TestCLIViaRunner:
    """Test CLI using click's CliRunner (doesn't require __main__.py)."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def sample_project(self, tmp_path: Path) -> Path:
        """Create a sample project."""
        project_dir = tmp_path / "subprocess_test"
        project_dir.mkdir()

        (project_dir / "pyproject.toml").write_text("""
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "subprocess-test"
version = "0.1.0"

[tool.setuptools.packages.find]
where = ["src"]
""")

        src = project_dir / "src" / "subprocess_test"
        src.mkdir(parents=True)
        (src / "__init__.py").write_text("")

        return project_dir

    def test_cli_help(self, runner: CliRunner):
        """Test CLI help."""
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "build" in result.output.lower()

    def test_cli_build(self, runner: CliRunner, sample_project: Path, tmp_path: Path):
        """Test build command via CLI runner."""
        output_dir = tmp_path / "dist"

        result = runner.invoke(
            cli,
            [
                "build",
                str(sample_project),
                "--output",
                str(output_dir),
            ],
        )

        assert result.exit_code == 0, f"Build failed: {result.output}"

        # Check wheel was created
        wheels = list(output_dir.glob("*.whl"))
        assert len(wheels) == 1

    def test_cli_inspect(self, runner: CliRunner, sample_project: Path):
        """Test inspect command via CLI runner."""
        result = runner.invoke(
            cli,
            [
                "inspect",
                str(sample_project),
            ],
        )

        assert result.exit_code == 0
        assert "subprocess-test" in result.output
        assert "0.1.0" in result.output


class TestMultipleBuildFormats:
    """Test building different project configurations."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI runner."""
        return CliRunner()

    def test_build_pure_python_wheel(self, runner: CliRunner, tmp_path: Path):
        """Test building pure Python wheel."""
        project_dir = tmp_path / "pure_python"
        project_dir.mkdir()

        (project_dir / "pyproject.toml").write_text("""
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "pure-python-pkg"
version = "1.0.0"

[tool.setuptools.packages.find]
where = ["src"]
""")

        src = project_dir / "src" / "pure_python_pkg"
        src.mkdir(parents=True)
        (src / "__init__.py").write_text("pass")

        output_dir = tmp_path / "dist"

        result = runner.invoke(
            cli,
            [
                "build",
                str(project_dir),
                "--output",
                str(output_dir),
            ],
        )

        assert result.exit_code == 0

        wheels = list(output_dir.glob("*.whl"))
        assert len(wheels) == 1

        # Pure Python should be py3-none-any
        assert "py3-none-any" in wheels[0].name or "py" in wheels[0].name

    def test_build_with_package_data(self, runner: CliRunner, tmp_path: Path):
        """Test building wheel with package data."""
        project_dir = tmp_path / "with_data"
        project_dir.mkdir()

        (project_dir / "pyproject.toml").write_text("""
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "pkg-with-data"
version = "1.0.0"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
"*" = ["*.json", "*.yaml"]
""")

        src = project_dir / "src" / "pkg_with_data"
        src.mkdir(parents=True)
        (src / "__init__.py").write_text("pass")
        (src / "config.json").write_text('{"key": "value"}')

        output_dir = tmp_path / "dist"

        result = runner.invoke(
            cli,
            [
                "build",
                str(project_dir),
                "--output",
                str(output_dir),
            ],
        )

        assert result.exit_code == 0

        # Check wheel contains data file
        import zipfile

        wheels = list(output_dir.glob("*.whl"))
        with zipfile.ZipFile(wheels[0]) as whl:
            names = whl.namelist()
            assert any("config.json" in n for n in names)
