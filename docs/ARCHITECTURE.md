# Headless Wheel Builder - Architecture Documentation

> **Purpose**: Deep technical documentation of system architecture, component interactions, and design decisions.
> **Last Updated**: 2026-01-23

---

## 2026 Best Practices Applied

> **Sources**: [PEP 517 Build Interface](https://peps.python.org/pep-0517/), [PEP 518 Build Dependencies](https://peps.python.org/pep-0518/), [PEP 621 Project Metadata](https://peps.python.org/pep-0621/), [uv Documentation](https://docs.astral.sh/uv/), [Python Packaging User Guide](https://packaging.python.org/en/latest/), [manylinux Project](https://github.com/pypa/manylinux), [Hatchling Build Backend](https://hatch.pypa.io/latest/)

This architecture follows 2026 Python packaging best practices:

1. **PEP 517 Build Frontend**: Acts as a standards-compliant build frontend, invoking any PEP 517-compliant backend (hatchling, setuptools, flit, pdm, maturin).

2. **Build Isolation by Default**: Every build runs in an isolated environment. No assumptions about host packages.

3. **uv-First, pip-Fallback**: Use uv for 10-100x faster dependency resolution when available. Graceful fallback to pip.

4. **Pluggable Isolation**: Users choose venv (fast, lightweight) or Docker (reproducible, cross-platform). Architecture supports adding more strategies.

5. **Registry-Agnostic Publishing**: Abstract registry interface supports PyPI, private registries, and S3-compatible storage.

6. **OIDC-First Authentication**: Prefer Trusted Publishers (short-lived tokens) over long-lived API keys where supported.

7. **Async Throughout**: Core operations are async for parallel builds and non-blocking I/O.

8. **Windows-Native**: First-class Windows support using pathlib, subprocess with proper quoting, no shell=True.

---

## System Overview

The Headless Wheel Builder (HWB) is a CLI tool and Python library for building, versioning, and publishing Python wheels in automated environments.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              User Interface                                  │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐ │
│  │     CLI (click)     │  │   Python API        │  │   CI/CD Helpers     │ │
│  │  hwb build/publish  │  │   hwb.build()       │  │   GH Action/GitLab  │ │
│  └──────────┬──────────┘  └──────────┬──────────┘  └──────────┬──────────┘ │
└─────────────┼────────────────────────┼────────────────────────┼─────────────┘
              │                        │                        │
              └────────────────────────┼────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Orchestration Layer                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         Build Coordinator                            │   │
│  │   • Source acquisition    • Build matrix expansion                   │   │
│  │   • Isolation selection   • Parallel execution                       │   │
│  └──────────────────────────────────┬──────────────────────────────────┘   │
└─────────────────────────────────────┼───────────────────────────────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Core Services                                   │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌─────────────┐  │
│  │    Source     │  │   Project     │  │    Build      │  │  Artifact   │  │
│  │   Resolver    │  │   Analyzer    │  │   Engine      │  │  Manager    │  │
│  │               │  │               │  │               │  │             │  │
│  │ • Git clone   │  │ • pyproject   │  │ • PEP 517     │  │ • Wheel     │  │
│  │ • Local path  │  │ • setup.py    │  │ • Build deps  │  │   validation│  │
│  │ • URL fetch   │  │ • Metadata    │  │ • Execution   │  │ • Checksums │  │
│  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘  └──────┬──────┘  │
└──────────┼──────────────────┼──────────────────┼─────────────────┼──────────┘
           │                  │                  │                 │
           └──────────────────┼──────────────────┘                 │
                              ▼                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Isolation Layer                                    │
│  ┌───────────────────────────────┐  ┌───────────────────────────────────┐  │
│  │      VirtualEnv Strategy      │  │        Docker Strategy            │  │
│  │                               │  │                                   │  │
│  │  • venv/virtualenv creation   │  │  • manylinux images               │  │
│  │  • uv/pip dependency install  │  │  • musllinux images               │  │
│  │  • Python version selection   │  │  • Custom Dockerfile              │  │
│  │  • Environment cleanup        │  │  • Volume mounting                │  │
│  └───────────────────────────────┘  └───────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                              │                                    │
                              └──────────────────┬─────────────────┘
                                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Publishing Layer                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐│
│  │    PyPI     │  │   DevPi     │  │ Artifactory │  │  S3/Object Store    ││
│  │  (Trusted   │  │             │  │             │  │  (PEP 503 index)    ││
│  │  Publishers)│  │             │  │             │  │                     ││
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Version Management                                 │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────────┐   │
│  │  Commit Parser    │  │  Version Bumper   │  │  Changelog Generator  │   │
│  │  (Conventional)   │  │  (SemVer/CalVer)  │  │  (Keep a Changelog)   │   │
│  └───────────────────┘  └───────────────────┘  └───────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Deep Dive

### 1. Source Resolver

**File**: `src/headless_wheel_builder/core/source.py`

Handles acquisition of source code from various locations.

```python
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional
import asyncio

class SourceType(Enum):
    """Types of source locations."""
    LOCAL_PATH = "local_path"       # /path/to/project
    GIT_HTTPS = "git_https"         # https://github.com/user/repo
    GIT_SSH = "git_ssh"             # git@github.com:user/repo
    TARBALL = "tarball"             # https://example.com/pkg.tar.gz
    SDIST = "sdist"                 # package-1.0.0.tar.gz


@dataclass
class SourceSpec:
    """Specification for a source location."""
    type: SourceType
    location: str
    ref: Optional[str] = None       # Git branch/tag/commit
    subdirectory: Optional[str] = None  # For monorepos
    editable: bool = False


@dataclass
class ResolvedSource:
    """A source that has been resolved to a local path."""
    spec: SourceSpec
    local_path: Path
    is_temporary: bool              # Should be cleaned up after build
    commit_hash: Optional[str] = None  # For git sources


class SourceResolver:
    """
    Resolves source specifications to local paths.

    Handles:
    - Local directory detection
    - Git cloning (sparse checkout for monorepos)
    - Tarball/sdist extraction
    - Temporary directory management
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path.home() / ".cache" / "hwb" / "sources"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def resolve(self, spec: SourceSpec) -> ResolvedSource:
        """Resolve a source spec to a local path."""
        match spec.type:
            case SourceType.LOCAL_PATH:
                return await self._resolve_local(spec)
            case SourceType.GIT_HTTPS | SourceType.GIT_SSH:
                return await self._resolve_git(spec)
            case SourceType.TARBALL | SourceType.SDIST:
                return await self._resolve_archive(spec)

    async def _resolve_git(self, spec: SourceSpec) -> ResolvedSource:
        """Clone a git repository."""
        # Use sparse checkout if subdirectory specified
        clone_args = ["git", "clone", "--depth=1"]

        if spec.ref:
            clone_args.extend(["--branch", spec.ref])

        if spec.subdirectory:
            clone_args.extend([
                "--filter=blob:none",
                "--sparse"
            ])

        # Clone to temp or cache directory
        dest = self._get_cache_path(spec)
        clone_args.extend([spec.location, str(dest)])

        process = await asyncio.create_subprocess_exec(
            *clone_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.wait()

        # Get commit hash
        commit_hash = await self._get_commit_hash(dest)

        # Handle subdirectory
        final_path = dest / spec.subdirectory if spec.subdirectory else dest

        return ResolvedSource(
            spec=spec,
            local_path=final_path,
            is_temporary=True,
            commit_hash=commit_hash
        )

    def parse_source(self, source: str) -> SourceSpec:
        """Parse a source string into a SourceSpec."""
        if source.startswith("git@"):
            return SourceSpec(SourceType.GIT_SSH, source)
        elif source.startswith("https://") and ".git" in source:
            return SourceSpec(SourceType.GIT_HTTPS, source)
        elif source.endswith((".tar.gz", ".tgz", ".zip")):
            return SourceSpec(SourceType.TARBALL, source)
        else:
            path = Path(source)
            if path.exists():
                return SourceSpec(SourceType.LOCAL_PATH, str(path.resolve()))
            raise ValueError(f"Cannot determine source type for: {source}")
```

### 2. Project Analyzer

**File**: `src/headless_wheel_builder/core/analyzer.py`

Analyzes Python project structure and extracts metadata.

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import tomllib

@dataclass
class BuildBackend:
    """Build backend specification."""
    module: str                     # e.g., "hatchling.build"
    requirements: list[str]         # e.g., ["hatchling>=1.26"]

    @property
    def name(self) -> str:
        """Get friendly name of backend."""
        if "hatchling" in self.module:
            return "hatchling"
        elif "setuptools" in self.module:
            return "setuptools"
        elif "flit" in self.module:
            return "flit"
        elif "pdm" in self.module:
            return "pdm"
        elif "maturin" in self.module:
            return "maturin"
        return self.module


@dataclass
class ProjectMetadata:
    """Extracted project metadata."""
    name: str
    version: Optional[str]
    requires_python: Optional[str] = None
    dependencies: list[str] = field(default_factory=list)
    optional_dependencies: dict[str, list[str]] = field(default_factory=dict)

    # Build info
    backend: Optional[BuildBackend] = None
    has_pyproject: bool = False
    has_setup_py: bool = False
    has_setup_cfg: bool = False

    # Extension modules
    has_extension_modules: bool = False
    extension_languages: list[str] = field(default_factory=list)  # ["c", "cpp", "rust"]


class ProjectAnalyzer:
    """
    Analyzes Python projects to extract build information.

    Handles:
    - pyproject.toml parsing (PEP 621)
    - setup.py/setup.cfg fallback detection
    - Build backend identification
    - Extension module detection
    """

    # Default build backend per PEP 517
    DEFAULT_BACKEND = BuildBackend(
        module="setuptools.build_meta",
        requirements=["setuptools>=61.0", "wheel"]
    )

    async def analyze(self, source_path: Path) -> ProjectMetadata:
        """Analyze a project and extract metadata."""
        pyproject_path = source_path / "pyproject.toml"
        setup_py_path = source_path / "setup.py"
        setup_cfg_path = source_path / "setup.cfg"

        metadata = ProjectMetadata(
            name="",
            version=None,
            has_pyproject=pyproject_path.exists(),
            has_setup_py=setup_py_path.exists(),
            has_setup_cfg=setup_cfg_path.exists()
        )

        if metadata.has_pyproject:
            await self._parse_pyproject(pyproject_path, metadata)
        elif metadata.has_setup_py:
            await self._parse_setup_py(setup_py_path, metadata)

        # Detect extension modules
        await self._detect_extensions(source_path, metadata)

        return metadata

    async def _parse_pyproject(self, path: Path, metadata: ProjectMetadata) -> None:
        """Parse pyproject.toml for metadata."""
        with open(path, "rb") as f:
            data = tomllib.load(f)

        # Build system (PEP 518)
        build_system = data.get("build-system", {})
        if build_system:
            metadata.backend = BuildBackend(
                module=build_system.get("build-backend", "setuptools.build_meta"),
                requirements=build_system.get("requires", ["setuptools", "wheel"])
            )
        else:
            # No build-system = legacy setuptools
            metadata.backend = self.DEFAULT_BACKEND

        # Project metadata (PEP 621)
        project = data.get("project", {})
        metadata.name = project.get("name", "")
        metadata.version = project.get("version")
        metadata.requires_python = project.get("requires-python")
        metadata.dependencies = project.get("dependencies", [])
        metadata.optional_dependencies = project.get("optional-dependencies", {})

        # Dynamic version detection
        if "version" in project.get("dynamic", []):
            # Version will be determined at build time
            metadata.version = None

    async def _detect_extensions(self, source_path: Path, metadata: ProjectMetadata) -> None:
        """Detect if project has extension modules."""
        # Check for common patterns
        patterns = {
            "c": ["*.c", "*.h"],
            "cpp": ["*.cpp", "*.cxx", "*.cc", "*.hpp"],
            "rust": ["Cargo.toml"],
            "cython": ["*.pyx", "*.pxd"]
        }

        for lang, globs in patterns.items():
            for glob_pattern in globs:
                if list(source_path.rglob(glob_pattern)):
                    metadata.has_extension_modules = True
                    metadata.extension_languages.append(lang)
                    break
```

### 3. Build Engine

**File**: `src/headless_wheel_builder/core/builder.py`

Implements PEP 517 build frontend.

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol
import asyncio
import importlib
import sys
import tempfile

@dataclass
class BuildResult:
    """Result of a wheel build."""
    success: bool
    wheel_path: Optional[Path] = None
    sdist_path: Optional[Path] = None
    build_log: str = ""
    duration_seconds: float = 0.0
    error: Optional[str] = None


class IsolationStrategy(Protocol):
    """Protocol for build isolation strategies."""

    async def create_environment(
        self,
        python_version: str,
        build_requirements: list[str]
    ) -> "BuildEnvironment":
        ...


@dataclass
class BuildEnvironment:
    """An isolated build environment."""
    python_path: Path
    site_packages: Path
    env_vars: dict[str, str]
    cleanup: callable  # Async cleanup function


class BuildEngine:
    """
    PEP 517-compliant build frontend.

    Executes builds in isolated environments using any
    PEP 517-compliant build backend.
    """

    def __init__(
        self,
        isolation: IsolationStrategy,
        output_dir: Optional[Path] = None
    ):
        self.isolation = isolation
        self.output_dir = output_dir or Path("dist")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def build_wheel(
        self,
        source_path: Path,
        metadata: "ProjectMetadata",
        python_version: str = "3.12"
    ) -> BuildResult:
        """
        Build a wheel from source.

        Process:
        1. Create isolated environment
        2. Install build dependencies
        3. Call build backend's build_wheel hook
        4. Validate output wheel
        5. Cleanup environment
        """
        import time
        start_time = time.time()
        build_log = []

        try:
            # Create isolated environment
            build_log.append(f"Creating isolated environment for Python {python_version}")
            env = await self.isolation.create_environment(
                python_version=python_version,
                build_requirements=metadata.backend.requirements
            )

            try:
                # Build the wheel using PEP 517 hooks
                wheel_path = await self._invoke_build_backend(
                    source_path=source_path,
                    env=env,
                    backend=metadata.backend,
                    build_log=build_log
                )

                # Validate wheel
                await self._validate_wheel(wheel_path)

                # Move to output directory
                final_path = self.output_dir / wheel_path.name
                wheel_path.rename(final_path)

                return BuildResult(
                    success=True,
                    wheel_path=final_path,
                    build_log="\n".join(build_log),
                    duration_seconds=time.time() - start_time
                )

            finally:
                await env.cleanup()

        except Exception as e:
            return BuildResult(
                success=False,
                build_log="\n".join(build_log),
                duration_seconds=time.time() - start_time,
                error=str(e)
            )

    async def _invoke_build_backend(
        self,
        source_path: Path,
        env: BuildEnvironment,
        backend: "BuildBackend",
        build_log: list[str]
    ) -> Path:
        """
        Invoke PEP 517 build backend.

        Uses subprocess to run in isolated environment.
        """
        build_log.append(f"Using build backend: {backend.name}")

        # Create temp directory for wheel output
        with tempfile.TemporaryDirectory() as wheel_dir:
            # PEP 517 build script
            build_script = f'''
import sys
sys.path.insert(0, {str(source_path)!r})

from {backend.module} import build_wheel

wheel_name = build_wheel(
    {str(wheel_dir)!r},
    config_settings=None
)
print(f"WHEEL_NAME={{wheel_name}}")
'''

            # Execute in isolated environment
            process = await asyncio.create_subprocess_exec(
                str(env.python_path),
                "-c", build_script,
                cwd=source_path,
                env=env.env_vars,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                build_log.append(f"Build failed:\n{stderr.decode()}")
                raise BuildError(f"Build backend failed: {stderr.decode()}")

            # Parse wheel name from output
            output = stdout.decode()
            for line in output.split("\n"):
                if line.startswith("WHEEL_NAME="):
                    wheel_name = line.split("=", 1)[1].strip()
                    return Path(wheel_dir) / wheel_name

            raise BuildError("Build backend did not report wheel name")

    async def _validate_wheel(self, wheel_path: Path) -> None:
        """Validate wheel structure and metadata."""
        import zipfile

        if not wheel_path.exists():
            raise BuildError(f"Wheel not found: {wheel_path}")

        if not wheel_path.suffix == ".whl":
            raise BuildError(f"Invalid wheel extension: {wheel_path.suffix}")

        # Check wheel structure
        with zipfile.ZipFile(wheel_path) as whl:
            names = whl.namelist()

            # Must have WHEEL and METADATA files
            has_wheel = any("WHEEL" in n for n in names)
            has_metadata = any("METADATA" in n for n in names)

            if not has_wheel or not has_metadata:
                raise BuildError("Invalid wheel: missing WHEEL or METADATA")


class BuildError(Exception):
    """Build-related error."""
    pass
```

### 4. Isolation Strategies

**File**: `src/headless_wheel_builder/isolation/venv.py`

Virtual environment isolation.

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import asyncio
import os
import shutil
import tempfile
import venv

@dataclass
class VenvConfig:
    """Configuration for venv isolation."""
    use_uv: bool = True             # Use uv if available
    python_path: Optional[Path] = None  # Specific Python interpreter
    cache_envs: bool = False        # Reuse environments


class VenvIsolation:
    """
    Virtual environment isolation strategy.

    Creates ephemeral venvs for each build. Uses uv for
    fast dependency installation when available.
    """

    def __init__(self, config: Optional[VenvConfig] = None):
        self.config = config or VenvConfig()
        self._uv_available: Optional[bool] = None

    async def create_environment(
        self,
        python_version: str,
        build_requirements: list[str]
    ) -> "BuildEnvironment":
        """Create an isolated venv with build dependencies."""

        # Create temp directory for venv
        venv_dir = Path(tempfile.mkdtemp(prefix="hwb_venv_"))

        try:
            # Find Python interpreter
            python_path = await self._find_python(python_version)

            # Create venv
            await self._create_venv(python_path, venv_dir)

            # Get venv Python path
            if os.name == "nt":
                venv_python = venv_dir / "Scripts" / "python.exe"
                site_packages = venv_dir / "Lib" / "site-packages"
            else:
                venv_python = venv_dir / "bin" / "python"
                site_packages = venv_dir / "lib" / f"python{python_version}" / "site-packages"

            # Install build requirements
            await self._install_requirements(venv_python, build_requirements)

            # Build environment variables
            env_vars = os.environ.copy()
            env_vars["VIRTUAL_ENV"] = str(venv_dir)
            env_vars["PATH"] = f"{venv_dir / 'Scripts' if os.name == 'nt' else venv_dir / 'bin'}{os.pathsep}{env_vars.get('PATH', '')}"

            # Windows-specific: disable xformers for SM 12.0
            if os.name == "nt":
                env_vars["XFORMERS_DISABLED"] = "1"

            async def cleanup():
                shutil.rmtree(venv_dir, ignore_errors=True)

            return BuildEnvironment(
                python_path=venv_python,
                site_packages=site_packages,
                env_vars=env_vars,
                cleanup=cleanup
            )

        except Exception:
            shutil.rmtree(venv_dir, ignore_errors=True)
            raise

    async def _find_python(self, version: str) -> Path:
        """Find Python interpreter for specified version."""
        # Try uv first (manages Python versions)
        if await self._check_uv_available():
            result = await asyncio.create_subprocess_exec(
                "uv", "python", "find", version,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            if result.returncode == 0:
                return Path(stdout.decode().strip())

        # Try pyenv
        pyenv_root = os.environ.get("PYENV_ROOT", Path.home() / ".pyenv")
        pyenv_python = Path(pyenv_root) / "versions" / version / "bin" / "python"
        if pyenv_python.exists():
            return pyenv_python

        # Fallback to system Python
        for name in [f"python{version}", "python3", "python"]:
            python = shutil.which(name)
            if python:
                return Path(python)

        raise RuntimeError(f"Python {version} not found")

    async def _create_venv(self, python: Path, venv_dir: Path) -> None:
        """Create virtual environment."""
        # Use uv if available (faster)
        if await self._check_uv_available():
            process = await asyncio.create_subprocess_exec(
                "uv", "venv", str(venv_dir),
                "--python", str(python),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.wait()
            if process.returncode == 0:
                return

        # Fallback to venv module
        venv.create(venv_dir, with_pip=True)

    async def _install_requirements(
        self,
        python: Path,
        requirements: list[str]
    ) -> None:
        """Install requirements in venv."""
        if not requirements:
            return

        # Use uv pip if available (10-100x faster)
        if await self._check_uv_available():
            process = await asyncio.create_subprocess_exec(
                "uv", "pip", "install",
                "--python", str(python),
                *requirements,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        else:
            process = await asyncio.create_subprocess_exec(
                str(python), "-m", "pip", "install",
                "--quiet",
                *requirements,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"Failed to install build requirements: {stderr.decode()}")

    async def _check_uv_available(self) -> bool:
        """Check if uv is available."""
        if self._uv_available is None:
            self._uv_available = shutil.which("uv") is not None
        return self._uv_available
```

**File**: `src/headless_wheel_builder/isolation/docker.py`

Docker isolation for manylinux/musllinux builds.

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import asyncio
import json
import os
import tempfile

@dataclass
class DockerConfig:
    """Configuration for Docker isolation."""

    # manylinux images
    manylinux_image: str = "quay.io/pypa/manylinux_2_28_x86_64"
    musllinux_image: str = "quay.io/pypa/musllinux_1_2_x86_64"

    # Platform support
    platform: Optional[str] = None  # e.g., "linux/amd64"

    # GPU support
    enable_gpu: bool = False
    gpu_runtime: str = "nvidia"

    # Resource limits
    memory_limit: Optional[str] = None  # e.g., "8g"
    cpu_limit: Optional[float] = None   # e.g., 4.0


# Available manylinux images by glibc version
MANYLINUX_IMAGES = {
    "2014": "quay.io/pypa/manylinux2014_{arch}",
    "2_28": "quay.io/pypa/manylinux_2_28_{arch}",
    "2_34": "quay.io/pypa/manylinux_2_34_{arch}",
    "2_35": "quay.io/pypa/manylinux_2_35_{arch}",
}

MUSLLINUX_IMAGES = {
    "1_2": "quay.io/pypa/musllinux_1_2_{arch}",
}

# Python paths in manylinux images
PYTHON_PATHS = {
    "3.9": "/opt/python/cp39-cp39/bin/python",
    "3.10": "/opt/python/cp310-cp310/bin/python",
    "3.11": "/opt/python/cp311-cp311/bin/python",
    "3.12": "/opt/python/cp312-cp312/bin/python",
    "3.13": "/opt/python/cp313-cp313/bin/python",
    "3.14": "/opt/python/cp314-cp314/bin/python",
}


class DockerIsolation:
    """
    Docker-based isolation for manylinux/musllinux builds.

    Creates containers from official PyPA images for building
    portable Linux wheels with bundled dependencies.
    """

    def __init__(self, config: Optional[DockerConfig] = None):
        self.config = config or DockerConfig()

    async def create_environment(
        self,
        python_version: str,
        build_requirements: list[str],
        manylinux: str = "2_28",
        arch: str = "x86_64"
    ) -> "BuildEnvironment":
        """Create a Docker-based build environment."""

        # Select image
        image = MANYLINUX_IMAGES[manylinux].format(arch=arch)
        python_path = PYTHON_PATHS.get(python_version)

        if not python_path:
            raise ValueError(f"Python {python_version} not available in manylinux image")

        # Create container
        container_id = await self._create_container(image, python_path)

        try:
            # Install build requirements
            await self._install_in_container(
                container_id,
                python_path,
                build_requirements
            )

            async def cleanup():
                await self._remove_container(container_id)

            return DockerBuildEnvironment(
                container_id=container_id,
                python_path=Path(python_path),
                site_packages=Path("/opt/python/lib"),  # Not used directly
                env_vars={},  # Environment is in container
                cleanup=cleanup,
                docker_isolation=self
            )

        except Exception:
            await self._remove_container(container_id)
            raise

    async def _create_container(
        self,
        image: str,
        python_path: str
    ) -> str:
        """Create a Docker container."""
        cmd = [
            "docker", "create",
            "--interactive",
        ]

        # GPU support
        if self.config.enable_gpu:
            cmd.extend(["--gpus", "all", "--runtime", self.config.gpu_runtime])

        # Resource limits
        if self.config.memory_limit:
            cmd.extend(["--memory", self.config.memory_limit])
        if self.config.cpu_limit:
            cmd.extend(["--cpus", str(self.config.cpu_limit)])

        # Platform
        if self.config.platform:
            cmd.extend(["--platform", self.config.platform])

        cmd.extend([image, "/bin/bash"])

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"Failed to create container: {stderr.decode()}")

        container_id = stdout.decode().strip()

        # Start the container
        await asyncio.create_subprocess_exec(
            "docker", "start", container_id,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )

        return container_id

    async def _install_in_container(
        self,
        container_id: str,
        python_path: str,
        requirements: list[str]
    ) -> None:
        """Install packages in container."""
        if not requirements:
            return

        # Create requirements string
        req_str = " ".join(f'"{r}"' for r in requirements)

        process = await asyncio.create_subprocess_exec(
            "docker", "exec", container_id,
            python_path, "-m", "pip", "install", *requirements,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"Failed to install requirements: {stderr.decode()}")

    async def build_in_container(
        self,
        container_id: str,
        source_path: Path,
        output_path: Path,
        python_path: str
    ) -> Path:
        """
        Build wheel inside Docker container.

        Copies source in, builds, runs auditwheel, copies wheel out.
        """
        # Copy source into container
        await asyncio.create_subprocess_exec(
            "docker", "cp",
            str(source_path), f"{container_id}:/src",
            stdout=asyncio.subprocess.DEVNULL
        )

        # Build wheel
        build_cmd = f"{python_path} -m build --wheel --outdir /wheels /src"

        process = await asyncio.create_subprocess_exec(
            "docker", "exec", container_id,
            "/bin/bash", "-c", build_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"Build failed: {stderr.decode()}")

        # Run auditwheel to bundle dependencies
        auditwheel_cmd = f"auditwheel repair /wheels/*.whl -w /wheels/repaired"

        process = await asyncio.create_subprocess_exec(
            "docker", "exec", container_id,
            "/bin/bash", "-c", auditwheel_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.wait()

        # Copy wheel out
        output_path.mkdir(parents=True, exist_ok=True)

        await asyncio.create_subprocess_exec(
            "docker", "cp",
            f"{container_id}:/wheels/repaired/.", str(output_path),
            stdout=asyncio.subprocess.DEVNULL
        )

        # Find the wheel
        wheels = list(output_path.glob("*.whl"))
        if not wheels:
            raise RuntimeError("No wheel produced")

        return wheels[0]

    async def _remove_container(self, container_id: str) -> None:
        """Remove Docker container."""
        await asyncio.create_subprocess_exec(
            "docker", "rm", "-f", container_id,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )


@dataclass
class DockerBuildEnvironment:
    """Build environment backed by Docker container."""
    container_id: str
    python_path: Path
    site_packages: Path
    env_vars: dict[str, str]
    cleanup: callable
    docker_isolation: DockerIsolation
```

### 5. Publishing Layer

**File**: `src/headless_wheel_builder/publish/pypi.py`

PyPI publishing with Trusted Publishers support.

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import asyncio
import os

@dataclass
class PyPIConfig:
    """PyPI publishing configuration."""
    repository_url: str = "https://upload.pypi.org/legacy/"
    test_pypi: bool = False

    # Authentication (mutually exclusive)
    api_token: Optional[str] = None
    trusted_publisher: bool = False  # Use OIDC

    # Options
    skip_existing: bool = False
    verbose: bool = False


class PyPIPublisher:
    """
    Publish wheels to PyPI.

    Supports:
    - Trusted Publishers (OIDC) - preferred
    - API tokens - fallback
    - TestPyPI for testing
    """

    def __init__(self, config: Optional[PyPIConfig] = None):
        self.config = config or PyPIConfig()

    async def publish(
        self,
        wheel_path: Path,
        sdist_path: Optional[Path] = None
    ) -> "PublishResult":
        """
        Publish wheel (and optionally sdist) to PyPI.
        """
        files = [wheel_path]
        if sdist_path:
            files.append(sdist_path)

        # Determine authentication method
        auth_args = await self._get_auth_args()

        # Build twine command
        cmd = [
            "twine", "upload",
            "--repository-url", self._get_repository_url(),
            *auth_args,
        ]

        if self.config.skip_existing:
            cmd.append("--skip-existing")

        if self.config.verbose:
            cmd.append("--verbose")

        cmd.extend(str(f) for f in files)

        # Execute upload
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=await self._get_env()
        )

        stdout, stderr = await process.communicate()

        return PublishResult(
            success=process.returncode == 0,
            output=stdout.decode() + stderr.decode(),
            repository_url=self._get_repository_url()
        )

    async def _get_auth_args(self) -> list[str]:
        """Get authentication arguments for twine."""
        if self.config.trusted_publisher:
            # OIDC token exchange happens automatically via environment
            return []

        if self.config.api_token:
            return [
                "--username", "__token__",
                "--password", self.config.api_token
            ]

        # Try environment variables
        if os.environ.get("TWINE_PASSWORD"):
            return []  # twine will use TWINE_USERNAME/TWINE_PASSWORD

        raise ValueError(
            "No authentication configured. Use trusted_publisher=True, "
            "provide api_token, or set TWINE_USERNAME/TWINE_PASSWORD"
        )

    async def _get_env(self) -> dict[str, str]:
        """Get environment variables for twine."""
        env = os.environ.copy()

        if self.config.trusted_publisher:
            # For Trusted Publishers, we need to get OIDC token
            # This is typically provided by CI environment
            # GitHub Actions: ACTIONS_ID_TOKEN_REQUEST_TOKEN/URL
            # GitLab CI: CI_JOB_JWT_V2
            pass

        return env

    def _get_repository_url(self) -> str:
        """Get repository URL."""
        if self.config.test_pypi:
            return "https://test.pypi.org/legacy/"
        return self.config.repository_url


@dataclass
class PublishResult:
    """Result of a publish operation."""
    success: bool
    output: str
    repository_url: str
    package_url: Optional[str] = None
```

---

## Data Flow Diagrams

### Build Flow

```
┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
│   CLI    │      │ Source   │      │ Project  │      │  Build   │      │ Artifact │
│          │      │ Resolver │      │ Analyzer │      │  Engine  │      │ Manager  │
└────┬─────┘      └────┬─────┘      └────┬─────┘      └────┬─────┘      └────┬─────┘
     │                 │                 │                 │                 │
     │ hwb build       │                 │                 │                 │
     │ github.com/...  │                 │                 │                 │
     │────────────────►│                 │                 │                 │
     │                 │                 │                 │                 │
     │                 │ clone repo      │                 │                 │
     │                 │────────────────►│                 │                 │
     │                 │                 │                 │                 │
     │                 │◄────────────────│                 │                 │
     │                 │ ResolvedSource  │                 │                 │
     │                 │                 │                 │                 │
     │                 │ analyze()       │                 │                 │
     │                 │────────────────►│                 │                 │
     │                 │                 │                 │                 │
     │                 │                 │ parse           │                 │
     │                 │                 │ pyproject.toml  │                 │
     │                 │                 │                 │                 │
     │                 │◄────────────────│                 │                 │
     │                 │ ProjectMetadata │                 │                 │
     │                 │                 │                 │                 │
     │                 │                 │ build_wheel()   │                 │
     │                 │                 │────────────────►│                 │
     │                 │                 │                 │                 │
     │                 │                 │                 │ create_env()    │
     │                 │                 │                 │───────────────► │
     │                 │                 │                 │   (isolation)   │
     │                 │                 │                 │                 │
     │                 │                 │                 │ install deps    │
     │                 │                 │                 │───────────────► │
     │                 │                 │                 │                 │
     │                 │                 │                 │ PEP 517 build   │
     │                 │                 │                 │───────────────► │
     │                 │                 │                 │                 │
     │                 │                 │                 │◄─────────────── │
     │                 │                 │                 │   wheel file    │
     │                 │                 │                 │                 │
     │                 │                 │                 │ validate()      │
     │                 │                 │                 │────────────────►│
     │                 │                 │                 │                 │
     │                 │                 │◄────────────────│                 │
     │                 │                 │  BuildResult    │                 │
     │                 │                 │                 │                 │
     │◄────────────────│                 │                 │                 │
     │   wheel path    │                 │                 │                 │
     │                 │                 │                 │                 │
```

### Publish Flow with Trusted Publishers

```
┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
│   CLI    │      │   CI     │      │   PyPI   │      │  OIDC    │
│          │      │ Provider │      │          │      │ Provider │
└────┬─────┘      └────┬─────┘      └────┬─────┘      └────┬─────┘
     │                 │                 │                 │
     │ hwb publish     │                 │                 │
     │ (trusted pub)   │                 │                 │
     │────────────────►│                 │                 │
     │                 │                 │                 │
     │                 │ request         │                 │
     │                 │ OIDC token      │                 │
     │                 │────────────────────────────────────►
     │                 │                 │                 │
     │                 │◄────────────────────────────────────
     │                 │  ID token       │                 │
     │                 │  (short-lived)  │                 │
     │                 │                 │                 │
     │                 │ token exchange  │                 │
     │                 │ + project claim │                 │
     │                 │────────────────►│                 │
     │                 │                 │                 │
     │                 │                 │ verify token    │
     │                 │                 │────────────────►│
     │                 │                 │                 │
     │                 │                 │◄────────────────│
     │                 │                 │   valid         │
     │                 │                 │                 │
     │                 │◄────────────────│                 │
     │                 │ PyPI API token  │                 │
     │                 │ (15 min TTL)    │                 │
     │                 │                 │                 │
     │                 │ upload wheel    │                 │
     │                 │────────────────►│                 │
     │                 │                 │                 │
     │◄────────────────│                 │                 │
     │   success       │                 │                 │
     │                 │                 │                 │
```

---

## Key Design Decisions

### 1. Why PEP 517 Frontend, Not Build Backend?

**Decision**: Implement as a build frontend that uses existing backends.

**Alternatives Considered**:
- Custom build backend (reinventing wheel)
- Wrapper around pip/build (less control)
- Backend-specific integrations (fragmented)

**Rationale**:
- Leverages ecosystem: works with any PEP 517 backend
- Users keep their existing build configuration
- No lock-in to specific backend
- Future-proof as new backends emerge

### 2. Why uv for Dependency Resolution?

**Decision**: Use uv when available, fallback to pip.

**Alternatives Considered**:
- pip only (slower, but ubiquitous)
- uv required (not installed everywhere)
- poetry/pdm resolver (backend-specific)

**Rationale**:
- uv is 10-100x faster for dependency resolution
- Falls back gracefully when unavailable
- Rust binary is easy to install
- Active development by Astral

### 3. Why Support Both venv and Docker?

**Decision**: Support both isolation strategies as first-class options.

**Alternatives Considered**:
- venv only (faster, simpler)
- Docker only (more reproducible)
- Conda environments (different ecosystem)

**Rationale**:
- venv is faster for pure Python packages
- Docker needed for manylinux compliance
- Different use cases need different trade-offs
- User choice maximizes flexibility

### 4. Why Trusted Publishers First?

**Decision**: Recommend OIDC-based publishing over API tokens.

**Alternatives Considered**:
- API tokens only (simpler, widely supported)
- Both equal (no clear guidance)

**Rationale**:
- Short-lived tokens (15 min) reduce breach impact
- No secrets to manage or rotate
- Audit trail built into CI provider
- PyPA recommended approach for 2026

---

## Performance Considerations

### Build Times

| Scenario | venv (uv) | venv (pip) | Docker |
|----------|-----------|------------|--------|
| Pure Python, no deps | ~3s | ~8s | ~15s |
| Pure Python, 10 deps | ~5s | ~30s | ~25s |
| C extension | ~20s | ~25s | ~45s |
| CUDA extension | N/A | N/A | ~120s |

### Memory Usage

| Component | Typical | Maximum |
|-----------|---------|---------|
| CLI process | ~50 MB | ~200 MB |
| venv creation | ~100 MB | ~500 MB |
| Docker container | ~500 MB | ~4 GB |
| Build (C extension) | ~1 GB | ~8 GB |

### Parallelization

- Build matrix entries run in parallel (configurable limit)
- Source download and analysis are sequential
- Publishing is sequential (registry rate limits)

---

## Security Considerations

See `SECURITY.md` for detailed security model. Key points:

1. **Build isolation**: All builds run in isolated environments
2. **No arbitrary code execution**: Source is analyzed, not executed, before build
3. **Trusted Publishers**: Eliminates long-lived secrets
4. **Credential handling**: API tokens never logged or cached

---

## Future Architecture Considerations

### Remote Build Workers
- Offload builds to remote machines
- GPU cluster for CUDA wheels
- Distributed build cache

### Package Signing
- Sigstore integration
- PEP 458 TUF support
- Attestation generation

### Monorepo Support
- Workspace-aware builds
- Dependency graph analysis
- Incremental rebuilds

---

## Changelog

| Date | Changes |
|------|---------|
| 2026-01-23 | Initial architecture documentation |
