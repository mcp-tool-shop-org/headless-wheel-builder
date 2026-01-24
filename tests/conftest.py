"""Pytest fixtures for Headless Wheel Builder tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path
    pass


@pytest.fixture
def sample_pyproject_content() -> str:
    """Sample pyproject.toml content."""
    return """
[build-system]
requires = ["hatchling>=1.26"]
build-backend = "hatchling.build"

[project]
name = "sample-package"
version = "1.0.0"
description = "A sample package for testing"
requires-python = ">=3.10"
dependencies = [
    "click>=8.0",
    "rich>=13.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]
"""


@pytest.fixture
def sample_project(tmp_path: Path, sample_pyproject_content: str) -> Path:
    """Create a sample Python project for testing."""
    project_dir = tmp_path / "sample-package"
    project_dir.mkdir()

    # pyproject.toml
    (project_dir / "pyproject.toml").write_text(sample_pyproject_content)

    # Source files
    src_dir = project_dir / "src" / "sample_package"
    src_dir.mkdir(parents=True)
    (src_dir / "__init__.py").write_text('__version__ = "1.0.0"\n')
    (src_dir / "main.py").write_text('def hello():\n    return "Hello, World!"\n')

    # README
    (project_dir / "README.md").write_text("# Sample Package\n\nA sample package.\n")

    return project_dir


@pytest.fixture
def sample_setuptools_project(tmp_path: Path) -> Path:
    """Create a sample project using setuptools."""
    project_dir = tmp_path / "setuptools-project"
    project_dir.mkdir()

    # pyproject.toml with setuptools
    pyproject = """
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "setuptools-project"
version = "0.1.0"
description = "A setuptools project"
"""
    (project_dir / "pyproject.toml").write_text(pyproject)

    # Source files
    pkg_dir = project_dir / "setuptools_project"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text('__version__ = "0.1.0"\n')

    return project_dir


@pytest.fixture
def sample_legacy_project(tmp_path: Path) -> Path:
    """Create a legacy project with only setup.py."""
    project_dir = tmp_path / "legacy-project"
    project_dir.mkdir()

    # setup.py only
    setup_py = """
from setuptools import setup, find_packages

setup(
    name="legacy-project",
    version="0.1.0",
    packages=find_packages(),
)
"""
    (project_dir / "setup.py").write_text(setup_py)

    # Source files
    pkg_dir = project_dir / "legacy_project"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text('__version__ = "0.1.0"\n')

    return project_dir


@pytest.fixture
def sample_extension_project(tmp_path: Path) -> Path:
    """Create a project with C extension."""
    project_dir = tmp_path / "extension-project"
    project_dir.mkdir()

    # pyproject.toml
    pyproject = """
[build-system]
requires = ["setuptools>=61.0", "wheel", "cython"]
build-backend = "setuptools.build_meta"

[project]
name = "extension-project"
version = "0.1.0"
"""
    (project_dir / "pyproject.toml").write_text(pyproject)

    # C source file
    (project_dir / "extension.c").write_text("// Dummy C file\n")

    # Python package
    pkg_dir = project_dir / "extension_project"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")

    return project_dir


@pytest.fixture
def empty_dir(tmp_path: Path) -> Path:
    """Create an empty directory."""
    empty = tmp_path / "empty"
    empty.mkdir()
    return empty
