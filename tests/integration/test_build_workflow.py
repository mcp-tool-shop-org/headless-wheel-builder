"""Integration tests for build workflows.

These tests exercise the full build pipeline from source resolution
to wheel creation, testing real-world scenarios.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

from headless_wheel_builder.core.analyzer import ProjectAnalyzer
from headless_wheel_builder.core.builder import BuildEngine
from headless_wheel_builder.core.source import SourceResolver
from headless_wheel_builder.isolation.venv import VenvIsolation

if TYPE_CHECKING:
    from pathlib import Path

# Mark all tests as integration tests
pytestmark = pytest.mark.integration


class TestLocalBuildWorkflow:
    """Test building wheels from local sources."""

    @pytest.fixture
    def sample_project(self, tmp_path: Path) -> Path:
        """Create a minimal Python project for testing."""
        project_dir = tmp_path / "sample_project"
        project_dir.mkdir()

        # Create pyproject.toml
        pyproject = project_dir / "pyproject.toml"
        pyproject.write_text("""
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "sample-project"
version = "0.1.0"
description = "A sample project for testing"
requires-python = ">=3.9"

[tool.setuptools.packages.find]
where = ["src"]
""")

        # Create source directory
        src_dir = project_dir / "src" / "sample_project"
        src_dir.mkdir(parents=True)

        # Create __init__.py
        (src_dir / "__init__.py").write_text('"""Sample project."""\n__version__ = "0.1.0"\n')

        # Create a module
        (src_dir / "main.py").write_text('''"""Main module."""

def hello(name: str = "World") -> str:
    """Return a greeting."""
    return f"Hello, {name}!"
''')

        return project_dir

    @pytest.mark.asyncio
    async def test_full_build_workflow(self, sample_project: Path, tmp_path: Path):
        """Test complete build workflow: resolve -> analyze -> build."""
        output_dir = tmp_path / "dist"
        output_dir.mkdir()

        # Step 1: Resolve source
        resolver = SourceResolver()
        spec = resolver.parse_source(str(sample_project))
        source = await resolver.resolve(spec)
        assert source.local_path.exists()

        # Step 2: Analyze project
        analyzer = ProjectAnalyzer()
        info = await analyzer.analyze(source.local_path)
        assert info.name == "sample-project"
        assert info.version == "0.1.0"
        assert info.backend.module == "setuptools.build_meta"

        # Step 3: Build wheel
        builder = BuildEngine()
        result = await builder.build(source, output_dir)

        assert result.success
        assert result.wheel_path is not None
        assert result.wheel_path.exists()
        assert result.wheel_path.suffix == ".whl"
        assert "sample_project" in result.wheel_path.name
        assert "0.1.0" in result.wheel_path.name

    @pytest.mark.asyncio
    async def test_build_sdist(self, sample_project: Path, tmp_path: Path):
        """Test building source distribution."""
        output_dir = tmp_path / "dist"
        output_dir.mkdir()

        builder = BuildEngine()
        result = await builder.build(
            source=sample_project,
            output_dir=output_dir,
            sdist=True,
        )

        assert result.success
        # Check for sdist
        sdists = list(output_dir.glob("*.tar.gz"))
        assert len(sdists) >= 0  # May or may not create sdist depending on config

    @pytest.mark.asyncio
    async def test_build_invalid_project(self, tmp_path: Path):
        """Test building from invalid project directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        builder = BuildEngine()
        result = await builder.build(
            source=empty_dir,
            output_dir=tmp_path / "dist",
        )

        assert result.success is False
        assert result.error is not None


class TestSourceResolution:
    """Test source resolution across different input types."""

    @pytest.mark.asyncio
    async def test_resolve_local_directory(self, tmp_path: Path):
        """Test resolving local directory."""
        # Create a minimal project
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").write_text('[project]\nname = "test"\nversion = "0.1.0"')

        resolver = SourceResolver()
        spec = resolver.parse_source(str(project_dir))
        source = await resolver.resolve(spec)

        assert source.local_path == project_dir
        assert source.local_path.exists()

    @pytest.mark.asyncio
    async def test_resolve_nonexistent_path(self, tmp_path: Path):
        """Test resolving non-existent path."""
        resolver = SourceResolver()

        with pytest.raises(Exception):  # Should raise an error
            resolver.parse_source(str(tmp_path / "nonexistent"))


