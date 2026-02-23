"""Tests for Docker refactored modules."""

import pytest

from headless_wheel_builder.exceptions import IsolationError
from headless_wheel_builder.isolation.docker_commands import (
    build_docker_command,
    generate_build_script,
)
from headless_wheel_builder.isolation.docker_config import (
    DockerConfig,
    build_env_vars,
)
from headless_wheel_builder.isolation.docker_images import (
    MANYLINUX_IMAGES,
    MANYLINUX_PYTHON_PATHS,
    get_container_python,
    list_available_images,
    select_image,
)


class TestDockerConfig:
    """Test Docker configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = DockerConfig()
        assert config.platform == "auto"
        assert config.image is None
        assert config.architecture == "x86_64"
        assert config.network is True
        assert config.memory_limit is None
        assert config.cpu_limit is None
        assert config.repair_wheel is True
        assert config.strip_binaries is True
        assert config.extra_mounts == {}
        assert config.extra_env == {}

    def test_custom_config(self):
        """Test custom configuration values."""
        config = DockerConfig(
            platform="manylinux",
            image="custom:tag",
            architecture="aarch64",
            network=False,
            memory_limit="4g",
            cpu_limit=2.0,
            repair_wheel=False,
            extra_mounts={"/host": "/container"},
            extra_env={"KEY": "value"},
        )
        assert config.platform == "manylinux"
        assert config.image == "custom:tag"
        assert config.architecture == "aarch64"
        assert config.network is False
        assert config.memory_limit == "4g"
        assert config.cpu_limit == 2.0
        assert config.repair_wheel is False
        assert config.extra_mounts == {"/host": "/container"}
        assert config.extra_env == {"KEY": "value"}

    def test_build_env_vars_default(self):
        """Test default environment variables."""
        config = DockerConfig()
        env = build_env_vars(config)
        assert env["DEBIAN_FRONTEND"] == "noninteractive"
        assert env["PIP_NO_CACHE_DIR"] == "1"
        assert env["PIP_DISABLE_PIP_VERSION_CHECK"] == "1"
        assert env["PYTHONDONTWRITEBYTECODE"] == "1"

    def test_build_env_vars_with_extras(self):
        """Test environment variables with custom additions."""
        config = DockerConfig(extra_env={"CUSTOM_VAR": "custom_value"})
        env = build_env_vars(config)
        assert env["CUSTOM_VAR"] == "custom_value"
        assert env["DEBIAN_FRONTEND"] == "noninteractive"


class TestDockerImages:
    """Test Docker image management."""

    def test_manylinux_images_available(self):
        """Test that manylinux images are defined."""
        assert len(MANYLINUX_IMAGES) > 0
        assert "manylinux2014_x86_64" in MANYLINUX_IMAGES
        assert "manylinux_2_28_x86_64" in MANYLINUX_IMAGES
        assert "musllinux_1_2_x86_64" in MANYLINUX_IMAGES

    def test_python_paths_available(self):
        """Test that Python paths are defined."""
        assert len(MANYLINUX_PYTHON_PATHS) > 0
        assert "3.11" in MANYLINUX_PYTHON_PATHS
        assert "3.12" in MANYLINUX_PYTHON_PATHS

    def test_get_container_python_exact_match(self):
        """Test getting Python path with exact version match."""
        python_path = get_container_python("3.11")
        assert python_path == "/opt/python/cp311-cp311/bin/python"

    def test_get_container_python_major_minor_match(self):
        """Test getting Python path with major.minor.patch version."""
        python_path = get_container_python("3.11.5")
        assert python_path == "/opt/python/cp311-cp311/bin/python"

    def test_get_container_python_unsupported(self):
        """Test error for unsupported Python version."""
        with pytest.raises(IsolationError, match="Unsupported Python version"):
            get_container_python("2.7")

    def test_get_container_python_invalid(self):
        """Test error for invalid Python version format."""
        with pytest.raises(IsolationError, match="Unsupported Python version"):
            get_container_python("invalid")

    @pytest.mark.asyncio
    async def test_select_image_explicit(self):
        """Test explicit image selection."""
        # Mock ensure_image_available to avoid actual Docker calls
        import headless_wheel_builder.isolation.docker_images as docker_images
        original = docker_images.ensure_image_available

        async def mock_ensure(image: str) -> None:
            pass

        docker_images.ensure_image_available = mock_ensure

        try:
            # Use a key from available images
            image = await select_image("manylinux_2_28_x86_64", "auto", "x86_64")
            assert image == "quay.io/pypa/manylinux_2_28_x86_64"
        finally:
            docker_images.ensure_image_available = original

    @pytest.mark.asyncio
    async def test_select_image_auto_platform(self):
        """Test automatic platform selection."""
        import headless_wheel_builder.isolation.docker_images as docker_images
        original = docker_images.ensure_image_available

        async def mock_ensure(image: str) -> None:
            pass

        docker_images.ensure_image_available = mock_ensure

        try:
            image = await select_image(None, "auto", "x86_64")
            assert "manylinux" in image
        finally:
            docker_images.ensure_image_available = original

    def test_list_available_images(self):
        """Test listing available images."""
        images = list_available_images()
        assert len(images) > 0
        assert "manylinux2014_x86_64" in images
        assert images == MANYLINUX_IMAGES


class TestDockerCommands:
    """Test Docker command generation."""

    @pytest.mark.asyncio
    async def test_build_docker_command_basic(self, tmp_path):
        """Test basic docker command building."""
        config = DockerConfig()
        source_dir = tmp_path / "source"
        output_dir = tmp_path / "output"
        source_dir.mkdir()
        output_dir.mkdir()

        cmd = await build_docker_command(
            config=config,
            image="test:image",
            source_dir=source_dir,
            output_dir=output_dir,
        )

        assert cmd[0] == "docker"
        assert cmd[1] == "run"
        assert "--rm" in cmd
        assert "-w" in cmd
        assert "/src" in cmd
        assert cmd[-1] == "test:image"

    @pytest.mark.asyncio
    async def test_build_docker_command_with_limits(self, tmp_path):
        """Test docker command with resource limits."""
        config = DockerConfig(memory_limit="4g", cpu_limit=2.0)
        source_dir = tmp_path / "source"
        output_dir = tmp_path / "output"
        source_dir.mkdir()
        output_dir.mkdir()

        cmd = await build_docker_command(
            config=config,
            image="test:image",
            source_dir=source_dir,
            output_dir=output_dir,
        )

        assert "--memory" in cmd
        assert "4g" in cmd
        assert "--cpus" in cmd
        assert "2.0" in cmd

    @pytest.mark.asyncio
    async def test_build_docker_command_no_network(self, tmp_path):
        """Test docker command with network disabled."""
        config = DockerConfig(network=False)
        source_dir = tmp_path / "source"
        output_dir = tmp_path / "output"
        source_dir.mkdir()
        output_dir.mkdir()

        cmd = await build_docker_command(
            config=config,
            image="test:image",
            source_dir=source_dir,
            output_dir=output_dir,
        )

        assert "--network=none" in cmd

    @pytest.mark.asyncio
    async def test_build_docker_command_extra_mounts(self, tmp_path):
        """Test docker command with extra volume mounts."""
        config = DockerConfig(extra_mounts={"/host/path": "/container/path"})
        source_dir = tmp_path / "source"
        output_dir = tmp_path / "output"
        source_dir.mkdir()
        output_dir.mkdir()

        cmd = await build_docker_command(
            config=config,
            image="test:image",
            source_dir=source_dir,
            output_dir=output_dir,
        )

        assert "/host/path:/container/path" in " ".join(cmd)

    def test_generate_build_script_basic(self):
        """Test basic build script generation."""
        script = generate_build_script(
            python_path="/opt/python/cp311-cp311/bin/python",
            build_requirements=[],
            build_wheel=True,
            build_sdist=False,
            config_settings=None,
            repair_wheel=True,
        )

        assert "set -ex" in script
        assert "/opt/python/cp311-cp311/bin/python" in script
        assert "pip install --upgrade pip build auditwheel" in script
        assert "python -m build --wheel" in script
        assert "auditwheel repair" in script

    def test_generate_build_script_with_requirements(self):
        """Test build script with build requirements."""
        script = generate_build_script(
            python_path="/opt/python/cp311-cp311/bin/python",
            build_requirements=["setuptools", "wheel"],
            build_wheel=True,
            build_sdist=False,
            config_settings=None,
            repair_wheel=False,
        )

        assert "pip install" in script
        assert '"setuptools"' in script
        assert '"wheel"' in script

    def test_generate_build_script_both_artifacts(self):
        """Test build script for both wheel and sdist."""
        script = generate_build_script(
            python_path="/opt/python/cp311-cp311/bin/python",
            build_requirements=[],
            build_wheel=True,
            build_sdist=True,
            config_settings=None,
            repair_wheel=False,
        )

        assert "python -m build" in script
        # Should not have --wheel or --sdist flags when building both
        assert "build --wheel" not in script
        assert "build --sdist" not in script

    def test_generate_build_script_sdist_only(self):
        """Test build script for sdist only."""
        script = generate_build_script(
            python_path="/opt/python/cp311-cp311/bin/python",
            build_requirements=[],
            build_wheel=False,
            build_sdist=True,
            config_settings=None,
            repair_wheel=False,
        )

        assert "python -m build --sdist" in script
        # Note: auditwheel is always installed, but not used for repair
        assert "auditwheel repair" not in script

    def test_generate_build_script_with_config_settings(self):
        """Test build script with config settings."""
        script = generate_build_script(
            python_path="/opt/python/cp311-cp311/bin/python",
            build_requirements=[],
            build_wheel=True,
            build_sdist=False,
            config_settings={"key": "value", "another": "setting"},
            repair_wheel=False,
        )

        assert "--config-setting=key=value" in script
        assert "--config-setting=another=setting" in script

    def test_generate_build_script_no_repair(self):
        """Test build script without wheel repair."""
        script = generate_build_script(
            python_path="/opt/python/cp311-cp311/bin/python",
            build_requirements=[],
            build_wheel=True,
            build_sdist=False,
            config_settings=None,
            repair_wheel=False,
        )

        assert "auditwheel repair" not in script
        assert "cp /tmp/dist/* /output/" in script
