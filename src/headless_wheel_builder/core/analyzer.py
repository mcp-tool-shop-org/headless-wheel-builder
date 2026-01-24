"""Project analysis - extracts metadata and build configuration from Python projects."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from headless_wheel_builder.exceptions import ProjectError

# tomllib is stdlib in 3.11+
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass
class BuildBackend:
    """Build backend specification."""

    module: str  # e.g., "hatchling.build"
    requirements: list[str]  # e.g., ["hatchling>=1.26"]

    @property
    def name(self) -> str:
        """Get friendly name of backend."""
        module_lower = self.module.lower()
        if "hatchling" in module_lower:
            return "hatchling"
        if "setuptools" in module_lower:
            return "setuptools"
        if "flit" in module_lower:
            return "flit"
        if "pdm" in module_lower:
            return "pdm"
        if "maturin" in module_lower:
            return "maturin"
        if "poetry" in module_lower:
            return "poetry"
        return self.module.split(".")[0]


@dataclass
class ProjectMetadata:
    """Extracted project metadata."""

    name: str
    version: str | None
    requires_python: str | None = None
    dependencies: list[str] = field(default_factory=list)
    optional_dependencies: dict[str, list[str]] = field(default_factory=dict)

    # Build info
    backend: BuildBackend | None = None
    has_pyproject: bool = False
    has_setup_py: bool = False
    has_setup_cfg: bool = False

    # Extension modules
    has_extension_modules: bool = False
    extension_languages: list[str] = field(default_factory=list)

    # Source paths
    source_path: Path | None = None

    @property
    def is_pure_python(self) -> bool:
        """Check if package is pure Python (no extensions)."""
        return not self.has_extension_modules

    @property
    def build_requirements(self) -> list[str]:
        """Get build requirements."""
        if self.backend:
            return self.backend.requirements
        return ["setuptools>=61.0", "wheel"]


# Default build backend per PEP 517
DEFAULT_BACKEND = BuildBackend(
    module="setuptools.build_meta",
    requirements=["setuptools>=61.0", "wheel"],
)


class ProjectAnalyzer:
    """
    Analyzes Python projects to extract build information.

    Handles:
    - pyproject.toml parsing (PEP 621)
    - setup.py/setup.cfg fallback detection
    - Build backend identification
    - Extension module detection
    """

    async def analyze(self, source_path: Path) -> ProjectMetadata:
        """
        Analyze a project and extract metadata.

        Args:
            source_path: Path to project root

        Returns:
            ProjectMetadata with extracted information

        Raises:
            ProjectError: If project cannot be analyzed
        """
        source_path = Path(source_path)

        if not source_path.exists():
            raise ProjectError(f"Source path does not exist: {source_path}")

        if not source_path.is_dir():
            raise ProjectError(f"Source path is not a directory: {source_path}")

        pyproject_path = source_path / "pyproject.toml"
        setup_py_path = source_path / "setup.py"
        setup_cfg_path = source_path / "setup.cfg"

        metadata = ProjectMetadata(
            name="",
            version=None,
            has_pyproject=pyproject_path.exists(),
            has_setup_py=setup_py_path.exists(),
            has_setup_cfg=setup_cfg_path.exists(),
            source_path=source_path,
        )

        # Must have at least one config file
        if not metadata.has_pyproject and not metadata.has_setup_py:
            raise ProjectError(f"No pyproject.toml or setup.py found in: {source_path}")

        # Parse pyproject.toml if present
        if metadata.has_pyproject:
            self._parse_pyproject(pyproject_path, metadata)
        else:
            # Fallback to default setuptools for setup.py-only projects
            metadata.backend = DEFAULT_BACKEND

        # Try to extract name/version from setup.py/setup.cfg if not in pyproject.toml
        if not metadata.name and metadata.has_setup_cfg:
            self._parse_setup_cfg(setup_cfg_path, metadata)

        if not metadata.name:
            # Fall back to directory name
            metadata.name = source_path.name

        # Detect extension modules
        self._detect_extensions(source_path, metadata)

        return metadata

    def _parse_pyproject(self, path: Path, metadata: ProjectMetadata) -> None:
        """Parse pyproject.toml for metadata."""
        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ProjectError(f"Invalid pyproject.toml: {e}") from e

        # Build system (PEP 518)
        build_system = data.get("build-system", {})
        if build_system:
            backend_module = build_system.get("build-backend", "setuptools.build_meta")
            requirements = build_system.get("requires", ["setuptools", "wheel"])

            metadata.backend = BuildBackend(
                module=backend_module,
                requirements=requirements,
            )
        else:
            # No build-system = legacy setuptools
            metadata.backend = DEFAULT_BACKEND

        # Project metadata (PEP 621)
        project = data.get("project", {})
        metadata.name = project.get("name", "")
        metadata.requires_python = project.get("requires-python")
        metadata.dependencies = project.get("dependencies", [])
        metadata.optional_dependencies = project.get("optional-dependencies", {})

        # Version handling
        if "version" in project:
            metadata.version = project["version"]
        elif "version" in project.get("dynamic", []):
            # Version will be determined at build time
            metadata.version = None
        else:
            metadata.version = None

        # Check for tool-specific version configuration
        if metadata.version is None:
            metadata.version = self._get_dynamic_version(data)

    def _get_dynamic_version(self, data: dict[str, Any]) -> str | None:
        """Try to extract dynamic version from tool configuration."""
        # Check hatch/hatchling
        tool = data.get("tool", {})

        # Hatch version from file
        hatch_version = tool.get("hatch", {}).get("version", {})
        if "path" in hatch_version:
            # Could read from file, but that's build-time
            return None

        # setuptools_scm
        if "setuptools_scm" in tool:
            # Version comes from git
            return None

        return None

    def _parse_setup_cfg(self, path: Path, metadata: ProjectMetadata) -> None:
        """Parse setup.cfg for metadata."""
        import configparser

        config = configparser.ConfigParser()
        try:
            config.read(path)
        except configparser.Error:
            return

        if "metadata" in config:
            meta = config["metadata"]
            if not metadata.name and "name" in meta:
                metadata.name = meta["name"]
            if not metadata.version and "version" in meta:
                metadata.version = meta["version"]

    def _detect_extensions(self, source_path: Path, metadata: ProjectMetadata) -> None:
        """Detect if project has extension modules."""
        # Patterns that indicate extension modules
        extension_patterns = {
            "c": ["*.c"],
            "cpp": ["*.cpp", "*.cxx", "*.cc"],
            "cython": ["*.pyx"],
            "rust": ["Cargo.toml"],
        }

        languages_found: set[str] = set()

        for lang, patterns in extension_patterns.items():
            for pattern in patterns:
                # Check in src/ and root
                matches = list(source_path.rglob(pattern))
                # Filter out common non-extension C files
                matches = [
                    m
                    for m in matches
                    if not any(
                        part in str(m)
                        for part in ["venv", ".venv", "site-packages", "__pycache__", ".git"]
                    )
                ]
                if matches:
                    languages_found.add(lang)
                    break

        # Check for Cython in pyproject.toml build requirements
        if metadata.backend:
            for req in metadata.backend.requirements:
                if "cython" in req.lower():
                    languages_found.add("cython")
                    break

        # Check for maturin (Rust)
        if metadata.backend and "maturin" in metadata.backend.module:
            languages_found.add("rust")

        metadata.has_extension_modules = len(languages_found) > 0
        metadata.extension_languages = sorted(languages_found)

    def get_wheel_tags(self, metadata: ProjectMetadata) -> dict[str, str]:
        """
        Determine appropriate wheel tags for a project.

        Args:
            metadata: Project metadata

        Returns:
            Dict with python_tag, abi_tag, platform_tag
        """
        if metadata.is_pure_python:
            return {
                "python_tag": "py3",
                "abi_tag": "none",
                "platform_tag": "any",
            }

        # For extension modules, tags are determined at build time
        return {
            "python_tag": "cp312",  # Will be set based on interpreter
            "abi_tag": "cp312",
            "platform_tag": "linux_x86_64",  # Will be set based on platform
        }
