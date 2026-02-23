"""Docker command building and script generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from headless_wheel_builder.isolation.docker_config import DockerConfig, build_env_vars

if TYPE_CHECKING:
    from pathlib import Path


async def build_docker_command(
    config: DockerConfig,
    image: str,
    source_dir: Path,
    output_dir: Path,
) -> list[str]:
    """
    Build the docker run command.

    Args:
        config: Docker configuration
        image: Docker image name/URL
        source_dir: Source directory to mount (read-only)
        output_dir: Output directory to mount (read-write)

    Returns:
        List of command arguments for docker run
    """
    cmd = ["docker", "run", "--rm"]

    # Resource limits
    if config.memory_limit:
        cmd.extend(["--memory", config.memory_limit])

    if config.cpu_limit:
        cmd.extend(["--cpus", str(config.cpu_limit)])

    # Network
    if not config.network:
        cmd.append("--network=none")

    # Mount source directory (read-only)
    cmd.extend(["-v", f"{source_dir.absolute()}:/src:ro"])

    # Mount output directory (read-write)
    cmd.extend(["-v", f"{output_dir.absolute()}:/output:rw"])

    # Extra mounts
    for host_path, container_path in config.extra_mounts.items():
        cmd.extend(["-v", f"{host_path}:{container_path}"])

    # Environment variables
    env_vars = build_env_vars(config)
    for key, value in env_vars.items():
        if not key.startswith("__HWB_"):  # Skip internal vars
            cmd.extend(["-e", f"{key}={value}"])

    # Working directory
    cmd.extend(["-w", "/src"])

    # Image
    cmd.append(image)

    return cmd


def generate_build_script(
    python_path: str,
    build_requirements: list[str],
    build_wheel: bool,
    build_sdist: bool,
    config_settings: dict[str, str] | None,
    repair_wheel: bool,
) -> str:
    """
    Generate the build script to run inside container.

    Args:
        python_path: Path to Python executable in container
        build_requirements: List of build dependencies to install
        build_wheel: Whether to build wheel
        build_sdist: Whether to build sdist
        config_settings: Build configuration settings
        repair_wheel: Whether to repair wheel with auditwheel

    Returns:
        Bash script to execute in container
    """
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
