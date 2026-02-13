from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest

from headless_wheel_builder.exceptions import IsolationError
from headless_wheel_builder.isolation.docker import (
    MANYLINUX_IMAGES,
    MANYLINUX_PYTHON_PATHS,
    DockerConfig,
    DockerIsolation,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.asyncio
async def test_select_image_respects_explicit_override() -> None:
    iso = DockerIsolation(DockerConfig(image="my/custom:image", platform="manylinux"))
    img = await iso._select_image("3.12")
    assert img == "my/custom:image"


@pytest.mark.asyncio
async def test_select_image_auto_defaults_to_manylinux_2_28_x86_64() -> None:
    iso = DockerIsolation(DockerConfig(platform="auto", architecture="x86_64"))
    # Mock _ensure_image to avoid needing Docker installed
    iso._ensure_image = AsyncMock()  # type: ignore[method-assign]
    img = await iso._select_image("3.12")
    # Should be the full URL from MANYLINUX_IMAGES
    assert "manylinux_2_28_x86_64" in img or img.endswith("manylinux_2_28_x86_64")


@pytest.mark.asyncio
async def test_select_image_architecture_adjusts_default() -> None:
    iso = DockerIsolation(DockerConfig(platform="manylinux", architecture="aarch64"))
    # Mock _ensure_image to avoid needing Docker installed
    iso._ensure_image = AsyncMock()  # type: ignore[method-assign]
    img = await iso._select_image("3.12")
    assert "aarch64" in img


@pytest.mark.asyncio
async def test_build_docker_command_excludes_internal_env_vars(tmp_path: Path) -> None:
    cfg = DockerConfig(
        platform="manylinux",
        extra_env={"__HWB_SECRET": "nope", "FOO": "bar"},
        network=False,
    )
    iso = DockerIsolation(cfg)
    cmd = await iso._build_docker_command("image", source_dir=tmp_path, output_dir=tmp_path / "out")
    joined = " ".join(cmd)
    assert "--network=none" in joined
    assert "FOO=bar" in joined
    assert "__HWB_SECRET" not in joined


# =============================================================================
# P0: Validate python_version support early
# =============================================================================


def test_get_container_python_supported_version() -> None:
    """Supported Python versions should return the correct path."""
    iso = DockerIsolation()
    # Test exact match
    assert iso._get_container_python("3.12") == "/opt/python/cp312-cp312/bin/python"
    # Test all supported versions
    for version in MANYLINUX_PYTHON_PATHS:
        path = iso._get_container_python(version)
        assert path == MANYLINUX_PYTHON_PATHS[version]


def test_get_container_python_major_minor_match() -> None:
    """Python version with patch level should match major.minor."""
    iso = DockerIsolation()
    # 3.12.0 should match 3.12
    assert iso._get_container_python("3.12.0") == MANYLINUX_PYTHON_PATHS["3.12"]
    assert iso._get_container_python("3.11.5") == MANYLINUX_PYTHON_PATHS["3.11"]


def test_get_container_python_unsupported_version() -> None:
    """Unsupported Python versions should raise IsolationError with supported list."""
    iso = DockerIsolation()
    with pytest.raises(IsolationError, match="Unsupported Python version: 2.7") as exc_info:
        iso._get_container_python("2.7")

    # Error message should list supported versions
    error_msg = str(exc_info.value)
    assert "Supported versions:" in error_msg
    assert "3.12" in error_msg


def test_get_container_python_unsupported_future_version() -> None:
    """Future unsupported versions should raise IsolationError."""
    iso = DockerIsolation()
    with pytest.raises(IsolationError, match="Unsupported Python version: 3.99"):
        iso._get_container_python("3.99")


# =============================================================================
# P0: Docker image selection returns canonical full URLs deterministically
# =============================================================================


@pytest.mark.asyncio
async def test_select_image_returns_full_quay_url() -> None:
    """Image selection should return the full quay.io URL."""
    iso = DockerIsolation(DockerConfig(platform="manylinux", architecture="x86_64"))
    # Mock _ensure_image to avoid needing Docker installed
    iso._ensure_image = AsyncMock()  # type: ignore[method-assign]
    img = await iso._select_image("3.12")
    # Should return the full URL from MANYLINUX_IMAGES
    assert img == "quay.io/pypa/manylinux_2_28_x86_64"


@pytest.mark.asyncio
async def test_select_image_unknown_platform_raises_isolation_error() -> None:
    """Unknown platform/arch combo should raise IsolationError with available keys."""
    iso = DockerIsolation(DockerConfig(platform="manylinux", architecture="s390x"))
    # No mock needed - error happens before _ensure_image is called
    with pytest.raises(IsolationError, match="Unknown platform") as exc_info:
        await iso._select_image("3.12")

    # Error should list available keys
    error_msg = str(exc_info.value)
    assert "Available:" in error_msg
    assert "manylinux_2_28_x86_64" in error_msg


@pytest.mark.asyncio
async def test_select_image_deterministic_across_calls() -> None:
    """Image selection should be deterministic across multiple calls."""
    iso = DockerIsolation(DockerConfig(platform="auto", architecture="x86_64"))
    # Mock _ensure_image to avoid needing Docker installed
    iso._ensure_image = AsyncMock()  # type: ignore[method-assign]
    img1 = await iso._select_image("3.12")
    img2 = await iso._select_image("3.12")
    img3 = await iso._select_image("3.12")
    assert img1 == img2 == img3


# =============================================================================
# P2: Golden tests for image selection tables
# =============================================================================


def test_manylinux_images_contains_expected_keys() -> None:
    """MANYLINUX_IMAGES should contain all expected platform keys."""
    expected_keys = {
        "manylinux2014_x86_64",
        "manylinux2014_aarch64",
        "manylinux_2_28_x86_64",
        "manylinux_2_28_aarch64",
        "manylinux_2_34_x86_64",
        "manylinux_2_34_aarch64",
        "musllinux_1_1_x86_64",
        "musllinux_1_1_aarch64",
        "musllinux_1_2_x86_64",
        "musllinux_1_2_aarch64",
    }
    for key in expected_keys:
        assert key in MANYLINUX_IMAGES, f"Missing key: {key}"


def test_manylinux_python_paths_contains_expected_versions() -> None:
    """MANYLINUX_PYTHON_PATHS should contain expected Python versions."""
    expected_versions = {"3.9", "3.10", "3.11", "3.12", "3.13"}
    for version in expected_versions:
        assert version in MANYLINUX_PYTHON_PATHS, f"Missing version: {version}"


def test_all_manylinux_images_are_quay_urls() -> None:
    """All MANYLINUX_IMAGES values should be quay.io URLs."""
    for key, url in MANYLINUX_IMAGES.items():
        assert url.startswith("quay.io/pypa/"), f"Invalid URL for {key}: {url}"
