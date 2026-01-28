"""Docker image management and selection."""

from __future__ import annotations

import asyncio

from headless_wheel_builder.exceptions import IsolationError
from headless_wheel_builder.security_validation import (
    ensure_deterministic_image,
    validate_python_version,
)

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


def get_container_python(version: str) -> str:
    """
    Get Python path inside manylinux container.

    Args:
        version: Python version (e.g., "3.11" or "3.11.5")

    Returns:
        Path to Python executable in container

    Raises:
        IsolationError: If the python_version is not supported.
    """
    # SECURITY: Validate python version upfront before lookup
    validate_python_version(version)

    # Try exact match first
    if version in MANYLINUX_PYTHON_PATHS:
        return MANYLINUX_PYTHON_PATHS[version]

    # Try major.minor match
    parts = version.split(".")
    if len(parts) >= 2:
        short_version = f"{parts[0]}.{parts[1]}"
        if short_version in MANYLINUX_PYTHON_PATHS:
            return MANYLINUX_PYTHON_PATHS[short_version]

    # Unsupported version - raise with helpful message
    supported = sorted(MANYLINUX_PYTHON_PATHS.keys())
    raise IsolationError(
        f"Unsupported Python version: {version}. "
        f"Supported versions: {', '.join(supported)}"
    )


async def select_image(
    explicit_image: str | None,
    platform: str,
    architecture: str,
) -> str:
    """
    Select the appropriate Docker image.

    Args:
        explicit_image: Explicitly specified image (takes precedence)
        platform: Platform type ("manylinux", "musllinux", or "auto")
        architecture: CPU architecture (e.g., "x86_64", "aarch64")

    Returns:
        Full Docker image URL

    Raises:
        IsolationError: If the platform/architecture combination is not found
    """
    # Use explicit image if provided
    if explicit_image:
        # SECURITY: Ensure deterministic canonical image name
        return ensure_deterministic_image(explicit_image, MANYLINUX_IMAGES)

    # Select based on platform type
    if platform == "auto":
        # Default to manylinux_2_28 for broadest compatibility
        platform = "manylinux"

    # Get the default for this platform
    platform_key = DEFAULT_IMAGES.get(platform, "manylinux_2_28_x86_64")

    # Adjust for architecture
    if architecture != "x86_64":
        platform_key = platform_key.replace("x86_64", architecture)

    # Get the full image URL
    image = MANYLINUX_IMAGES.get(platform_key)
    if not image:
        raise IsolationError(
            f"Unknown platform: {platform_key}. "
            f"Available: {', '.join(MANYLINUX_IMAGES.keys())}"
        )

    # Pull image if needed
    await ensure_image_available(image)

    # SECURITY: Return canonical deterministic image name
    return ensure_deterministic_image(image, MANYLINUX_IMAGES)


async def ensure_image_available(image: str) -> None:
    """
    Pull Docker image if not present locally.

    Args:
        image: Docker image name/URL

    Raises:
        IsolationError: If image pull fails
    """
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
            raise IsolationError(
                f"Failed to pull Docker image {image}:\n{stdout.decode()}"
            )


def list_available_images() -> dict[str, str]:
    """List available manylinux/musllinux images."""
    return MANYLINUX_IMAGES.copy()
