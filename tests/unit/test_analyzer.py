"""Tests for project analyzer."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from headless_wheel_builder.core.analyzer import ProjectAnalyzer, ProjectMetadata
from headless_wheel_builder.exceptions import ProjectError

if TYPE_CHECKING:
    from pathlib import Path


class TestProjectAnalyzer:
    """Tests for ProjectAnalyzer."""

    @pytest.mark.asyncio
    async def test_analyze_pyproject(self, sample_project: Path) -> None:
        """Test analyzing a pyproject.toml project."""
        analyzer = ProjectAnalyzer()
        metadata = await analyzer.analyze(sample_project)

        assert metadata.name == "sample-package"
        assert metadata.version == "1.0.0"
        assert metadata.requires_python == ">=3.10"
        assert metadata.has_pyproject is True
        assert metadata.has_setup_py is False

    @pytest.mark.asyncio
    async def test_analyze_backend_detection(self, sample_project: Path) -> None:
        """Test build backend detection."""
        analyzer = ProjectAnalyzer()
        metadata = await analyzer.analyze(sample_project)

        assert metadata.backend is not None
        assert metadata.backend.name == "hatchling"
        assert metadata.backend.module == "hatchling.build"
        assert "hatchling>=1.26" in metadata.backend.requirements

    @pytest.mark.asyncio
    async def test_analyze_dependencies(self, sample_project: Path) -> None:
        """Test dependency extraction."""
        analyzer = ProjectAnalyzer()
        metadata = await analyzer.analyze(sample_project)

        assert "click>=8.0" in metadata.dependencies
        assert "rich>=13.0" in metadata.dependencies
        assert "dev" in metadata.optional_dependencies
        assert "pytest>=8.0" in metadata.optional_dependencies["dev"]

    @pytest.mark.asyncio
    async def test_analyze_setuptools_project(self, sample_setuptools_project: Path) -> None:
        """Test analyzing a setuptools project."""
        analyzer = ProjectAnalyzer()
        metadata = await analyzer.analyze(sample_setuptools_project)

        assert metadata.name == "setuptools-project"
        assert metadata.version == "0.1.0"
        assert metadata.backend is not None
        assert metadata.backend.name == "setuptools"

    @pytest.mark.asyncio
    async def test_analyze_legacy_project(self, sample_legacy_project: Path) -> None:
        """Test analyzing a legacy setup.py project."""
        analyzer = ProjectAnalyzer()
        metadata = await analyzer.analyze(sample_legacy_project)

        # Should fall back to setuptools
        assert metadata.backend is not None
        assert metadata.backend.name == "setuptools"
        assert metadata.has_setup_py is True
        assert metadata.has_pyproject is False

    @pytest.mark.asyncio
    async def test_analyze_extension_project(self, sample_extension_project: Path) -> None:
        """Test analyzing a project with C extensions."""
        analyzer = ProjectAnalyzer()
        metadata = await analyzer.analyze(sample_extension_project)

        assert metadata.has_extension_modules is True
        assert "c" in metadata.extension_languages

    @pytest.mark.asyncio
    async def test_analyze_pure_python(self, sample_project: Path) -> None:
        """Test that pure Python project has no extensions."""
        analyzer = ProjectAnalyzer()
        metadata = await analyzer.analyze(sample_project)

        assert metadata.is_pure_python is True
        assert metadata.has_extension_modules is False

    @pytest.mark.asyncio
    async def test_analyze_missing_project(self, tmp_path: Path) -> None:
        """Test analyzing a nonexistent directory."""
        analyzer = ProjectAnalyzer()
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(ProjectError, match="does not exist"):
            await analyzer.analyze(nonexistent)

    @pytest.mark.asyncio
    async def test_analyze_empty_directory(self, empty_dir: Path) -> None:
        """Test analyzing an empty directory."""
        analyzer = ProjectAnalyzer()

        with pytest.raises(ProjectError, match="No pyproject.toml or setup.py"):
            await analyzer.analyze(empty_dir)

    @pytest.mark.asyncio
    async def test_analyze_invalid_pyproject(self, tmp_path: Path) -> None:
        """Test analyzing an invalid pyproject.toml."""
        project_dir = tmp_path / "invalid"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").write_text("invalid toml content [[[")

        analyzer = ProjectAnalyzer()

        with pytest.raises(ProjectError, match="Invalid pyproject.toml"):
            await analyzer.analyze(project_dir)


class TestProjectMetadata:
    """Tests for ProjectMetadata."""

    def test_is_pure_python(self) -> None:
        """Test is_pure_python property."""
        metadata = ProjectMetadata(
            name="test",
            version="1.0.0",
            has_extension_modules=False,
        )
        assert metadata.is_pure_python is True

        metadata.has_extension_modules = True
        assert metadata.is_pure_python is False

    def test_build_requirements(self) -> None:
        """Test build_requirements property."""
        from headless_wheel_builder.core.analyzer import BuildBackend

        metadata = ProjectMetadata(
            name="test",
            version="1.0.0",
            backend=BuildBackend(
                module="hatchling.build",
                requirements=["hatchling>=1.26"],
            ),
        )
        assert metadata.build_requirements == ["hatchling>=1.26"]

    def test_build_requirements_default(self) -> None:
        """Test default build requirements without backend."""
        metadata = ProjectMetadata(
            name="test",
            version="1.0.0",
            backend=None,
        )
        # Should return setuptools defaults
        assert "setuptools>=61.0" in metadata.build_requirements


class TestBuildBackend:
    """Tests for BuildBackend."""

    def test_backend_name_detection(self) -> None:
        """Test build backend name detection."""
        from headless_wheel_builder.core.analyzer import BuildBackend

        test_cases = [
            ("hatchling.build", "hatchling"),
            ("setuptools.build_meta", "setuptools"),
            ("flit_core.buildapi", "flit"),
            ("pdm.backend", "pdm"),
            ("maturin", "maturin"),
            ("poetry.core.masonry.api", "poetry"),
            ("custom.backend", "custom"),
        ]

        for module, expected_name in test_cases:
            backend = BuildBackend(module=module, requirements=[])
            assert backend.name == expected_name, f"Expected {expected_name} for {module}"
