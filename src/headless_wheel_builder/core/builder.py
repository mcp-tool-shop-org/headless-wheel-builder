"""Build engine - PEP 517 compliant wheel builder."""

from __future__ import annotations

import asyncio
import hashlib
import shutil
import tempfile
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from headless_wheel_builder.core.analyzer import ProjectAnalyzer, ProjectMetadata
from headless_wheel_builder.core.source import ResolvedSource, SourceResolver, SourceSpec
from headless_wheel_builder.exceptions import BuildError
from headless_wheel_builder.isolation.venv import VenvIsolation

if TYPE_CHECKING:
    from headless_wheel_builder.isolation.base import BuildEnvironment, IsolationStrategy
    pass


@dataclass
class BuildResult:
    """Result of a wheel build."""

    success: bool
    wheel_path: Path | None = None
    sdist_path: Path | None = None
    build_log: str = ""
    duration_seconds: float = 0.0
    error: str | None = None

    # Wheel metadata (if successful)
    name: str | None = None
    version: str | None = None
    python_tag: str | None = None
    abi_tag: str | None = None
    platform_tag: str | None = None
    sha256: str | None = None
    size_bytes: int | None = None

    @classmethod
    def failure(cls, error: str, build_log: str = "", duration: float = 0.0) -> BuildResult:
        """Create a failure result."""
        return cls(
            success=False,
            error=error,
            build_log=build_log,
            duration_seconds=duration,
        )


@dataclass
class BuildConfig:
    """Configuration for a build."""

    output_dir: Path = field(default_factory=lambda: Path("dist"))
    python_version: str = "3.12"
    build_wheel: bool = True
    build_sdist: bool = False
    clean_output: bool = False
    config_settings: dict[str, str] | None = None
    isolation: IsolationStrategy | None = None

    # Docker-specific options
    use_docker: bool = False
    docker_platform: str = "auto"  # "auto", "manylinux", "musllinux"
    docker_image: str | None = None  # Override specific image
    docker_architecture: str = "x86_64"  # x86_64, aarch64