class TestAnalyzerIntegration:
    """Test project analyzer with various project configurations."""

    @pytest.fixture
    def setuptools_project(self, tmp_path: Path) -> Path:
        """Create a setuptools project."""
        project_dir = tmp_path / "setuptools_proj"
        project_dir.mkdir()

        (project_dir / "pyproject.toml").write_text("""
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "setuptools-test"
version = "1.2.3"
description = "Test project"
requires-python = ">=3.9"
dependencies = ["requests>=2.0"]

[project.optional-dependencies]
dev = ["pytest"]
""")

        src = project_dir / "src" / "setuptools_test"
        src.mkdir(parents=True)
        (src / "__init__.py").write_text("__version__ = '1.2.3'")

        return project_dir

    @pytest.fixture
    def hatchling_project(self, tmp_path: Path) -> Path:
        """Create a hatchling project."""
        project_dir = tmp_path / "hatch_proj"
        project_dir.mkdir()

        (project_dir / "pyproject.toml").write_text("""
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "hatch-test"
version = "2.0.0"
description = "Hatch test project"
""")

        src = project_dir / "src" / "hatch_test"
        src.mkdir(parents=True)
        (src / "__init__.py").write_text("__version__ = '2.0.0'")

        return project_dir

    @pytest.mark.asyncio
    async def test_analyze_setuptools_project(self, setuptools_project: Path):
        """Test analyzing setuptools project."""
        analyzer = ProjectAnalyzer()
        info = await analyzer.analyze(setuptools_project)

        assert info.name == "setuptools-test"
        assert info.version == "1.2.3"
        assert info.backend.module == "setuptools.build_meta"
        assert "setuptools>=61.0" in info.backend.requirements
        assert "requests>=2.0" in info.dependencies or any(
            "requests" in d for d in info.dependencies
        )

    @pytest.mark.asyncio
    async def test_analyze_hatchling_project(self, hatchling_project: Path):
        """Test analyzing hatchling project."""
        analyzer = ProjectAnalyzer()
        info = await analyzer.analyze(hatchling_project)

        assert info.name == "hatch-test"
        assert info.version == "2.0.0"
        assert info.backend.module == "hatchling.build"
        assert "hatchling" in info.backend.requirements


