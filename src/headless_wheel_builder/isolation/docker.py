"""Docker-based build isolation for manylinux/musllinux wheels."""

from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
from pathlib import Path

from headless_wheel_builder.exceptions import IsolationError
from headless_wheel_builder.isolation.base import BaseIsolation, BuildEnvironment
from headless_wheel_builder.isolation.docker_commands import (
    build_docker_command,
    generate_build_script,
)
from headless_wheel_builder.isolation.docker_config import DockerConfig, PlatformType
from headless_wheel_builder.isolation.docker_images import (
    get_container_python,
    list_available_images,
    select_image,
)


class DockerIsolation(BaseIsolation):
    """
    Docker-based build isolation for producing portable Linux wheels.

    Uses official manylinux/musllinux images from PyPA to build wheels
    that are compatible with a wide range of Linux distributions.

    Features:
    - Automatic image selection based on project requirements
    - Support for manylinux2014, manylinux_2_28, manylinux_2_34
    - Support for musllinux (Alpine/musl)
    - Automatic wheel repair with auditwheel
    - Cross-architecture builds (x86_64, aarch64)
    """

    def __init__(self, config: DockerConfig | None = None) -> None:
        self.config = config or DockerConfig()
        self._docker_available: bool | None = None
        self._docker_path: str | None = None

    async def check_available(self) -> bool:
        """Check if Docker is available and running."""
        if self._docker_available is not None:
            return self._docker_available

        # Check for docker executable
        self._docker_path = shutil.which("docker")
        if not self._docker_path:
            self._docker_available = False
            return False

        # Check if Docker daemon is running
        try:
            process = await asyncio.create_subprocess_exec(
                "docker",
                "info",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await process.communicate()
            self._docker_available = process.returncode == 0
        except Exception:
            self._docker_available = False

        return self._docker_available

    async def create_environment(
        self,
        python_version: str,
        build_requirements: list[str],
    ) -> BuildEnvironment:
        """
        Create a Docker-based build environment.

        This doesn't actually start the container - it prepares the
        configuration. The actual build happens in build_in_container().
        """
        if not await self.check_available():
            raise IsolationError(
                "Docker is not available. Install Docker Desktop or ensure "
                "the Docker daemon is running."
            )

        # Select appropriate image
        image = await select_image(
            self.config.image,
            self.config.platform,
            self.config.architecture,
        )

        # Create temp directory for build context
        work_dir = Path(tempfile.mkdtemp(prefix="hwb_docker_"))

        # Get Python path in container
        python_path = get_container_python(python_version)

        # Build environment variables
        env_vars = {}

        async def cleanup() -> None:
            if work_dir.exists():
                shutil.rmtree(work_dir, ignore_errors=True)

        # Store Docker-specific info in env_vars for build_in_container
        env_vars["__HWB_DOCKER_IMAGE__"] = image
        env_vars["__HWB_DOCKER_PYTHON__"] = python_path
        env_vars["__HWB_DOCKER_WORKDIR__"] = str(work_dir)
        env_vars["__HWB_BUILD_REQS__"] = json.dumps(build_requirements)

        return BuildEnvironment(
            python_path=Path(python_path),  # Path inside container
            site_packages=Path("/tmp/site-packages"),  # Placeholder
            env_vars=env_vars,
            _cleanup=cleanup,
        )

    async def build_in_container(
        self,
        source_dir: Path,
        output_dir: Path,
        env: BuildEnvironment,
        build_wheel: bool = True,
        build_sdist: bool = False,
        config_settings: dict[str, str] | None = None,
    ) -> tuple[Path | None, Path | None, str]:
        """
        Build wheel inside Docker container.

        Returns:
            Tuple of (wheel_path, sdist_path, build_log)
        """
        image = env.env_vars["__HWB_DOCKER_IMAGE__"]
        python_path = env.env_vars["__HWB_DOCKER_PYTHON__"]
        build_reqs = json.loads(env.env_vars["__HWB_BUILD_REQS__"])

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build the container command
        docker_cmd = await build_docker_command(
            config=self.config,
            image=image,
            source_dir=source_dir,
            output_dir=output_dir,
        )

        # Build script to run inside container
        build_script = generate_build_script(
            python_path=python_path,
            build_requirements=build_reqs,
            build_wheel=build_wheel,
            build_sdist=build_sdist,
            config_settings=config_settings,
            repair_wheel=self.config.repair_wheel,
        )

        # Run the build
        full_cmd = [*docker_cmd, "bash", "-c", build_script]

        process = await asyncio.create_subprocess_exec(
            *full_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await process.communicate()
        build_log = stdout.decode(errors="replace")

        if process.returncode != 0:
            raise IsolationError(f"Docker build failed:\n{build_log}")

        # Find built artifacts
        wheel_path = None
        sdist_path = None

        for f in output_dir.iterdir():
            if f.suffix == ".whl":
                wheel_path = f
            elif f.suffix == ".gz" and ".tar" in f.name:
                sdist_path = f

        return wheel_path, sdist_path, build_log

    async def list_available_images(self) -> dict[str, str]:
        """List available manylinux/musllinux images."""
        return list_available_images()

    async def get_image_info(self, image: str) -> dict:
        """Get information about a Docker image."""
        process = await asyncio.create_subprocess_exec(
            "docker",
            "image",
            "inspect",
            image,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _stderr = await process.communicate()

        if process.returncode != 0:
            raise IsolationError(f"Image not found: {image}")

        info = json.loads(stdout.decode())[0]
        return {
            "id": info.get("Id", "")[:12],
            "created": info.get("Created", ""),
            "size": info.get("Size", 0),
            "architecture": info.get("Architecture", ""),
            "os": info.get("Os", ""),
        }


# Convenience function
async def get_docker_isolation(
    platform: PlatformType = "auto",
    architecture: str = "x86_64",
) -> DockerIsolation:
    """Get a Docker isolation strategy."""
    config = DockerConfig(platform=platform, architecture=architecture)
    isolation = DockerIsolation(config)

    if not await isolation.check_available():
        raise IsolationError("Docker is not available")

    return isolation
