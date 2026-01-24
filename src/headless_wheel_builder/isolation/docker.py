"""Docker-based build isolation for manylinux/musllinux wheels."""

from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from headless_wheel_builder.exceptions import IsolationError
from headless_wheel_builder.isolation.base import BaseIsolation, BuildEnvironment

# Official manylinux images from PyPA
# https://github.com/pypa/manylinux
MANYLINUX_IMAGES = {
    # manylinux2014 - CentOS 7 based (oldest, most compatible)
    "manylinux2014_x86_64": "quay.io/pypa/manylinux2014_x86_64",
    "manylinux2014_i686": "quay.io/pypa/manylinux2014_i686",
    "manylinux2014_aarch64": "quay.io/pypa/manylinux2014_aarch64",
    # manylinux_2_28 - AlmaLinux 8 based (recommended for new projects)
    "manylinux_2_28_x86_64": "quay.io/pypa/manylinux_2_28_x86_64",
    "manylinux_2_28_aarch64": "quay.io/pypa/manylinux_2_28_aarch64",
    # manylinux_2_34 - AlmaLinux 9 based (newest glibc)
    "manylinux_2_34_x86_64": "quay.io/pypa/manylinux_2_34_x86_64",
    "manylinux_2_34_aarch64": "quay.io/pypa/manylinux_2_34_aarch64",
    # musllinux - Alpine based (for musl libc distros)
    "musllinux_1_1_x86_64": "quay.io/pypa/musllinux_1_1_x86_64",
    "musllinux_1_1_aarch64": "quay.io/pypa/musllinux_1_1_aarch64",
    "musllinux_1_2_x86_64": "quay.io/pypa/musllinux_1_2_x86_64",
    "musllinux_1_2_aarch64": "quay.io/pypa/musllinux_1_2_aarch64",
}

# Python paths in manylinux images
MANYLINUX_PYTHON_PATHS = {
    "3.9": "/opt/python/cp39-cp39/bin/python",
    "3.10": "/opt/python/cp310-cp310/bin/python",
    "3.11": "/opt/python/cp311-cp311/bin/python",
    "3.12": "/opt/python/cp312-cp312/bin/python",
    "3.13": "/opt/python/cp313-cp313/bin/python",
}

# Default image for each platform type
DEFAULT_IMAGES = {
    "manylinux": "manylinux_2_28_x86_64",
    "musllinux": "musllinux_1_2_x86_64",
}

PlatformType = Literal["manylinux", "musllinux", "auto"]