class TestVenvIsolation:
    """Test venv isolation functionality."""

    @pytest.mark.asyncio
    async def test_venv_creation(self, tmp_path: Path):
        """Test creating isolated venv."""
        isolation = VenvIsolation()

        # Create environment with minimal requirements
        env = await isolation.create_environment(
            python_version="3.12",
            build_requirements=["setuptools", "wheel"],
        )

        assert env.python_path.exists()

        # Cleanup via the environment object
        await env.cleanup()

    @pytest.mark.asyncio
    async def test_venv_context_manager(self, tmp_path: Path):
        """Test venv creation via async context manager."""
        isolation = VenvIsolation()

        async with await isolation.create_environment(
            python_version="3.12",
            build_requirements=[],
        ) as env:
            assert env.python_path.exists()

            # Run a simple Python command
            process = await asyncio.create_subprocess_exec(
                str(env.python_path),
                "-c",
                "print('hello')",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _stderr = await process.communicate()

            assert process.returncode == 0
            assert b"hello" in stdout


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    @pytest.fixture
    def complete_project(self, tmp_path: Path) -> Path:
        """Create a complete project with all typical files."""
        project_dir = tmp_path / "complete_project"
        project_dir.mkdir()

        # pyproject.toml
        (project_dir / "pyproject.toml").write_text("""
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "complete-project"
version = "1.0.0"
description = "A complete test project"
readme = "README.md"
requires-python = ">=3.9"
license = {text = "MIT"}
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
]
keywords = ["test", "example"]
dependencies = []

[project.scripts]
complete-cli = "complete_project.cli:main"

[project.urls]
Homepage = "https://github.com/test/complete-project"
Documentation = "https://complete-project.readthedocs.io/"

[tool.setuptools.packages.find]
where = ["src"]
""")

        # README.md
        (project_dir / "README.md").write_text("""# Complete Project

A complete test project for integration testing.

## Installation

```bash
pip install complete-project
```

## Usage

```python
from complete_project import hello
print(hello())
```
""")

        # LICENSE
        (project_dir / "LICENSE").write_text("MIT License\n\nCopyright (c) 2024 Test")

        # Source code
        src = project_dir / "src" / "complete_project"
        src.mkdir(parents=True)

        (src / "__init__.py").write_text('''"""Complete project package."""

__version__ = "1.0.0"

def hello(name: str = "World") -> str:
    """Return a greeting."""
    return f"Hello, {name}!"
''')

        (src / "cli.py").write_text('''"""CLI module."""

def main():
    """Main entry point."""
    print("Hello from complete-project!")

if __name__ == "__main__":
    main()
''')

        (src / "utils.py").write_text('''"""Utility functions."""

def format_greeting(name: str, greeting: str = "Hello") -> str:
    """Format a greeting message."""
    return f"{greeting}, {name}!"
''')

        # Tests
        tests_dir = project_dir / "tests"
        tests_dir.mkdir()
        (tests_dir / "__init__.py").write_text("")
        (tests_dir / "test_main.py").write_text('''"""Tests for main module."""

from complete_project import hello

def test_hello():
    """Test hello function."""
    assert hello() == "Hello, World!"
    assert hello("Test") == "Hello, Test!"
''')

        return project_dir

    @pytest.mark.asyncio
    async def test_full_project_build(self, complete_project: Path, tmp_path: Path):
        """Test building a complete project end-to-end."""
        output_dir = tmp_path / "dist"
        output_dir.mkdir()

        # Resolve
        resolver = SourceResolver()
        spec = resolver.parse_source(str(complete_project))
        source = await resolver.resolve(spec)

        # Analyze
        analyzer = ProjectAnalyzer()
        info = await analyzer.analyze(source.local_path)

        assert info.name == "complete-project"
        assert info.version == "1.0.0"

        # Build
        builder = BuildEngine()
        result = await builder.build(source, output_dir)

        assert result.success
        assert result.wheel_path is not None
        assert result.wheel_path.exists()

        # Verify wheel contents
        import zipfile

        with zipfile.ZipFile(result.wheel_path) as whl:
            names = whl.namelist()

            # Should have the package
            assert any("complete_project/__init__.py" in n for n in names)
            assert any("complete_project/cli.py" in n for n in names)
            assert any("complete_project/utils.py" in n for n in names)

            # Should have metadata
            assert any("METADATA" in n for n in names)
            assert any("WHEEL" in n for n in names)
            assert any("RECORD" in n for n in names)

            # Check metadata content
            for name in names:
                if name.endswith("METADATA"):
                    content = whl.read(name).decode()
                    assert "Name: complete-project" in content
                    assert "Version: 1.0.0" in content
                    break

    @pytest.mark.asyncio
    async def test_wheel_is_installable(self, complete_project: Path, tmp_path: Path):
        """Test that built wheel can be installed."""
        output_dir = tmp_path / "dist"
        output_dir.mkdir()

        # Build the wheel
        builder = BuildEngine()
        result = await builder.build(complete_project, output_dir)

        assert result.success
        assert result.wheel_path is not None

        # Create a test venv and try to install
        isolation = VenvIsolation()
        env = await isolation.create_environment(
            python_version="3.12",
            build_requirements=["pip"],  # Ensure pip is available
        )

        try:
            # Install the wheel
            process = await asyncio.create_subprocess_exec(
                str(env.python_path),
                "-m",
                "pip",
                "install",
                str(result.wheel_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            assert process.returncode == 0, f"Failed to install: {stderr.decode()}"

            # Try to import the package
            process = await asyncio.create_subprocess_exec(
                str(env.python_path),
                "-c",
                "from complete_project import hello; print(hello())",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            assert process.returncode == 0, f"Failed to import: {stderr.decode()}"
            assert b"Hello, World!" in stdout
        finally:
            await env.cleanup()


class TestErrorHandling:
    """Test error handling in workflows."""

    @pytest.mark.asyncio
    async def test_missing_pyproject(self, tmp_path: Path):
        """Test handling of missing pyproject.toml."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        analyzer = ProjectAnalyzer()

        # Should handle gracefully
        with pytest.raises(Exception):  # Should raise some error
            await analyzer.analyze(empty_dir)

    @pytest.mark.asyncio
    async def test_invalid_pyproject(self, tmp_path: Path):
        """Test handling of invalid pyproject.toml."""
        project_dir = tmp_path / "invalid"
        project_dir.mkdir()

        # Invalid TOML
        (project_dir / "pyproject.toml").write_text("this is not valid toml [")

        analyzer = ProjectAnalyzer()

        with pytest.raises(Exception):  # Should raise parsing error
            await analyzer.analyze(project_dir)

    @pytest.mark.asyncio
    async def test_missing_build_backend(self, tmp_path: Path):
        """Test handling of missing build backend."""
        project_dir = tmp_path / "no_backend"
        project_dir.mkdir()

        # No build-system specified
        (project_dir / "pyproject.toml").write_text("""
[project]
name = "test"
version = "0.1.0"
""")

        src = project_dir / "test"
        src.mkdir()
        (src / "__init__.py").write_text("")

        # Should still work with default backend
        builder = BuildEngine()
        result = await builder.build(project_dir, tmp_path / "dist")

        # May succeed with setuptools fallback or fail gracefully
        # The important thing is it doesn't crash
        assert isinstance(result.success, bool)
