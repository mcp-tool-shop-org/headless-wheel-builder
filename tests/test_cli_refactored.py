"""Tests for refactored CLI commands."""

import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from headless_wheel_builder.cli.commands.build import (
    _parse_config_settings,
    validate_build_options,
)
from headless_wheel_builder.cli.main import cli


class TestBuildCommandValidation:
    """Test build command validation."""

    def test_validate_missing_source(self):
        """Test validation rejects missing source directory."""
        with pytest.raises(Exception):  # click.BadParameter
            validate_build_options(
                source="/nonexistent/path",
                output_dir="dist",
                python="3.12",
                isolation="venv",
                docker_image=None,
                platform="auto",
            )

    def test_validate_missing_pyproject_toml(self):
        """Test validation requires pyproject.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(Exception):  # click.BadParameter
                validate_build_options(
                    source=tmpdir,
                    output_dir="dist",
                    python="3.12",
                    isolation="venv",
                    docker_image=None,
                    platform="auto",
                )

    def test_validate_valid_project(self):
        """Test validation passes for valid project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "pyproject.toml").touch()

            # Should not raise
            validate_build_options(
                source=str(project_dir),
                output_dir="dist",
                python="3.12",
                isolation="venv",
                docker_image=None,
                platform="auto",
            )

    def test_validate_docker_image_with_platform_conflict(self):
        """Test validation detects docker-image and platform conflict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "pyproject.toml").touch()

            with pytest.raises(Exception):  # click.BadParameter
                validate_build_options(
                    source=str(project_dir),
                    output_dir="dist",
                    python="3.12",
                    isolation="docker",
                    docker_image="quay.io/pypa/manylinux_2_28_x86_64",
                    platform="manylinux",
                )

    def test_validate_invalid_python_version(self):
        """Test validation rejects invalid Python versions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / "pyproject.toml").touch()

            with pytest.raises(Exception):  # click.BadParameter
                validate_build_options(
                    source=str(project_dir),
                    output_dir="dist",
                    python="invalid",
                    isolation="venv",
                    docker_image=None,
                    platform="auto",
                )


class TestConfigSettingsParsing:
    """Test config settings parsing."""

    def test_parse_single_setting(self):
        """Test parsing single config setting."""
        result = _parse_config_settings(("key=value",))
        assert result == [("key", "value")]

    def test_parse_multiple_settings(self):
        """Test parsing multiple config settings."""
        result = _parse_config_settings(("key1=value1", "key2=value2"))
        assert result == [("key1", "value1"), ("key2", "value2")]

    def test_parse_setting_with_equals_in_value(self):
        """Test parsing setting with equals sign in value."""
        result = _parse_config_settings(("key=value=with=equals",))
        assert result == [("key", "value=with=equals")]

    def test_parse_invalid_setting(self):
        """Test that invalid settings raise error."""
        with pytest.raises(Exception):  # click.BadParameter
            _parse_config_settings(("no_equals",))

    def test_parse_empty_settings(self):
        """Test parsing with no settings."""
        result = _parse_config_settings(())
        assert result == []


class TestCLIIntegration:
    """Integration tests for CLI."""

    def test_version_command(self):
        """Test version command."""
        runner = CliRunner()
        result = runner.invoke(cli, ["version"])
        assert result.exit_code == 0
        assert "Headless Wheel Builder" in result.output

    def test_cli_help(self):
        """Test CLI help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "build" in result.output
        assert "inspect" in result.output
        assert "version" in result.output

    def test_build_help(self):
        """Test build command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["build", "--help"])
        assert result.exit_code == 0
        assert "--python" in result.output
        assert "--isolation" in result.output

    def test_inspect_help(self):
        """Test inspect command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["inspect", "--help"])
        assert result.exit_code == 0
        assert "--format" in result.output
        assert "--check" in result.output

    def test_images_list_command(self):
        """Test images list command."""
        runner = CliRunner()
        result = runner.invoke(cli, ["images"])
        assert result.exit_code == 0
        assert "manylinux" in result.output or "Available" in result.output

    def test_version_next_command(self):
        """Test version-next command."""
        runner = CliRunner()
        result = runner.invoke(cli, ["version-next", "1.0.0"])
        assert result.exit_code == 0
        assert "1.0.1" in result.output

    def test_version_next_major(self):
        """Test version-next with major increment."""
        runner = CliRunner()
        result = runner.invoke(cli, ["version-next", "1.2.3", "--part", "major"])
        assert result.exit_code == 0
        assert "2.0.0" in result.output

    def test_version_next_invalid(self):
        """Test version-next with invalid version."""
        runner = CliRunner()
        result = runner.invoke(cli, ["version-next", "invalid"])
        assert result.exit_code != 0

    def test_cli_verbose_flag(self):
        """Test CLI verbose flag."""
        runner = CliRunner()
        result = runner.invoke(cli, ["-v", "version"])
        assert result.exit_code == 0

    def test_cli_quiet_flag(self):
        """Test CLI quiet flag."""
        runner = CliRunner()
        result = runner.invoke(cli, ["-q", "version"])
        assert result.exit_code == 0

    def test_cli_json_flag(self):
        """Test CLI JSON flag."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--json", "version"])
        # JSON flag doesn't affect version command but should not error
        assert result.exit_code == 0

    def test_cli_no_color_flag(self):
        """Test CLI no-color flag."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--no-color", "version"])
        assert result.exit_code == 0