@dataclass
class DockerConfig:
    """Configuration for Docker isolation."""

    # Platform selection
    platform: PlatformType = "auto"
    image: str | None = None  # Override specific image
    architecture: str = "x86_64"  # x86_64, aarch64, i686

    # Container settings
    network: bool = True  # Enable network for pip installs
    memory_limit: str | None = None  # e.g., "4g"
    cpu_limit: float | None = None  # e.g., 2.0 for 2 CPUs

    # Build settings
    repair_wheel: bool = True  # Run auditwheel/delocate
    strip_binaries: bool = True  # Strip debug symbols

    # Volume mounts
    extra_mounts: dict[str, str] = field(default_factory=dict)

    # Environment variables
    extra_env: dict[str, str] = field(default_factory=dict)


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
        image = await self._select_image(python_version)

        # Create temp directory for build context
        work_dir = Path(tempfile.mkdtemp(prefix="hwb_docker_"))

        # Get Python path in container
        python_path = self._get_container_python(python_version)

        # Build environment variables
        env_vars = self._build_env_vars()

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
        docker_cmd = await self._build_docker_command(
            image=image,
            source_dir=source_dir,
            output_dir=output_dir,
        )

        # Build script to run inside container
        build_script = self._generate_build_script(
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

    async def _select_image(self, python_version: str) -> str:
        """Select the appropriate Docker image."""
        # Use explicit image if provided
        if self.config.image:
            return self.config.image

        # Select based on platform type
        platform = self.config.platform
        arch = self.config.architecture

        if platform == "auto":
            # Default to manylinux_2_28 for broadest compatibility
            platform = "manylinux"

        # Get the default for this platform
        platform_key = DEFAULT_IMAGES.get(platform, "manylinux_2_28_x86_64")

        # Adjust for architecture
        if arch != "x86_64":
            platform_key = platform_key.replace("x86_64", arch)

        # Get the full image URL
        image = MANYLINUX_IMAGES.get(platform_key)
        if not image:
            raise IsolationError(
                f"Unknown platform: {platform_key}. Available: {', '.join(MANYLINUX_IMAGES.keys())}"
            )

        # Pull image if needed
        await self._ensure_image(image)

        return image

    async def _ensure_image(self, image: str) -> None:
        """Pull Docker image if not present locally."""
        # Check if image exists
        process = await asyncio.create_subprocess_exec(
            "docker",
            "image",
            "inspect",
            image,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await process.communicate()

        if process.returncode != 0:
            # Pull the image
            process = await asyncio.create_subprocess_exec(
                "docker",
                "pull",
                image,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await process.communicate()

            if process.returncode != 0:
                raise IsolationError(f"Failed to pull Docker image {image}:\n{stdout.decode()}")

    def _get_container_python(self, version: str) -> str:
        """Get Python path inside manylinux container."""
        # Try exact match first
        if version in MANYLINUX_PYTHON_PATHS:
            return MANYLINUX_PYTHON_PATHS[version]

        # Try major.minor match
        parts = version.split(".")
        if len(parts) >= 2:
            short_version = f"{parts[0]}.{parts[1]}"
            if short_version in MANYLINUX_PYTHON_PATHS:
                return MANYLINUX_PYTHON_PATHS[short_version]

        # Default to 3.12
        return MANYLINUX_PYTHON_PATHS.get("3.12", "/opt/python/cp312-cp312/bin/python")

    def _build_env_vars(self) -> dict[str, str]:
        """Build environment variables for container."""
        env = {
            # Disable interactive prompts
            "DEBIAN_FRONTEND": "noninteractive",
            # Pip settings
            "PIP_NO_CACHE_DIR": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            # Build settings
            "PYTHONDONTWRITEBYTECODE": "1",
        }

        # Add extra env vars from config
        if self.config.extra_env:
            env.update(self.config.extra_env)

        return env

    async def _build_docker_command(
        self,
        image: str,
        source_dir: Path,
        output_dir: Path,
    ) -> list[str]:
        """Build the docker run command."""
        cmd = ["docker", "run", "--rm"]

        # Resource limits
        if self.config.memory_limit:
            cmd.extend(["--memory", self.config.memory_limit])
        if self.config.cpu_limit:
            cmd.extend(["--cpus", str(self.config.cpu_limit)])

        # Network
        if not self.config.network:
            cmd.append("--network=none")

        # Mount source directory
        cmd.extend(["-v", f"{source_dir.absolute()}:/src:ro"])

        # Mount output directory
        cmd.extend(["-v", f"{output_dir.absolute()}:/output:rw"])

        # Extra mounts
        for host_path, container_path in self.config.extra_mounts.items():
            cmd.extend(["-v", f"{host_path}:{container_path}"])

        # Environment variables
        env_vars = self._build_env_vars()
        for key, value in env_vars.items():
            if not key.startswith("__HWB_"):  # Skip internal vars
                cmd.extend(["-e", f"{key}={value}"])

        # Working directory
        cmd.extend(["-w", "/src"])

        # Image
        cmd.append(image)

        return cmd

    def _generate_build_script(
        self,
        python_path: str,
        build_requirements: list[str],
        build_wheel: bool,
        build_sdist: bool,
        config_settings: dict[str, str] | None,
        repair_wheel: bool,
    ) -> str:
        """Generate the build script to run inside container."""
        lines = [
            "set -ex",  # Exit on error, print commands
            "",
            "# Upgrade pip and install build tools",
            f"{python_path} -m pip install --upgrade pip build auditwheel",
        ]

        # Install build requirements
        if build_requirements:
            reqs_str = " ".join(f'"{r}"' for r in build_requirements)
            lines.append(f"{python_path} -m pip install {reqs_str}")

        lines.append("")
        lines.append("# Build the package")

        # Build command
        build_cmd = f"{python_path} -m build"

        if build_wheel and not build_sdist:
            build_cmd += " --wheel"
        elif build_sdist and not build_wheel:
            build_cmd += " --sdist"

        # Config settings
        if config_settings:
            for key, value in config_settings.items():
                build_cmd += f" --config-setting={key}={value}"

        build_cmd += " --outdir /tmp/dist"
        lines.append(build_cmd)

        # Repair wheel with auditwheel
        if repair_wheel and build_wheel:
            lines.extend(
                [
                    "",
                    "# Repair wheel for manylinux compatibility",
                    "for whl in /tmp/dist/*.whl; do",
                    '    if [ -f "$whl" ]; then',
                    '        auditwheel repair "$whl" --plat auto -w /output/ || cp "$whl" /output/',
                    "    fi",
                    "done",
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    "# Copy artifacts to output",
                    "cp /tmp/dist/* /output/ 2>/dev/null || true",
                ]
            )

        # Copy sdist if built
        if build_sdist:
            lines.append("cp /tmp/dist/*.tar.gz /output/ 2>/dev/null || true")

        lines.extend(
            [
                "",
                "# List output",
                "ls -la /output/",
            ]
        )

        return "\n".join(lines)

    async def list_available_images(self) -> dict[str, str]:
        """List available manylinux/musllinux images."""
        return MANYLINUX_IMAGES.copy()

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
