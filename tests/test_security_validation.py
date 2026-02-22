"""Tests for security validation module."""

import os
import tempfile
from pathlib import Path
from typing import ClassVar

import pytest

from headless_wheel_builder.exceptions import BuildError, IsolationError
from headless_wheel_builder.security_validation import (
    SUPPORTED_PYTHON_VERSIONS,
    AtomicFileWriter,
    ensure_deterministic_image,
    safe_cleanup_wheels,
    validate_cleanup_path,
    validate_python_version,
    validate_wheel_path,
)


class TestValidatePythonVersion:
    """Test Python version validation."""

    def test_valid_versions(self):
        """Test that valid versions pass validation."""
        for version in SUPPORTED_PYTHON_VERSIONS:
            validate_python_version(version)  # Should not raise

    def test_valid_versions_with_patch(self):
        """Test that versions with patch numbers pass validation."""
        validate_python_version("3.10.5")
        validate_python_version("3.11.0")
        validate_python_version("3.12.10")

    def test_invalid_version(self):
        """Test that invalid versions raise IsolationError."""
        with pytest.raises(IsolationError, match="Unsupported Python version"):
            validate_python_version("3.8")

    def test_invalid_version_with_patch(self):
        """Test that invalid versions with patch raise IsolationError."""
        with pytest.raises(IsolationError, match="Unsupported Python version"):
            validate_python_version("2.7.18")

    def test_invalid_version_empty(self):
        """Test that empty version is handled."""
        with pytest.raises(IsolationError):
            validate_python_version("")

    def test_invalid_version_format(self):
        """Test that malformed versions are rejected."""
        with pytest.raises(IsolationError):
            validate_python_version("python3.10")


class TestValidateWheelPath:
    """Test wheel path validation."""

    def test_valid_relative_paths(self):
        """Test that valid relative paths pass validation."""
        validate_wheel_path("dist/package-1.0-py3-none-any.whl")
        validate_wheel_path("./dist/wheel.whl")
        validate_wheel_path("output.whl")

    @pytest.mark.skipif(os.name == "nt", reason="Unix path test")
    def test_unix_absolute_path_rejected(self):
        """Test that Unix absolute paths are rejected."""
        with pytest.raises(BuildError, match="Absolute paths not allowed"):
            validate_wheel_path("/etc/passwd")

    def test_directory_traversal_rejected(self):
        """Test that directory traversal attempts are rejected."""
        with pytest.raises(BuildError, match="Directory traversal"):
            validate_wheel_path("../etc/passwd")

    def test_directory_traversal_in_middle_rejected(self):
        """Test that .. in middle of path is rejected."""
        with pytest.raises(BuildError, match="Directory traversal"):
            validate_wheel_path("dist/../../../etc/passwd")

    def test_hyphen_prefix_rejected(self):
        """Test that path components starting with hyphen are rejected."""
        with pytest.raises(BuildError, match="Invalid path component"):
            validate_wheel_path("dist/-malicious.whl")


