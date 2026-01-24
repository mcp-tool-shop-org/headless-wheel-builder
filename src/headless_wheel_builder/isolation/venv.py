"""Virtual environment isolation strategy."""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from headless_wheel_builder.exceptions import DependencyError, IsolationError
from headless_wheel_builder.isolation.base import BaseIsolation, BuildEnvironment


@dataclass
class VenvConfig:
    """Configuration for venv isolation."""

    use_uv: bool = True  # Use uv if available (10-100x faster)
    python_path: Path | None = None  # Specific Python interpreter
    cache_envs: bool = False  # Reuse environments (not implemented yet)
    extra_env: dict[str, str] | None = None  # Extra environment variables


class VenvIsolation(BaseIsolation):
    """
    Virtual environment isolation strategy.

    Creates ephemeral venvs for each build. Uses uv for
    fast dependency installation when available.
    """

    def __init__(self, config: VenvConfig | None = None) -> None:
        self.config = config or VenvConfig()
        self._uv_available: bool | None = None
        self._uv_path: Path | None = None

    async def check_available(self) -> bool:
        """Check if venv isolation is available (always true on supported Python)."""
        return True

    async def create_environment(
        self,
        python_version: str,
        build_requirements: list[str],
    ) -> BuildEnvironment:
        """
        Create an isolated venv with build dependencies.

        Args:
            python_version: Python version to use
            build_requirements: Packages to install in the environment

        Returns:
            BuildEnvironment with isolated Python

        Raises:
            IsolationError: If environment creation fails
            DependencyError: If dependency installation fails
        """
        # Create temp directory for venv
        venv_dir = Path(tempfile.mkdtemp(prefix="hwb_venv_"))

        try:
            # Find Python interpreter
            python_path = await self._find_python(python_version)

            # Create venv
            await self._create_venv(python_path, venv_dir)

            # Get paths for the venv
            if sys.platform == "win32":
                venv_python = venv_dir / "Scripts" / "python.exe"
                venv_scripts = venv_dir / "Scripts"
                site_packages = venv_dir / "Lib" / "site-packages"
            else:
                venv_python = venv_dir / "bin" / "python"
                venv_scripts = venv_dir / "bin"
                # Site-packages path varies by Python version
                site_packages = venv_dir / "lib" / f"python{python_version}" / "site-packages"
                if not site_packages.exists():
                    # Try to find it
                    lib_dir = venv_dir / "lib"
                    if lib_dir.exists():
                        for d in lib_dir.iterdir():
                            if d.name.startswith("python"):
                                site_packages = d / "site-packages"
                                break

            if not venv_python.exists():
                raise IsolationError(f"venv Python not found at {venv_python}")

            # Install build requirements
            if build_requirements:
                await self._install_requirements(venv_python, build_requirements)

            # Build environment variables
            env_vars = self._build_env_vars(venv_dir, venv_scripts)

            async def cleanup() -> None:
                if venv_dir.exists():
                    shutil.rmtree(venv_dir, ignore_errors=True)

            return BuildEnvironment(
                python_path=venv_python,
                site_packages=site_packages,
                env_vars=env_vars,
                _cleanup=cleanup,
            )

        except Exception as e:
            # Clean up on failure
            if venv_dir.exists():
                shutil.rmtree(venv_dir, ignore_errors=True)
            if isinstance(e, (IsolationError, DependencyError)):
                raise
            raise IsolationError(f"Failed to create venv: {e}") from e

    def _build_env_vars(self, venv_dir: Path, scripts_dir: Path) -> dict[str, str]:
        """Build environment variables for the venv."""
        env = os.environ.copy()

        # Virtual environment setup
        env["VIRTUAL_ENV"] = str(venv_dir)
        env["PATH"] = f"{scripts_dir}{os.pathsep}{env.get('PATH', '')}"

        # Remove PYTHONHOME if set (can interfere with venv)
        env.pop("PYTHONHOME", None)

        # Windows-specific: disable xformers for SM 12.0 (RTX 5080)
        if sys.platform == "win32":
            env["XFORMERS_DISABLED"] = "1"

        # Add extra env vars from config
        if self.config.extra_env:
            env.update(self.config.extra_env)

        return env

    async def _find_python(self, version: str) -> Path:
        """
        Find Python interpreter for specified version.

        Search order:
        1. Config-specified path
        2. uv-managed Python
        3. pyenv Python
        4. System Python

        Args:
            version: Python version (e.g., "3.12")

        Returns:
            Path to Python interpreter

        Raises:
            IsolationError: If Python version not found
        """
        # Use configured path if provided
        if self.config.python_path and self.config.python_path.exists():
            return self.config.python_path

        # Try uv first (manages Python versions)
        if self.config.use_uv and await self._check_uv_available():
            uv_python = await self._find_uv_python(version)
            if uv_python:
                return uv_python

        # Try pyenv
        pyenv_python = self._find_pyenv_python(version)
        if pyenv_python:
            return pyenv_python

        # Try system Python
        system_python = self._find_system_python(version)
        if system_python:
            return system_python

        raise IsolationError(
            f"Python {version} not found. Install it with:\n"
            f"  uv python install {version}\n"
            f"  pyenv install {version}"
        )

    async def _find_uv_python(self, version: str) -> Path | None:
        """Find Python via uv."""
        try:
            process = await asyncio.create_subprocess_exec(
                "uv",
                "python",
                "find",
                version,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0:
                path = Path(stdout.decode().strip())
                if path.exists():
                    return path
        except FileNotFoundError:
            pass
        return None

    def _find_pyenv_python(self, version: str) -> Path | None:
        """Find Python via pyenv."""
        pyenv_root = os.environ.get("PYENV_ROOT")
        if not pyenv_root:
            pyenv_root = str(Path.home() / ".pyenv")

        pyenv_root_path = Path(pyenv_root)

        # Look for exact version or version prefix
        versions_dir = pyenv_root_path / "versions"
        if not versions_dir.exists():
            return None

        for ver_dir in versions_dir.iterdir():
            if ver_dir.name.startswith(version):
                if sys.platform == "win32":
                    python = ver_dir / "python.exe"
                else:
                    python = ver_dir / "bin" / "python"
                if python.exists():
                    return python

        return None

    def _find_system_python(self, version: str) -> Path | None:
        """Find system Python."""
        # Try specific version first
        names_to_try = [
            f"python{version}",
            f"python{version.replace('.', '')}",  # python312
        ]

        # On Windows, also try py launcher
        if sys.platform == "win32":
            names_to_try.insert(0, "py")

        for name in names_to_try:
            path = shutil.which(name)
            if path:
                # Verify version
                if name == "py":
                    # Use py launcher with version flag
                    path = shutil.which("py")
                    if path:
                        return Path(path)
                else:
                    return Path(path)

        # Fallback: check if current Python matches
        current_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        if current_version == version or version.startswith(current_version):
            return Path(sys.executable)

        return None

    async def _create_venv(self, python: Path, venv_dir: Path) -> None:
        """Create virtual environment."""
        # Use uv if available (much faster)
        if self.config.use_uv and await self._check_uv_available():
            await self._create_venv_uv(python, venv_dir)
        else:
            await self._create_venv_stdlib(python, venv_dir)

    async def _create_venv_uv(self, python: Path, venv_dir: Path) -> None:
        """Create venv using uv."""
        process = await asyncio.create_subprocess_exec(
            "uv",
            "venv",
            str(venv_dir),
            "--python",
            str(python),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, _stderr = await process.communicate()

        if process.returncode != 0:
            # Fall back to stdlib
            await self._create_venv_stdlib(python, venv_dir)

    async def _create_venv_stdlib(self, python: Path, venv_dir: Path) -> None:
        """Create venv using stdlib venv module."""
        # Use subprocess to ensure we use the correct Python
        process = await asyncio.create_subprocess_exec(
            str(python),
            "-m",
            "venv",
            str(venv_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()

        if process.returncode != 0:
            raise IsolationError(f"Failed to create venv: {stderr.decode()}")

    async def _install_requirements(
        self,
        python: Path,
        requirements: list[str],
    ) -> None:
        """Install requirements in the venv."""
        if not requirements:
            return

        # Use uv pip if available (10-100x faster)
        if self.config.use_uv and await self._check_uv_available():
            await self._install_with_uv(python, requirements)
        else:
            await self._install_with_pip(python, requirements)

    async def _install_with_uv(self, python: Path, requirements: list[str]) -> None:
        """Install packages using uv pip."""
        process = await asyncio.create_subprocess_exec(
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            *requirements,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _stdout, _stderr = await process.communicate()

        if process.returncode != 0:
            # Fall back to pip
            await self._install_with_pip(python, requirements)

    async def _install_with_pip(self, python: Path, requirements: list[str]) -> None:
        """Install packages using pip."""
        process = await asyncio.create_subprocess_exec(
            str(python),
            "-m",
            "pip",
            "install",
            "--quiet",
            "--disable-pip-version-check",
            *requirements,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode()
            # Try to identify which package failed
            for req in requirements:
                if req.split("[")[0].split(">=")[0].split("==")[0] in error_msg:
                    raise DependencyError(
                        f"Failed to install {req}: {error_msg}",
                        package=req,
                    )
            raise DependencyError(f"Failed to install requirements: {error_msg}")

    async def _check_uv_available(self) -> bool:
        """Check if uv is available."""
        if self._uv_available is not None:
            return self._uv_available

        self._uv_path = shutil.which("uv")
        self._uv_available = self._uv_path is not None
        return self._uv_available


# Convenience function to detect best isolation
async def get_default_isolation() -> VenvIsolation:
    """Get the default isolation strategy."""
    return VenvIsolation()
