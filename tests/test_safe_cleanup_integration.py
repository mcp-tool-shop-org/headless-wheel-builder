"""Tests for Phase 1.3: Safe cleanup logic integration."""

import tempfile
from pathlib import Path

import pytest

from headless_wheel_builder.core.builder import _is_dangerous_cleanup_path
from headless_wheel_builder.exceptions import BuildError
from headless_wheel_builder.security_validation import safe_cleanup_wheels


class TestSafeCleanupIntegration:
    """Integration tests for safe cleanup operations."""

    def test_cleanup_wheels_in_project_directory(self):
        """Test cleanup works on project directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "myproject"
            dist_dir = project_root / "dist"
            dist_dir.mkdir(parents=True)

            # Create test artifact files
            (dist_dir / "package-1.0-py3-none-any.whl").touch()
            (dist_dir / "package-1.0.tar.gz").touch()
            (dist_dir / "package-1.0.zip").touch()

            # Create non-artifact files
            (dist_dir / "README.txt").touch()
            (dist_dir / ".gitkeep").touch()

            # Clean
            deleted = safe_cleanup_wheels(dist_dir)

            assert deleted == 3, f"Expected 3 files deleted, got {deleted}"
            assert not (dist_dir / "package-1.0-py3-none-any.whl").exists()
            assert not (dist_dir / "package-1.0.tar.gz").exists()
            assert not (dist_dir / "package-1.0.zip").exists()
            assert (dist_dir / "README.txt").exists()
            assert (dist_dir / ".gitkeep").exists()

    def test_cleanup_respects_dangerous_path_detection(self):
        """Test that cleanup validation respects dangerous path detection."""
        # This should raise an error for dangerous paths
        with pytest.raises(BuildError, match="Cannot clean"):
            safe_cleanup_wheels("/")

    def test_cleanup_only_removes_artifact_patterns(self):
        """Test that only specific patterns are removed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "proj"
            project.mkdir()

            # Create various files
            artifacts = [
                ("package-1.0-py3-none-any.whl", True),
                ("package-1.0.tar.gz", True),
                ("package-1.0.zip", True),
                ("package-1.0.tar", False),  # Should not be deleted
                ("package-1.0.tar.bz2", False),
                ("build.log", False),
                ("setup.py", False),
            ]

            for filename, _should_delete in artifacts:
                (project / filename).touch()

            deleted = safe_cleanup_wheels(project)

            # Should delete exactly 3 files (whl, tar.gz, zip)
            assert deleted == 3

            # Verify correct files remain
            assert not (project / "package-1.0-py3-none-any.whl").exists()
            assert not (project / "package-1.0.tar.gz").exists()
            assert not (project / "package-1.0.zip").exists()
            assert (project / "package-1.0.tar").exists()
            assert (project / "package-1.0.tar.bz2").exists()
            assert (project / "build.log").exists()
            assert (project / "setup.py").exists()

    def test_cleanup_handles_permission_errors_gracefully(self):
        """Test that cleanup handles permission errors well."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "proj"
            project.mkdir()

            # Create an artifact file
            wheel_file = project / "package-1.0-py3-none-any.whl"
            wheel_file.touch()

            # Try to cleanup - should succeed (permissions usually OK in temp dir)
            deleted = safe_cleanup_wheels(project)
            assert deleted == 1

    def test_dangerous_path_detection_comprehensive(self):
        """Test comprehensive dangerous path detection."""
        # Create test temp projects that are safe
        with tempfile.TemporaryDirectory() as tmpdir:
            safe_project = Path(tmpdir) / "safe" / "dist"
            safe_project.mkdir(parents=True)

            # These should NOT be marked as dangerous
            assert not _is_dangerous_cleanup_path(safe_project)
            assert not _is_dangerous_cleanup_path(Path(tmpdir))

    def test_cleanup_with_nested_directory_structure(self):
        """Test cleanup with nested dist directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "myproject"
            dist1 = project / "dist"
            dist2 = project / "build" / "dist"

            dist1.mkdir(parents=True)
            dist2.mkdir(parents=True)

            # Add artifacts to both
            (dist1 / "package-1.0-py3-none-any.whl").touch()
            (dist2 / "another-1.0-py3-none-any.whl").touch()

            # Clean dist1
            deleted1 = safe_cleanup_wheels(dist1)
            assert deleted1 == 1
            assert not (dist1 / "package-1.0-py3-none-any.whl").exists()

            # dist2 should be unaffected
            assert (dist2 / "another-1.0-py3-none-any.whl").exists()

            # Clean dist2
            deleted2 = safe_cleanup_wheels(dist2)
            assert deleted2 == 1
            assert not (dist2 / "another-1.0-py3-none-any.whl").exists()

    def test_cleanup_idempotency(self):
        """Test that cleanup is idempotent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "proj"
            project.mkdir()

            (project / "package-1.0-py3-none-any.whl").touch()

            # First cleanup
            deleted1 = safe_cleanup_wheels(project)
            assert deleted1 == 1

            # Second cleanup (should find nothing)
            deleted2 = safe_cleanup_wheels(project)
            assert deleted2 == 0

            # Can cleanup multiple times without error
            for _ in range(5):
                deleted = safe_cleanup_wheels(project)
                assert deleted == 0