class TestValidateCleanupPath:
    """Test cleanup path validation."""

    def test_valid_cleanup_paths(self):
        """Test that valid cleanup paths pass validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a project-like subdirectory
            project_dir = Path(tmpdir) / "my_project" / "dist"
            project_dir.mkdir(parents=True)
            validate_cleanup_path(project_dir)  # Should not raise

    @pytest.mark.skipif(os.name == "nt", reason="Unix path test")
    def test_dangerous_unix_paths_rejected(self):
        """Test that dangerous Unix paths are rejected."""
        for path in ["/", "/home", "/root", "/var", "/opt", "/usr"]:
            with pytest.raises(BuildError, match="Cannot clean critical"):
                validate_cleanup_path(path)

    def test_nonexistent_path_rejected(self):
        """Test that nonexistent paths are rejected."""
        with pytest.raises(BuildError, match="does not exist"):
            # Use a path that definitely doesn't exist
            nonexistent = Path("/nonexistent_project_dir_xyz123_that_will_never_exist_12345")
            if nonexistent.exists():
                nonexistent = Path("/another_nonexistent_path_xyz_9999")
            validate_cleanup_path(nonexistent)

    def test_file_path_rejected(self):
        """Test that file paths (not directories) are rejected."""
        with tempfile.NamedTemporaryFile() as tmpfile, pytest.raises(BuildError, match="not a directory"):
            validate_cleanup_path(tmpfile.name)


class TestSafeCleanupWheels:
    """Test safe wheel cleanup."""

    def test_cleanup_wheels_only(self):
        """Test that only wheel files are deleted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "my_project" / "dist"
            project_dir.mkdir(parents=True)

            # Create test files
            (project_dir / "package-1.0-py3-none-any.whl").touch()
            (project_dir / "package-1.0.tar.gz").touch()
            (project_dir / "README.md").touch()
            (project_dir / "setup.py").touch()

            # Clean
            deleted = safe_cleanup_wheels(project_dir)

            # Check results
            assert deleted == 2
            assert not (project_dir / "package-1.0-py3-none-any.whl").exists()
            assert not (project_dir / "package-1.0.tar.gz").exists()
            assert (project_dir / "README.md").exists()
            assert (project_dir / "setup.py").exists()

    def test_cleanup_handles_nonexistent_dir(self):
        """Test that nonexistent directory raises error."""
        nonexistent = Path("/nonexistent_project_xyz_123_456_789_that_wont_exist")
        if nonexistent.exists():
            nonexistent = Path("/another_nonexistent_project_xyz_999")
        with pytest.raises(BuildError, match="does not exist"):
            safe_cleanup_wheels(nonexistent)

    def test_cleanup_empty_directory(self):
        """Test cleaning empty directory returns 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "my_project"
            project_dir.mkdir()
            deleted = safe_cleanup_wheels(project_dir)
            assert deleted == 0


class TestEnsureDeterministicImage:
    """Test Docker image determinism."""

    IMAGES: ClassVar[dict[str, str]] = {
        "manylinux_2_28_x86_64": "quay.io/pypa/manylinux_2_28_x86_64",
        "manylinux_2_34_x86_64": "quay.io/pypa/manylinux_2_34_x86_64",
    }

    def test_known_image_key(self):
        """Test that known image keys are resolved."""
        result = ensure_deterministic_image("manylinux_2_28_x86_64", self.IMAGES)
        assert result == "quay.io/pypa/manylinux_2_28_x86_64"

    def test_full_image_url(self):
        """Test that full image URLs are recognized."""
        result = ensure_deterministic_image(
            "quay.io/pypa/manylinux_2_28_x86_64", self.IMAGES
        )
        assert result == "quay.io/pypa/manylinux_2_28_x86_64"

    def test_unknown_image_key(self):
        """Test that unknown image keys raise error."""
        with pytest.raises(IsolationError, match="Unknown image key"):
            ensure_deterministic_image("unknown_image", self.IMAGES)

    def test_unsupported_image_url(self):
        """Test that unsupported full URLs raise error."""
        with pytest.raises(IsolationError, match="Unknown or unsupported image"):
            ensure_deterministic_image("quay.io/pypa/unknown_image", self.IMAGES)


class TestAtomicFileWriter:
    """Test atomic file writing."""

    def test_successful_write(self):
        """Test successful atomic write."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "output.txt"

            with AtomicFileWriter(target, binary=False) as temp_path, temp_path.open("w") as f:
                f.write("test data")

            assert target.exists()
            assert target.read_text() == "test data"

    def test_atomic_write_with_exception(self):
        """Test that temp file is cleaned up on exception."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "output.txt"

            try:
                with AtomicFileWriter(target, binary=False) as temp_path:
                    with temp_path.open("w") as f:
                        f.write("partial data")
                    raise ValueError("Simulated error")
            except ValueError:
                pass

            # Target should not exist
            assert not target.exists()

            # Temp files should be cleaned up
            temp_files = list(Path(tmpdir).glob(".tmp_*"))
            assert len(temp_files) == 0

    def test_atomic_write_binary_mode(self):
        """Test binary mode atomic write."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "output.bin"
            test_data = b"binary test data"

            with AtomicFileWriter(target, binary=True) as temp_path, temp_path.open("wb") as f:
                f.write(test_data)

            assert target.exists()
            assert target.read_bytes() == test_data
