"""Tests for builder wheel validation hardening."""

import tempfile
import zipfile
from pathlib import Path

import pytest

from headless_wheel_builder.core.builder import BuildEngine, _is_dangerous_cleanup_path
from headless_wheel_builder.exceptions import BuildError


class TestWheelValidationHardening:
    """Test hardened wheel validation."""

    @staticmethod
    def create_valid_wheel(path: Path, has_wheel: bool = True, has_metadata: bool = True):
        """Create a valid test wheel file."""
        with zipfile.ZipFile(path, "w") as whl:
            if has_wheel:
                whl.writestr("package-1.0.dist-info/WHEEL", "Wheel-Version: 1.0\n")
            if has_metadata:
                whl.writestr("package-1.0.dist-info/METADATA", "Name: package\nVersion: 1.0\n")
            whl.writestr("package/__init__.py", "")

    def test_validate_wheel_path_traversal_detection(self):
        """Test that path traversal attempts are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a wheel with path traversal attempt
            wheel_path = Path(tmpdir) / "package.whl"
            with zipfile.ZipFile(wheel_path, "w") as whl:
                whl.writestr("package-1.0.dist-info/WHEEL", "Wheel-Version: 1.0\n")
                whl.writestr("package-1.0.dist-info/METADATA", "Name: package\n")
                # Add a file with path traversal
                whl.writestr("../evil.py", "import os; os.system('rm -rf /')")

            # Should still validate the unsafe path
            builder = BuildEngine(config=None)
            with pytest.raises(BuildError, match="unsafe path"):
                builder._validate_wheel(wheel_path)

    def test_validate_wheel_absolute_path_in_archive(self):
        """Test that absolute paths in wheel are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wheel_path = Path(tmpdir) / "package.whl"
            with zipfile.ZipFile(wheel_path, "w") as whl:
                whl.writestr("package-1.0.dist-info/WHEEL", "Wheel-Version: 1.0\n")
                whl.writestr("package-1.0.dist-info/METADATA", "Name: package\n")
                # Add a file with absolute path
                whl.writestr("/etc/passwd", "bad content")

            builder = BuildEngine(config=None)
            with pytest.raises(BuildError, match="unsafe path"):
                builder._validate_wheel(wheel_path)

    def test_validate_wheel_missing_metadata(self):
        """Test that wheels missing METADATA are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wheel_path = Path(tmpdir) / "package.whl"
            self.create_valid_wheel(wheel_path, has_metadata=False)

            builder = BuildEngine(config=None)
            with pytest.raises(BuildError, match="missing METADATA"):
                builder._validate_wheel(wheel_path)

    def test_validate_wheel_missing_wheel_file(self):
        """Test that wheels missing WHEEL are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wheel_path = Path(tmpdir) / "package.whl"
            self.create_valid_wheel(wheel_path, has_wheel=False)

            builder = BuildEngine(config=None)
            with pytest.raises(BuildError, match="missing WHEEL"):
                builder._validate_wheel(wheel_path)

    def test_validate_valid_wheel(self):
        """Test that valid wheels pass validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            wheel_path = Path(tmpdir) / "package-1.0-py3-none-any.whl"
            self.create_valid_wheel(wheel_path)

            builder = BuildEngine(config=None)
            # Should not raise
            builder._validate_wheel(wheel_path)


class TestDangerousCleanupPath:
    """Test dangerous cleanup path detection."""

    def test_dangerous_cleanup_path_detection(self):
        """Test that dangerous paths are properly detected."""
        # Test system directories are detected
        dangerous_paths = [Path("/"), Path.home(), Path("/usr"), Path("/var"), Path("/etc")]

        for path in dangerous_paths:
            if path.exists():  # Only test if path exists on current system
                assert _is_dangerous_cleanup_path(path), f"Should detect {path} as dangerous"

    def test_project_directory_not_dangerous(self):
        """Test that project directories are not marked as dangerous."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "my_project" / "dist"
            project_dir.mkdir(parents=True)
            assert not _is_dangerous_cleanup_path(project_dir), (
                "Project dir should not be dangerous"
            )