class BuildEngine:
    """
    PEP 517-compliant build frontend.

    Executes builds in isolated environments using any
    PEP 517-compliant build backend.
    """

    def __init__(self, config: BuildConfig | None = None) -> None:
        self.config = config or BuildConfig()
        self.source_resolver = SourceResolver()
        self.project_analyzer = ProjectAnalyzer()

    async def build(
        self,
        source: str | Path | SourceSpec | ResolvedSource,
        output_dir: Path | None = None,
        python_version: str | None = None,
        wheel: bool = True,
        sdist: bool = False,
    ) -> BuildResult:
        """
        Build wheel (and optionally sdist) from source.

        Args:
            source: Source to build from (path, URL, or SourceSpec)
            output_dir: Output directory for artifacts
            python_version: Python version to use
            wheel: Build wheel
            sdist: Build source distribution

        Returns:
            BuildResult with paths to built artifacts

        Raises:
            BuildError: If build fails
        """
        start_time = time.time()
        build_log: list[str] = []
        output_dir = output_dir or self.config.output_dir
        python_version = python_version or self.config.python_version

        # Ensure output directory exists
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Clean output directory if requested
        if self.config.clean_output:
            for f in output_dir.glob("*.whl"):
                f.unlink()
            for f in output_dir.glob("*.tar.gz"):
                f.unlink()

        try:
            # Resolve source
            build_log.append(f"Resolving source: {source}")
            resolved_source = await self._resolve_source(source)
            build_log.append(f"Source resolved to: {resolved_source.local_path}")

            # Analyze project
            build_log.append("Analyzing project...")
            metadata = await self.project_analyzer.analyze(resolved_source.local_path)
            build_log.append(f"Project: {metadata.name}")
            build_log.append(f"Backend: {metadata.backend.name if metadata.backend else 'unknown'}")

            # Get or create isolation
            isolation = self.config.isolation
            use_docker = self.config.use_docker

            if use_docker:
                # Use Docker isolation
                from headless_wheel_builder.isolation.docker import DockerConfig, DockerIsolation

                docker_config = DockerConfig(
                    platform=self.config.docker_platform,  # type: ignore[arg-type]
                    image=self.config.docker_image,
                    architecture=self.config.docker_architecture,
                )
                isolation = DockerIsolation(docker_config)
                build_log.append(
                    f"Using Docker isolation (platform: {self.config.docker_platform})"
                )

            if isolation is None:
                isolation = VenvIsolation()

            # Create isolated environment
            build_log.append(f"Creating isolated environment for Python {python_version}")
            env = await isolation.create_environment(
                python_version=python_version,
                build_requirements=metadata.build_requirements,
            )

            try:
                result = BuildResult(success=True)

                # Check if we're using Docker isolation for the actual build
                if use_docker:
                    from headless_wheel_builder.isolation.docker import DockerIsolation

                    if isinstance(isolation, DockerIsolation):
                        build_log.append("Building in Docker container...")
                        wheel_path, sdist_path, docker_log = await isolation.build_in_container(
                            source_dir=resolved_source.local_path,
                            output_dir=output_dir,
                            env=env,
                            build_wheel=wheel,
                            build_sdist=sdist,
                            config_settings=self.config.config_settings,
                        )
                        build_log.append(docker_log)

                        if wheel_path:
                            result.wheel_path = wheel_path
                            self._extract_wheel_metadata(wheel_path, result)
                        if sdist_path:
                            result.sdist_path = sdist_path

                        result.build_log = "\n".join(build_log)
                        result.duration_seconds = time.time() - start_time
                        return result

                # Standard venv build
                # Build wheel
                if wheel:
                    build_log.append("Building wheel...")
                    wheel_path = await self._build_wheel(
                        source_path=resolved_source.local_path,
                        output_dir=output_dir,
                        env=env,
                        metadata=metadata,
                        build_log=build_log,
                    )
                    result.wheel_path = wheel_path

                    # Extract wheel metadata
                    self._extract_wheel_metadata(wheel_path, result)

                # Build sdist
                if sdist:
                    build_log.append("Building source distribution...")
                    sdist_path = await self._build_sdist(
                        source_path=resolved_source.local_path,
                        output_dir=output_dir,
                        env=env,
                        metadata=metadata,
                        build_log=build_log,
                    )
                    result.sdist_path = sdist_path

                result.build_log = "\n".join(build_log)
                result.duration_seconds = time.time() - start_time

                return result

            finally:
                await env.cleanup()

        except BuildError:
            raise
        except Exception as e:
            return BuildResult.failure(
                error=str(e),
                build_log="\n".join(build_log),
                duration=time.time() - start_time,
            )

    async def _resolve_source(
        self,
        source: str | Path | SourceSpec | ResolvedSource,
    ) -> ResolvedSource:
        """Resolve source to a local path."""
        if isinstance(source, ResolvedSource):
            return source

        if isinstance(source, SourceSpec):
            return await self.source_resolver.resolve(source)

        if isinstance(source, Path):
            source = str(source)

        spec = self.source_resolver.parse_source(source)
        return await self.source_resolver.resolve(spec)

    async def _build_wheel(
        self,
        source_path: Path,
        output_dir: Path,
        env: BuildEnvironment,
        metadata: ProjectMetadata,
        build_log: list[str],
    ) -> Path:
        """Build wheel using PEP 517."""
        with tempfile.TemporaryDirectory(prefix="hwb_wheel_") as temp_dir:
            temp_path = Path(temp_dir)

            # Build script that invokes the backend
            build_script = self._create_build_script(
                backend_module=metadata.backend.module
                if metadata.backend
                else "setuptools.build_meta",
                source_path=source_path,
                output_path=temp_path,
                config_settings=self.config.config_settings,
            )

            # Run build in isolated environment
            process = await asyncio.create_subprocess_exec(
                str(env.python_path),
                "-c",
                build_script,
                cwd=source_path,
                env=env.env_vars,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()
            stdout_text = stdout.decode()
            stderr_text = stderr.decode()

            if process.returncode != 0:
                build_log.append(f"Build output:\n{stdout_text}")
                build_log.append(f"Build errors:\n{stderr_text}")
                raise BuildError(
                    f"Build failed with exit code {process.returncode}",
                    build_log="\n".join(build_log),
                )

            # Find the built wheel
            wheels = list(temp_path.glob("*.whl"))
            if not wheels:
                # Check if wheel name was printed
                for line in stdout_text.split("\n"):
                    if line.startswith("WHEEL_NAME="):
                        wheel_name = line.split("=", 1)[1].strip()
                        wheel_path = temp_path / wheel_name
                        if wheel_path.exists():
                            wheels = [wheel_path]
                            break

            if not wheels:
                raise BuildError("No wheel produced by build backend")

            wheel_path = wheels[0]

            # Validate wheel
            self._validate_wheel(wheel_path)

            # Move to output directory
            final_path = output_dir / wheel_path.name
            shutil.move(str(wheel_path), str(final_path))

            build_log.append(f"Built: {final_path.name}")
            return final_path

    async def _build_sdist(
        self,
        source_path: Path,
        output_dir: Path,
        env: BuildEnvironment,
        metadata: ProjectMetadata,
        build_log: list[str],
    ) -> Path:
        """Build source distribution using PEP 517."""
        with tempfile.TemporaryDirectory(prefix="hwb_sdist_") as temp_dir:
            temp_path = Path(temp_dir)

            # Build script for sdist
            build_script = self._create_sdist_script(
                backend_module=metadata.backend.module
                if metadata.backend
                else "setuptools.build_meta",
                source_path=source_path,
                output_path=temp_path,
                config_settings=self.config.config_settings,
            )

            process = await asyncio.create_subprocess_exec(
                str(env.python_path),
                "-c",
                build_script,
                cwd=source_path,
                env=env.env_vars,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            _stdout, stderr = await process.communicate()

            if process.returncode != 0:
                build_log.append(f"sdist build errors:\n{stderr.decode()}")
                raise BuildError(
                    f"sdist build failed with exit code {process.returncode}",
                    build_log="\n".join(build_log),
                )

            # Find the built sdist
            sdists = list(temp_path.glob("*.tar.gz"))
            if not sdists:
                raise BuildError("No sdist produced by build backend")

            sdist_path = sdists[0]

            # Move to output directory
            final_path = output_dir / sdist_path.name
            shutil.move(str(sdist_path), str(final_path))

            build_log.append(f"Built: {final_path.name}")
            return final_path

    def _create_build_script(
        self,
        backend_module: str,
        source_path: Path,
        output_path: Path,
        config_settings: dict[str, str] | None = None,
    ) -> str:
        """Create Python script to invoke build backend."""
        config_repr = repr(config_settings) if config_settings else "None"

        return f"""
import sys
import importlib

# Import the backend
backend = importlib.import_module({backend_module!r})

# Check which hook is available
if hasattr(backend, 'build_wheel'):
    wheel_name = backend.build_wheel(
        {str(output_path)!r},
        config_settings={config_repr}
    )
    print(f"WHEEL_NAME={{wheel_name}}")
else:
    raise RuntimeError("Build backend does not support build_wheel")
"""

    def _create_sdist_script(
        self,
        backend_module: str,
        source_path: Path,
        output_path: Path,
        config_settings: dict[str, str] | None = None,
    ) -> str:
        """Create Python script to invoke build backend for sdist."""
        config_repr = repr(config_settings) if config_settings else "None"

        return f"""
import sys
import importlib

# Import the backend
backend = importlib.import_module({backend_module!r})

# Check which hook is available
if hasattr(backend, 'build_sdist'):
    sdist_name = backend.build_sdist(
        {str(output_path)!r},
        config_settings={config_repr}
    )
    print(f"SDIST_NAME={{sdist_name}}")
else:
    raise RuntimeError("Build backend does not support build_sdist")
"""

    def _validate_wheel(self, wheel_path: Path) -> None:
        """Validate wheel structure and metadata."""
        if not wheel_path.exists():
            raise BuildError(f"Wheel not found: {wheel_path}")

        if wheel_path.suffix != ".whl":
            raise BuildError(f"Invalid wheel extension: {wheel_path.suffix}")

        try:
            with zipfile.ZipFile(wheel_path) as whl:
                names = whl.namelist()

                # Must have WHEEL and METADATA files
                has_wheel = any("WHEEL" in n for n in names)
                has_metadata = any("METADATA" in n for n in names)

                if not has_wheel:
                    raise BuildError("Invalid wheel: missing WHEEL file")
                if not has_metadata:
                    raise BuildError("Invalid wheel: missing METADATA file")

                # Check for unsafe paths
                for name in names:
                    if name.startswith("/") or ".." in name:
                        raise BuildError(f"Wheel contains unsafe path: {name}")

        except zipfile.BadZipFile as e:
            raise BuildError(f"Invalid wheel file: {e}") from e

    def _extract_wheel_metadata(self, wheel_path: Path, result: BuildResult) -> None:
        """Extract metadata from wheel filename and contents."""
        # Parse wheel filename
        # Format: {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
        name = wheel_path.stem
        parts = name.split("-")

        if len(parts) >= 5:
            result.name = parts[0].replace("_", "-")
            result.version = parts[1]
            result.python_tag = parts[-3]
            result.abi_tag = parts[-2]
            result.platform_tag = parts[-1]

        # Calculate SHA256
        result.sha256 = hashlib.sha256(wheel_path.read_bytes()).hexdigest()
        result.size_bytes = wheel_path.stat().st_size


# Convenience function for simple builds
async def build_wheel(
    source: str | Path = ".",
    output_dir: str | Path = "dist",
    python: str = "3.12",
    sdist: bool = False,
) -> BuildResult:
    """
    Build a wheel from source.

    This is the main entry point for programmatic usage.

    Args:
        source: Path to project or git URL
        output_dir: Directory for output files
        python: Python version to use
        sdist: Also build source distribution

    Returns:
        BuildResult with wheel path and metadata

    Example:
        >>> result = await build_wheel(".", python="3.12")
        >>> print(result.wheel_path)
        dist/mypackage-1.0.0-py3-none-any.whl
    """
    config = BuildConfig(
        output_dir=Path(output_dir),
        python_version=python,
        build_sdist=sdist,
    )
    engine = BuildEngine(config)
    return await engine.build(source)
