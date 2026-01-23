"""Tests for build isolation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from headless_wheel_builder.isolation.venv import VenvConfig, VenvIsolation


class TestVenvIsolation:
    """Tests for VenvIsolation."""

    @pytest.mark.asyncio
    async def test_check_available(self) -> None:
        """Test that venv isolation is always available."""
        isolation = VenvIsolation()
        assert await isolation.check_available() is True

    @pytest.mark.asyncio
    async def test_create_environment(self) -> None:
        """Test creating an isolated environment."""
        isolation = VenvIsolation()
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

        env = await isolation.create_environment(
            python_version=python_version,
            build_requirements=[],
        )

        try:
            assert env.python_path.exists()
            assert "VIRTUAL_ENV" in env.env_vars
        finally:
            await env.cleanup()

    @pytest.mark.asyncio
    async def test_create_environment_with_requirements(self) -> None:
        """Test creating environment with build requirements."""
        isolation = VenvIsolation()
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

        env = await isolation.create_environment(
            python_version=python_version,
            build_requirements=["wheel"],
        )

        try:
            assert env.python_path.exists()
            # Wheel should be installed
            # We don't verify directly, but the create should succeed
        finally:
            await env.cleanup()

    @pytest.mark.asyncio
    async def test_environment_cleanup(self) -> None:
        """Test that environment is cleaned up properly."""
        isolation = VenvIsolation()
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

        env = await isolation.create_environment(
            python_version=python_version,
            build_requirements=[],
        )

        venv_path = env.python_path.parent.parent
        assert venv_path.exists()

        await env.cleanup()
        assert not venv_path.exists()

    @pytest.mark.asyncio
    async def test_environment_context_manager(self) -> None:
        """Test using environment as context manager."""
        isolation = VenvIsolation()
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

        async with await isolation.create_environment(
            python_version=python_version,
            build_requirements=[],
        ) as env:
            venv_path = env.python_path.parent.parent
            assert venv_path.exists()

        # Should be cleaned up after context
        assert not venv_path.exists()

    @pytest.mark.asyncio
    async def test_windows_env_vars(self) -> None:
        """Test Windows-specific environment variables."""
        isolation = VenvIsolation()
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

        env = await isolation.create_environment(
            python_version=python_version,
            build_requirements=[],
        )

        try:
            if sys.platform == "win32":
                # Windows should have XFORMERS_DISABLED for RTX 5080
                assert env.env_vars.get("XFORMERS_DISABLED") == "1"
        finally:
            await env.cleanup()


class TestVenvConfig:
    """Tests for VenvConfig."""

    def test_default_config(self) -> None:
        """Test default configuration."""
        config = VenvConfig()

        assert config.use_uv is True
        assert config.python_path is None
        assert config.cache_envs is False

    def test_custom_config(self) -> None:
        """Test custom configuration."""
        config = VenvConfig(
            use_uv=False,
            python_path=Path("/usr/bin/python3"),
            extra_env={"MY_VAR": "value"},
        )

        assert config.use_uv is False
        assert config.python_path == Path("/usr/bin/python3")
        assert config.extra_env == {"MY_VAR": "value"}

    @pytest.mark.asyncio
    async def test_config_extra_env(self) -> None:
        """Test extra environment variables in config."""
        config = VenvConfig(extra_env={"CUSTOM_VAR": "custom_value"})
        isolation = VenvIsolation(config)
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

        env = await isolation.create_environment(
            python_version=python_version,
            build_requirements=[],
        )

        try:
            assert env.env_vars.get("CUSTOM_VAR") == "custom_value"
        finally:
            await env.cleanup()
