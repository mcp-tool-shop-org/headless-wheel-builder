"""Tests for publishing module."""

from __future__ import annotations

import os
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from headless_wheel_builder.publish.base import (
    PublishConfig,
    PublishResult,
)
from headless_wheel_builder.publish.pypi import (
    PYPI_URL,
    TEST_PYPI_URL,
    PyPIConfig,
    PyPIPublisher,
)
from headless_wheel_builder.publish.s3 import S3Config, S3Publisher


class TestPublishConfig:
    """Tests for PublishConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PublishConfig()

        assert config.files == []
        assert config.skip_existing is False
        assert config.dry_run is False
        assert config.verbose is False
        assert config.metadata == {}

    def test_custom_config(self):
        """Test custom configuration."""
        files = [Path("dist/test.whl")]
        config = PublishConfig(
            files=files,
            skip_existing=True,
            dry_run=True,
            verbose=True,
            metadata={"key": "value"},
        )

        assert config.files == files
        assert config.skip_existing is True
        assert config.dry_run is True
        assert config.verbose is True
        assert config.metadata == {"key": "value"}


class TestPublishResult:
    """Tests for PublishResult dataclass."""

    def test_default_result(self):
        """Test default result values."""
        result = PublishResult(success=True)

        assert result.success is True
        assert result.files_published == []
        assert result.files_skipped == []
        assert result.files_failed == []
        assert result.errors == []
        assert result.urls == []

    def test_failure_factory(self):
        """Test failure factory method."""
        result = PublishResult.failure("Something went wrong")

        assert result.success is False
        assert result.errors == ["Something went wrong"]

    def test_add_published(self):
        """Test adding published file."""
        result = PublishResult(success=True)
        path = Path("dist/test.whl")

        result.add_published(path, "https://pypi.org/project/test/1.0.0/")

        assert path in result.files_published
        assert "https://pypi.org/project/test/1.0.0/" in result.urls

    def test_add_skipped(self):
        """Test adding skipped file."""
        result = PublishResult(success=True)
        path = Path("dist/test.whl")

        result.add_skipped(path, "Already exists")

        assert path in result.files_skipped
        assert "Skipped" in result.errors[0]
        assert "Already exists" in result.errors[0]

    def test_add_failed(self):
        """Test adding failed file."""
        result = PublishResult(success=True)
        path = Path("dist/test.whl")

        result.add_failed(path, "Upload error")

        assert path in result.files_failed
        assert result.success is False
        assert "Failed" in result.errors[0]
        assert "Upload error" in result.errors[0]


class TestPyPIConfig:
    """Tests for PyPIConfig dataclass."""

    def test_default_config(self):
        """Test default PyPI configuration."""
        config = PyPIConfig()

        assert config.repository == "pypi"
        assert config.repository_url is None
        assert config.token is None
        assert config.username is None
        assert config.password is None
        assert config.use_trusted_publisher is False
        assert config.attestations is False
        assert config.verify_ssl is True
        assert config.max_retries == 3

    def test_testpypi_config(self):
        """Test TestPyPI configuration."""
        config = PyPIConfig(repository="testpypi", token="test-token")

        assert config.repository == "testpypi"
        assert config.token == "test-token"


class TestPyPIPublisher:
    """Tests for PyPIPublisher class."""

    def test_init_default_config(self):
        """Test initialization with default config."""
        publisher = PyPIPublisher()

        assert publisher.config.repository == "pypi"

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = PyPIConfig(repository="testpypi")
        publisher = PyPIPublisher(config)

        assert publisher.config.repository == "testpypi"

    def test_get_repository_url_pypi(self):
        """Test getting PyPI URL."""
        publisher = PyPIPublisher(PyPIConfig(repository="pypi"))

        url = publisher._get_repository_url()

        assert url == PYPI_URL

    def test_get_repository_url_testpypi(self):
        """Test getting TestPyPI URL."""
        publisher = PyPIPublisher(PyPIConfig(repository="testpypi"))

        url = publisher._get_repository_url()

        assert url == TEST_PYPI_URL

    def test_get_repository_url_custom(self):
        """Test getting custom repository URL."""
        publisher = PyPIPublisher(
            PyPIConfig(repository="custom", repository_url="https://my-pypi.example.com/simple/")
        )

        url = publisher._get_repository_url()

        assert url == "https://my-pypi.example.com/simple/"

    def test_get_credentials_from_token(self):
        """Test getting credentials from token."""
        publisher = PyPIPublisher(PyPIConfig(token="my-token"))

        username, password = publisher._get_credentials()

        assert username == "__token__"
        assert password == "my-token"

    def test_get_credentials_from_username_password(self):
        """Test getting credentials from username/password."""
        publisher = PyPIPublisher(PyPIConfig(username="user", password="pass"))

        username, password = publisher._get_credentials()

        assert username == "user"
        assert password == "pass"

    def test_get_credentials_from_env(self):
        """Test getting credentials from environment."""
        publisher = PyPIPublisher()

        with patch.dict(os.environ, {"PYPI_TOKEN": "env-token"}):
            username, password = publisher._get_credentials()

        assert username == "__token__"
        assert password == "env-token"

    def test_get_credentials_none(self):
        """Test getting credentials when none available."""
        publisher = PyPIPublisher()

        with patch.dict(os.environ, {}, clear=True):
            # Clear any existing env vars
            for key in ["PYPI_TOKEN", "TWINE_PASSWORD", "TWINE_USERNAME", "TEST_PYPI_TOKEN"]:
                os.environ.pop(key, None)

            username, password = publisher._get_credentials()

        assert username is None
        assert password is None

    @pytest.mark.asyncio
    async def test_check_credentials_with_token(self):
        """Test check_credentials with token."""
        publisher = PyPIPublisher(PyPIConfig(token="my-token"))

        result = await publisher.check_credentials()

        assert result is True

    @pytest.mark.asyncio
    async def test_check_credentials_no_credentials(self):
        """Test check_credentials without credentials."""
        publisher = PyPIPublisher()

        with patch.dict(os.environ, {}, clear=True):
            for key in ["PYPI_TOKEN", "TWINE_PASSWORD"]:
                os.environ.pop(key, None)

            result = await publisher.check_credentials()

        assert result is False

    @pytest.mark.asyncio
    async def test_publish_no_files(self):
        """Test publish with no files."""
        publisher = PyPIPublisher(PyPIConfig(token="token"))

        result = await publisher.publish(PublishConfig(files=[]))

        assert result.success is False
        assert "No files to publish" in result.errors[0]

    @pytest.mark.asyncio
    async def test_publish_dry_run(self, tmp_path):
        """Test dry run publishing."""
        # Create a valid wheel file
        wheel_path = tmp_path / "test_package-1.0.0-py3-none-any.whl"
        create_mock_wheel(wheel_path)

        publisher = PyPIPublisher(PyPIConfig(repository="testpypi"))
        config = PublishConfig(files=[wheel_path], dry_run=True)

        result = await publisher.publish(config)

        assert result.success is True
        assert wheel_path in result.files_published
        assert "[DRY RUN]" in result.errors[0]
        assert "test.pypi.org" in result.errors[0]

    @pytest.mark.asyncio
    async def test_publish_invalid_file(self, tmp_path):
        """Test publish with invalid file."""
        # Create an invalid wheel
        bad_wheel = tmp_path / "bad.whl"
        bad_wheel.write_text("not a wheel")

        publisher = PyPIPublisher(PyPIConfig(token="token"))
        config = PublishConfig(files=[bad_wheel])

        result = await publisher.publish(config)

        assert result.success is False
        assert "Invalid wheel file" in result.errors[0]


class TestS3Config:
    """Tests for S3Config dataclass."""

    def test_default_config(self):
        """Test default S3 configuration."""
        config = S3Config(bucket="my-bucket")

        assert config.bucket == "my-bucket"
        assert config.prefix == ""
        assert config.region == "us-east-1"
        assert config.provider == "aws"
        assert config.acl == "private"
        assert config.add_checksums is True
        assert config.generate_index is False

    def test_custom_config(self):
        """Test custom S3 configuration."""
        config = S3Config(
            bucket="wheels",
            prefix="packages/",
            region="eu-west-1",
            provider="minio",
            endpoint_url="http://localhost:9000",
            acl="public-read",
            generate_index=True,
        )

        assert config.bucket == "wheels"
        assert config.prefix == "packages/"
        assert config.region == "eu-west-1"
        assert config.provider == "minio"
        assert config.endpoint_url == "http://localhost:9000"
        assert config.acl == "public-read"
        assert config.generate_index is True


class TestS3Publisher:
    """Tests for S3Publisher class."""

    def test_init_requires_bucket(self):
        """Test that bucket is required."""
        with pytest.raises(ValueError, match="bucket is required"):
            S3Publisher(S3Config(bucket=""))

    def test_init_with_config(self):
        """Test initialization with config."""
        config = S3Config(bucket="my-bucket", region="us-west-2")
        publisher = S3Publisher(config)

        assert publisher.config.bucket == "my-bucket"
        assert publisher.config.region == "us-west-2"

    def test_get_key_no_prefix(self):
        """Test getting S3 key without prefix."""
        publisher = S3Publisher(S3Config(bucket="bucket"))
        path = Path("dist/test-1.0.0-py3-none-any.whl")

        key = publisher._get_key(path)

        assert key == "test-1.0.0-py3-none-any.whl"

    def test_get_key_with_prefix(self):
        """Test getting S3 key with prefix."""
        publisher = S3Publisher(S3Config(bucket="bucket", prefix="wheels/"))
        path = Path("dist/test-1.0.0-py3-none-any.whl")

        key = publisher._get_key(path)

        assert key == "wheels/test-1.0.0-py3-none-any.whl"

    def test_get_public_url_aws(self):
        """Test getting public URL for AWS S3."""
        publisher = S3Publisher(S3Config(bucket="my-bucket", region="us-west-2"))

        url = publisher._get_public_url("wheels/test.whl")

        assert url == "https://my-bucket.s3.us-west-2.amazonaws.com/wheels/test.whl"

    def test_get_public_url_custom(self):
        """Test getting public URL with custom URL."""
        publisher = S3Publisher(S3Config(bucket="bucket", public_url="https://cdn.example.com"))

        url = publisher._get_public_url("test.whl")

        assert url == "https://cdn.example.com/test.whl"

    def test_get_content_type_wheel(self):
        """Test content type for wheel."""
        publisher = S3Publisher(S3Config(bucket="bucket"))

        content_type = publisher._get_content_type(Path("test.whl"))

        assert content_type == "application/zip"

    def test_get_content_type_sdist(self):
        """Test content type for sdist."""
        publisher = S3Publisher(S3Config(bucket="bucket"))

        content_type = publisher._get_content_type(Path("test.tar.gz"))

        assert content_type == "application/gzip"

    def test_calculate_checksums(self, tmp_path):
        """Test checksum calculation."""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"hello world")

        publisher = S3Publisher(S3Config(bucket="bucket"))
        checksums = publisher._calculate_checksums(test_file)

        assert "md5" in checksums
        assert "sha256" in checksums
        assert len(checksums["md5"]) == 32
        assert len(checksums["sha256"]) == 64

    def test_generate_package_index(self):
        """Test PEP 503 index generation."""
        publisher = S3Publisher(S3Config(bucket="bucket"))
        files = [
            {
                "filename": "test-1.0.0-py3-none-any.whl",
                "url": "https://example.com/test.whl",
                "sha256": "abc123",
            },
            {
                "filename": "test-1.0.1-py3-none-any.whl",
                "url": "https://example.com/test2.whl",
                "sha256": "def456",
            },
        ]

        html = publisher._generate_package_index("test", files)

        assert "<title>Links for test</title>" in html
        assert 'href="https://example.com/test.whl#sha256=abc123"' in html
        assert "test-1.0.0-py3-none-any.whl" in html

    def test_generate_root_index(self):
        """Test root index generation."""
        publisher = S3Publisher(S3Config(bucket="bucket"))

        html = publisher._generate_root_index(["package_a", "package_b"])

        assert "<title>Simple Index</title>" in html
        assert 'href="package_a/"' in html
        assert 'href="package_b/"' in html


class TestBasePublisher:
    """Tests for BasePublisher helpers."""

    def test_validate_files_not_found(self):
        """Test validation with missing file."""
        publisher = PyPIPublisher(PyPIConfig(token="token"))

        errors = publisher._validate_files([Path("nonexistent.whl")])

        assert len(errors) == 1
        assert "File not found" in errors[0]

    def test_validate_files_invalid_extension(self, tmp_path):
        """Test validation with invalid extension."""
        bad_file = tmp_path / "test.txt"
        bad_file.write_text("content")

        publisher = PyPIPublisher(PyPIConfig(token="token"))

        errors = publisher._validate_files([bad_file])

        assert len(errors) == 1
        assert "Unknown file type" in errors[0]

    def test_is_valid_wheel(self, tmp_path):
        """Test wheel validation."""
        wheel_path = tmp_path / "test-1.0.0-py3-none-any.whl"
        create_mock_wheel(wheel_path)

        publisher = PyPIPublisher(PyPIConfig(token="token"))

        assert publisher._is_valid_wheel(wheel_path) is True

    def test_is_valid_wheel_invalid(self, tmp_path):
        """Test wheel validation with invalid file."""
        bad_wheel = tmp_path / "bad.whl"
        bad_wheel.write_bytes(b"not a zip")

        publisher = PyPIPublisher(PyPIConfig(token="token"))

        assert publisher._is_valid_wheel(bad_wheel) is False

    def test_get_package_info_from_wheel(self, tmp_path):
        """Test extracting package info from wheel."""
        wheel_path = tmp_path / "my_package-2.0.0-py3-none-any.whl"
        create_mock_wheel(wheel_path, name="my-package", version="2.0.0")

        publisher = PyPIPublisher(PyPIConfig(token="token"))
        info = publisher._get_package_info(wheel_path)

        assert info["name"] == "my-package"
        assert info["version"] == "2.0.0"

    def test_get_package_info_from_sdist(self, tmp_path):
        """Test extracting package info from sdist filename."""
        sdist_path = tmp_path / "my-package-1.2.3.tar.gz"
        sdist_path.write_bytes(b"")  # Empty file for testing

        publisher = PyPIPublisher(PyPIConfig(token="token"))
        info = publisher._get_package_info(sdist_path)

        assert info["name"] == "my-package"
        assert info["version"] == "1.2.3"


# Helper functions


def create_mock_wheel(
    path: Path,
    name: str = "test-package",
    version: str = "1.0.0",
) -> None:
    """Create a minimal valid wheel file for testing."""
    with zipfile.ZipFile(path, "w") as whl:
        # Add WHEEL file
        wheel_content = """Wheel-Version: 1.0
Generator: test
Root-Is-Purelib: true
Tag: py3-none-any
"""
        whl.writestr(f"{name.replace('-', '_')}-{version}.dist-info/WHEEL", wheel_content)

        # Add METADATA file
        metadata_content = f"""Metadata-Version: 2.1
Name: {name}
Version: {version}
"""
        whl.writestr(f"{name.replace('-', '_')}-{version}.dist-info/METADATA", metadata_content)

        # Add RECORD file (can be empty for testing)
        whl.writestr(f"{name.replace('-', '_')}-{version}.dist-info/RECORD", "")
