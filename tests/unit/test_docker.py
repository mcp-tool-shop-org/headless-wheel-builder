"""Tests for Docker isolation module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from headless_wheel_builder.isolation.docker import (
    DEFAULT_IMAGES,
    MANYLINUX_IMAGES,
    MANYLINUX_PYTHON_PATHS,
    DockerConfig,
    DockerIsolation,
    get_docker_isolation,
)


class TestDockerConfig:
    """Tests for DockerConfig dataclass."""

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
        """Test custom configuration."""
        config = DockerConfig(
            platform="manylinux",
            image="custom-image:latest",
            architecture="aarch64",
            network=False,
            memory_limit="4g",
            cpu_limit=2.0,
            repair_wheel=False,
            extra_env={"MY_VAR": "value"},
        )

        assert config.platform == "manylinux"
        assert config.image == "custom-image:latest"
        assert config.architecture == "aarch64"
        assert config.network is False
        assert config.memory_limit == "4g"
        assert config.cpu_limit == 2.0
        assert config.repair_wheel is False
        assert config.extra_env == {"MY_VAR": "value"}


class TestManylinuxImages:
    """Tests for manylinux image constants."""

    def test_manylinux_images_exist(self):
        """Test that required manylinux images are defined."""
        assert "manylinux2014_x86_64" in MANYLINUX_IMAGES
        assert "manylinux_2_28_x86_64" in MANYLINUX_IMAGES
        assert "manylinux_2_34_x86_64" in MANYLINUX_IMAGES

    def test_musllinux_images_exist(self):
        """Test that musllinux images are defined."""
        assert "musllinux_1_1_x86_64" in MANYLINUX_IMAGES
        assert "musllinux_1_2_x86_64" in MANYLINUX_IMAGES

    def test_aarch64_images_exist(self):
        """Test that ARM64 images are defined."""
        assert "manylinux2014_aarch64" in MANYLINUX_IMAGES
        assert "manylinux_2_28_aarch64" in MANYLINUX_IMAGES
        assert "musllinux_1_2_aarch64" in MANYLINUX_IMAGES

    def test_images_use_quay(self):
        """Test that images use quay.io registry."""
        for name, url in MANYLINUX_IMAGES.items():
            assert url.startswith("quay.io/pypa/"), f"{name} should use quay.io/pypa/"

    def test_default_images(self):
        """Test default image selections."""
        assert "manylinux" in DEFAULT_IMAGES
        assert "musllinux" in DEFAULT_IMAGES
        assert DEFAULT_IMAGES["manylinux"] == "manylinux_2_28_x86_64"
        assert DEFAULT_IMAGES["musllinux"] == "musllinux_1_2_x86_64"


class TestManylinuxPythonPaths:
    """Tests for Python path constants."""

    def test_python_versions_supported(self):
        """Test that common Python versions are supported."""
        assert "3.9" in MANYLINUX_PYTHON_PATHS
        assert "3.10" in MANYLINUX_PYTHON_PATHS
        assert "3.11" in MANYLINUX_PYTHON_PATHS
        assert "3.12" in MANYLINUX_PYTHON_PATHS

    def test_python_paths_format(self):
        """Test that Python paths follow expected format."""
        for version, path in MANYLINUX_PYTHON_PATHS.items():
            assert path.startswith("/opt/python/cp")
            assert path.endswith("/bin/python")
            # Version should be in path (without dot)
            version_nodot = version.replace(".", "")
            assert version_nodot in path


class TestDockerIsolation:
    """Tests for DockerIsolation class."""

    def test_init_default_config(self):
        """Test initialization with default config."""
        isolation = DockerIsolation()

        assert isolation.config.platform == "auto"
        assert isolation._docker_available is None
        assert isolation._docker_path is None

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = DockerConfig(platform="musllinux", architecture="aarch64")
        isolation = DockerIsolation(config)

        assert isolation.config.platform == "musllinux"
        assert isolation.config.architecture == "aarch64"

    @pytest.mark.asyncio
    async def test_check_available_no_docker(self):
        """Test check_available when docker is not installed."""
        isolation = DockerIsolation()

        with patch("shutil.which", return_value=None):
            result = await isolation.check_available()

        assert result is False
        assert isolation._docker_available is False

    @pytest.mark.asyncio
    async def test_check_available_docker_not_running(self):
        """Test check_available when docker is installed but not running."""
        isolation = DockerIsolation()

        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with patch("shutil.which", return_value="/usr/bin/docker"):
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                result = await isolation.check_available()

        assert result is False

    @pytest.mark.asyncio
    async def test_check_available_docker_running(self):
        """Test check_available when docker is running."""
        isolation = DockerIsolation()

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with patch("shutil.which", return_value="/usr/bin/docker"):
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                result = await isolation.check_available()

        assert result is True
        assert isolation._docker_available is True

    @pytest.mark.asyncio
    async def test_check_available_caches_result(self):
        """Test that check_available caches the result."""
        isolation = DockerIsolation()
        isolation._docker_available = True

        # Should return cached value without checking
        result = await isolation.check_available()
        assert result is True

    def test_get_container_python_exact_match(self):
        """Test getting Python path with exact version match."""
        isolation = DockerIsolation()

        path = isolation._get_container_python("3.12")
        assert path == "/opt/python/cp312-cp312/bin/python"

    def test_get_container_python_major_minor(self):
        """Test getting Python path with major.minor version."""
        isolation = DockerIsolation()

        path = isolation._get_container_python("3.11.5")
        assert path == "/opt/python/cp311-cp311/bin/python"

    def test_get_container_python_fallback(self):
        """Test getting Python path with unknown version falls back to 3.12."""
        isolation = DockerIsolation()

        path = isolation._get_container_python("3.99")
        assert path == "/opt/python/cp312-cp312/bin/python"

    def test_build_env_vars(self):
        """Test environment variable generation."""
        isolation = DockerIsolation()

        env = isolation._build_env_vars()

        assert env["DEBIAN_FRONTEND"] == "noninteractive"
        assert env["PIP_NO_CACHE_DIR"] == "1"
        assert env["PIP_DISABLE_PIP_VERSION_CHECK"] == "1"
        assert env["PYTHONDONTWRITEBYTECODE"] == "1"

    def test_build_env_vars_with_extra(self):
        """Test environment variables with extra vars from config."""
        config = DockerConfig(extra_env={"MY_VAR": "value", "ANOTHER": "test"})
        isolation = DockerIsolation(config)

        env = isolation._build_env_vars()

        assert env["MY_VAR"] == "value"
        assert env["ANOTHER"] == "test"

    @pytest.mark.asyncio
    async def test_build_docker_command_basic(self):
        """Test basic docker command generation."""
        isolation = DockerIsolation()
        source_dir = Path("/src/project")
        output_dir = Path("/output")

        cmd = await isolation._build_docker_command(
            image="quay.io/pypa/manylinux_2_28_x86_64",
            source_dir=source_dir,
            output_dir=output_dir,
        )

        assert cmd[0] == "docker"
        assert cmd[1] == "run"
        assert "--rm" in cmd
        assert "quay.io/pypa/manylinux_2_28_x86_64" in cmd

    @pytest.mark.asyncio
    async def test_build_docker_command_with_limits(self):
        """Test docker command with resource limits."""
        config = DockerConfig(memory_limit="4g", cpu_limit=2.0)
        isolation = DockerIsolation(config)
        source_dir = Path("/src/project")
        output_dir = Path("/output")

        cmd = await isolation._build_docker_command(
            image="test-image",
            source_dir=source_dir,
            output_dir=output_dir,
        )

        assert "--memory" in cmd
        assert "4g" in cmd
        assert "--cpus" in cmd
        assert "2.0" in cmd

    @pytest.mark.asyncio
    async def test_build_docker_command_no_network(self):
        """Test docker command with network disabled."""
        config = DockerConfig(network=False)
        isolation = DockerIsolation(config)
        source_dir = Path("/src/project")
        output_dir = Path("/output")

        cmd = await isolation._build_docker_command(
            image="test-image",
            source_dir=source_dir,
            output_dir=output_dir,
        )

        assert "--network=none" in cmd

    def test_generate_build_script_wheel_only(self):
        """Test build script generation for wheel only."""
        isolation = DockerIsolation()

        script = isolation._generate_build_script(
            python_path="/opt/python/cp312-cp312/bin/python",
            build_requirements=["hatchling"],
            build_wheel=True,
            build_sdist=False,
            config_settings=None,
            repair_wheel=True,
        )

        assert "set -ex" in script
        assert "/opt/python/cp312-cp312/bin/python" in script
        assert "pip install" in script
        assert "hatchling" in script
        assert "--wheel" in script
        assert "auditwheel repair" in script

    def test_generate_build_script_sdist_only(self):
        """Test build script generation for sdist only."""
        isolation = DockerIsolation()

        script = isolation._generate_build_script(
            python_path="/opt/python/cp312-cp312/bin/python",
            build_requirements=[],
            build_wheel=False,
            build_sdist=True,
            config_settings=None,
            repair_wheel=False,
        )

        assert "--sdist" in script
        assert "--wheel" not in script
        # auditwheel is installed but not used for sdist
        assert "auditwheel repair" not in script

    def test_generate_build_script_with_config_settings(self):
        """Test build script with config settings."""
        isolation = DockerIsolation()

        script = isolation._generate_build_script(
            python_path="/opt/python/cp312-cp312/bin/python",
            build_requirements=[],
            build_wheel=True,
            build_sdist=False,
            config_settings={"key": "value"},
            repair_wheel=False,
        )

        assert "--config-setting=key=value" in script

    def test_generate_build_script_no_repair(self):
        """Test build script without wheel repair."""
        isolation = DockerIsolation()

        script = isolation._generate_build_script(
            python_path="/opt/python/cp312-cp312/bin/python",
            build_requirements=[],
            build_wheel=True,
            build_sdist=False,
            config_settings=None,
            repair_wheel=False,
        )

        # auditwheel is installed but repair step is skipped
        assert "auditwheel repair" not in script
        assert "cp /tmp/dist/*" in script

    @pytest.mark.asyncio
    async def test_list_available_images(self):
        """Test listing available images."""
        isolation = DockerIsolation()

        images = await isolation.list_available_images()

        assert images == MANYLINUX_IMAGES
        # Should be a copy, not the original
        images["test"] = "test"
        assert "test" not in MANYLINUX_IMAGES

    @pytest.mark.asyncio
    async def test_create_environment_no_docker(self):
        """Test create_environment fails without Docker."""
        isolation = DockerIsolation()
        isolation._docker_available = False

        with pytest.raises(Exception) as exc_info:
            await isolation.create_environment(
                python_version="3.12",
                build_requirements=[],
            )

        assert "Docker is not available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_environment_success(self):
        """Test successful environment creation."""
        isolation = DockerIsolation()

        # Mock Docker as available
        isolation._docker_available = True

        # Mock image selection
        with patch.object(
            isolation, "_select_image", return_value="quay.io/pypa/manylinux_2_28_x86_64"
        ):
            env = await isolation.create_environment(
                python_version="3.12",
                build_requirements=["hatchling"],
            )

        # Check environment was created
        assert env is not None
        assert "__HWB_DOCKER_IMAGE__" in env.env_vars
        assert env.env_vars["__HWB_DOCKER_IMAGE__"] == "quay.io/pypa/manylinux_2_28_x86_64"
        assert "__HWB_DOCKER_PYTHON__" in env.env_vars
        assert "__HWB_BUILD_REQS__" in env.env_vars

        # Build requirements should be JSON encoded
        reqs = json.loads(env.env_vars["__HWB_BUILD_REQS__"])
        assert reqs == ["hatchling"]

        # Cleanup
        await env.cleanup()

    @pytest.mark.asyncio
    async def test_select_image_explicit(self):
        """Test image selection with explicit image."""
        config = DockerConfig(image="my-custom-image:latest")
        isolation = DockerIsolation(config)

        image = await isolation._select_image("3.12")

        assert image == "my-custom-image:latest"

    @pytest.mark.asyncio
    async def test_select_image_manylinux(self):
        """Test image selection for manylinux platform."""
        config = DockerConfig(platform="manylinux")
        isolation = DockerIsolation(config)

        # Mock ensure_image to avoid actual Docker calls
        with patch.object(isolation, "_ensure_image", return_value=None):
            image = await isolation._select_image("3.12")

        assert "manylinux" in image
        assert "quay.io/pypa/" in image

    @pytest.mark.asyncio
    async def test_select_image_musllinux(self):
        """Test image selection for musllinux platform."""
        config = DockerConfig(platform="musllinux")
        isolation = DockerIsolation(config)

        with patch.object(isolation, "_ensure_image", return_value=None):
            image = await isolation._select_image("3.12")

        assert "musllinux" in image

    @pytest.mark.asyncio
    async def test_select_image_aarch64(self):
        """Test image selection for ARM64 architecture."""
        config = DockerConfig(platform="manylinux", architecture="aarch64")
        isolation = DockerIsolation(config)

        with patch.object(isolation, "_ensure_image", return_value=None):
            image = await isolation._select_image("3.12")

        assert "aarch64" in image


class TestGetDockerIsolation:
    """Tests for get_docker_isolation convenience function."""

    @pytest.mark.asyncio
    async def test_get_docker_isolation_not_available(self):
        """Test get_docker_isolation when Docker is not available."""
        with patch.object(DockerIsolation, "check_available", return_value=False):
            with pytest.raises(Exception) as exc_info:
                await get_docker_isolation()

            assert "Docker is not available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_docker_isolation_success(self):
        """Test successful get_docker_isolation."""
        with patch.object(DockerIsolation, "check_available", return_value=True):
            isolation = await get_docker_isolation(
                platform="manylinux",
                architecture="x86_64",
            )

        assert isinstance(isolation, DockerIsolation)
        assert isolation.config.platform == "manylinux"
        assert isolation.config.architecture == "x86_64"


class TestDockerBuildInContainer:
    """Tests for build_in_container method."""

    @pytest.fixture
    def mock_isolation(self):
        """Create a DockerIsolation with mocked Docker."""
        isolation = DockerIsolation()
        isolation._docker_available = True
        return isolation

    @pytest.mark.asyncio
    async def test_build_in_container_success(self, mock_isolation, tmp_path):
        """Test successful build in container."""
        source_dir = tmp_path / "src"
        source_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create a fake wheel in output after "build"
        wheel_name = "mypackage-1.0.0-py3-none-manylinux_2_28_x86_64.whl"

        # Mock the subprocess
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"Build complete", b""))

        # Create environment
        from headless_wheel_builder.isolation.base import BuildEnvironment

        env = BuildEnvironment(
            python_path=Path("/opt/python/cp312-cp312/bin/python"),
            site_packages=Path("/tmp/site-packages"),
            env_vars={
                "__HWB_DOCKER_IMAGE__": "quay.io/pypa/manylinux_2_28_x86_64",
                "__HWB_DOCKER_PYTHON__": "/opt/python/cp312-cp312/bin/python",
                "__HWB_BUILD_REQS__": "[]",
            },
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            # Create the wheel file after the mock is set up
            (output_dir / wheel_name).write_bytes(b"fake wheel content")

            wheel_path, sdist_path, log = await mock_isolation.build_in_container(
                source_dir=source_dir,
                output_dir=output_dir,
                env=env,
                build_wheel=True,
                build_sdist=False,
            )

        assert wheel_path is not None
        assert wheel_path.name == wheel_name
        assert sdist_path is None
        assert "Build complete" in log

    @pytest.mark.asyncio
    async def test_build_in_container_failure(self, mock_isolation, tmp_path):
        """Test build failure in container."""
        source_dir = tmp_path / "src"
        source_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"Error: build failed", b""))

        from headless_wheel_builder.isolation.base import BuildEnvironment

        env = BuildEnvironment(
            python_path=Path("/opt/python/cp312-cp312/bin/python"),
            site_packages=Path("/tmp/site-packages"),
            env_vars={
                "__HWB_DOCKER_IMAGE__": "quay.io/pypa/manylinux_2_28_x86_64",
                "__HWB_DOCKER_PYTHON__": "/opt/python/cp312-cp312/bin/python",
                "__HWB_BUILD_REQS__": "[]",
            },
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with pytest.raises(Exception) as exc_info:
                await mock_isolation.build_in_container(
                    source_dir=source_dir,
                    output_dir=output_dir,
                    env=env,
                    build_wheel=True,
                    build_sdist=False,
                )

            assert "Docker build failed" in str(exc_info.value)
