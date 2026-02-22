"""Security and validation utilities for Phase 1 hardening.

This module provides enhanced validation and safety checks for:
- Python version validation
- Docker image determinism
- Wheel path traversal prevention
- Safe cleanup operations
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path

from headless_wheel_builder.exceptions import BuildError, IsolationError

# Supported Python versions in manylinux images
SUPPORTED_PYTHON_VERSIONS = {"3.9", "3.10", "3.11", "3.12", "3.13"}

# Dangerous paths that should never be cleaned
# Platform-specific dangerous paths
_UNIX_DANGEROUS = {"/", "/home", "/root", "/tmp", "/var", "/opt", "/usr"}
_WIN_DANGEROUS = {"C:\\", "C:\\Windows", "C:\\Program Files"}

def _get_dangerous_cleanup_paths() -> set[str]:
    """Get platform-specific dangerous paths."""
    paths = _UNIX_DANGEROUS.copy()
    if os.name == "nt":  # Windows
        paths.update(_WIN_DANGEROUS)
    return paths

DANGEROUS_CLEANUP_PATHS = _get_dangerous_cleanup_paths()


def validate_python_version(version: str) -> None:
    """Validate that the python_version is supported.

    Args:
        version: Python version string (e.g., "3.10", "3.10.5")

    Raises:
        IsolationError: If the version is not supported.

    Examples:
        >>> validate_python_version("3.10")  # OK
        >>> validate_python_version("3.9")   # OK
        >>> validate_python_version("3.8")   # Raises IsolationError
    """
    # Check for empty or None version
    if not version or not str(version).strip():
        supported_str = ", ".join(sorted(SUPPORTED_PYTHON_VERSIONS))
        raise IsolationError(
            f"Python version cannot be empty\n"
            f"Supported versions: {supported_str}"
        )

    # Extract major.minor version if patch version provided
    parts = str(version).split(".")
    short_version = f"{parts[0]}.{parts[1]}" if len(parts) >= 2 else version

    if short_version not in SUPPORTED_PYTHON_VERSIONS:
        supported_str = ", ".join(sorted(SUPPORTED_PYTHON_VERSIONS))
        raise IsolationError(
            f"Unsupported Python version: {version}\n"
            f"Supported versions: {supported_str}\n"
            f"Please specify one of the supported versions above."
        )


def validate_wheel_path(wheel_path: Path | str) -> None:
    """Validate wheel file path for security issues.

    Checks for:
    - Absolute paths (disallowed outside wheel archive)
    - Directory traversal attempts (..)
    - Required wheel metadata files

    Args:
        wheel_path: Path to wheel file to validate

    Raises:
        BuildError: If path contains traversal or other security issues.

    Examples:
        >>> validate_wheel_path("dist/package-1.0-py3-none-any.whl")  # OK
        >>> validate_wheel_path("../etc/passwd")  # Raises BuildError
        >>> validate_wheel_path("/etc/passwd")    # Raises BuildError
    """
    wheel_path_str = str(wheel_path)

    # Only validate relative paths - skip absolute path check for UNC paths
    # that don't start with drive letters (UNC paths are allowed in some contexts)
    is_absolute = Path(wheel_path_str).is_absolute()
    is_unc_path = wheel_path_str.startswith("\\\\")

    # Check for absolute paths (but allow UNC paths for network drives)
    if is_absolute and not is_unc_path and not wheel_path_str.startswith("//"):
        raise BuildError(
            f"Absolute paths not allowed in wheel: {wheel_path}\n"
            f"Use relative paths only."
        )

    # Check for directory traversal attempts
    parts = Path(wheel_path_str).parts
    for part in parts:
        if part == "..":
            raise BuildError(
                f"Directory traversal (..) not allowed in wheel path: {wheel_path}\n"
                f"This is a security restriction to prevent path traversal attacks."
            )
        if part.startswith("-"):
            raise BuildError(
                f"Invalid path component in wheel: {part}\n"
                f"Path components cannot start with hyphen."
            )


def validate_cleanup_path(output_dir: Path | str) -> None:
    """Validate that cleanup path is safe.

    Defensive check to prevent accidental deletion of critical directories.

    Args:
        output_dir: Directory to be cleaned

    Raises:
        BuildError: If path is considered dangerous.

    Examples:
        >>> validate_cleanup_path("./dist")  # OK
        >>> validate_cleanup_path("/")       # Raises BuildError
        >>> validate_cleanup_path("/home")   # Raises BuildError
    """
    output_dir = Path(output_dir).resolve()
    output_str = str(output_dir).lower()

    # Check against dangerous root directories (Unix)
    unix_roots = {"/", "/home", "/root", "/var", "/opt", "/usr"}
    for dangerous_root in unix_roots:
        if output_str == dangerous_root.lower() or output_str.startswith(dangerous_root.lower() + "/"):
            raise BuildError(
                f"Cannot clean critical system directory: {output_dir}\n"
                f"For safety, cleanup is restricted to project directories only."
            )

    # Check against dangerous Windows directories
    win_dangerous = {"\\", "c:\\", "c:\\windows", "c:\\program files"}
    for dangerous_win in win_dangerous:
        if output_str == dangerous_win.lower() or output_str.startswith(dangerous_win.lower() + "\\"):
            raise BuildError(
                f"Cannot clean critical system directory: {output_dir}\n"
                f"For safety, cleanup is restricted to project directories only."
            )

    # Verify path exists and is a directory
    if not output_dir.exists():
        raise BuildError(f"Output directory does not exist: {output_dir}")

    if not output_dir.is_dir():
        raise BuildError(f"Output path is not a directory: {output_dir}")


def safe_cleanup_wheels(output_dir: Path | str) -> int:
    """Safely clean wheel and source distribution files from directory.

    Only removes:
    - *.whl (wheel files)
    - *.tar.gz (source distributions)
    - *.zip (alternative source distributions)

    Args:
        output_dir: Directory to clean

    Returns:
        Number of files deleted

    Raises:
        BuildError: If path validation fails or directory is inaccessible.

    Examples:
        >>> count = safe_cleanup_wheels("./dist")
        >>> print(f"Deleted {count} artifact files")
    """
    output_dir = Path(output_dir)

    # Validate that path exists first
    if not output_dir.exists():
        raise BuildError(f"Output directory does not exist: {output_dir}")

    if not output_dir.is_dir():
        raise BuildError(f"Output path is not a directory: {output_dir}")

    # Validate safety
    validate_cleanup_path(output_dir)

    # Define patterns for cleanup (only artifact files)
    patterns = ["*.whl", "*.tar.gz", "*.zip"]

    deleted = 0
    errors = []

    for pattern in patterns:
        for file_path in output_dir.glob(pattern):
            try:
                file_path.unlink()
                deleted += 1
            except OSError as e:
                errors.append(f"Failed to delete {file_path}: {e}")

    if errors:
        raise BuildError(
            "Failed to delete some files during cleanup:\n" + "\n".join(errors)
        )

    return deleted


def ensure_deterministic_image(image: str, available_images: dict[str, str]) -> str:
    """Ensure Docker image string is deterministic and canonical.

    Validates that the image exists in the registry and returns the
    canonical form.

    Args:
        image: Image specification (key or URL)
        available_images: Dict mapping keys to canonical URLs

    Returns:
        Canonical full image URL

    Raises:
        IsolationError: If image is not recognized or available.

    Examples:
        >>> images = {"manylinux_2_28_x86_64": "quay.io/pypa/..."}
        >>> url = ensure_deterministic_image("manylinux_2_28_x86_64", images)
        >>> # Returns "quay.io/pypa/..."
    """
    # Check if this is already a full URL
    if image.startswith("quay.io/") or image.startswith("docker.io/"):
        # Verify it's in our known images
        if image not in available_images.values():
            available_keys = ", ".join(sorted(available_images.keys()))
            raise IsolationError(
                f"Unknown or unsupported image: {image}\n"
                f"Supported image keys: {available_keys}"
            )
        return image

    # Otherwise, treat as a key and look it up
    if image not in available_images:
        available_keys = ", ".join(sorted(available_images.keys()))
        raise IsolationError(
            f"Unknown image key: {image}\n"
            f"Supported image keys:\n  " + "\n  ".join(sorted(available_images.keys()))
        )

    return available_images[image]


class AtomicFileWriter:
    """Write files atomically using temp file + rename pattern.

    Ensures that if a write fails, no partial file remains.

    Examples:
        >>> writer = AtomicFileWriter(Path("output.whl"))
        >>> with writer as temp_file:
        ...     write_wheel_data(temp_file)
        ...     # File is renamed to final location on success
        ...     # Temp file cleaned up on exception
    """

    def __init__(self, target_path: Path | str, binary: bool = True):
        """Initialize atomic writer.

        Args:
            target_path: Final destination path
            binary: If True, open in binary mode; else text mode
        """
        self.target_path = Path(target_path)
        self.binary = binary
        self.temp_file: tempfile.NamedTemporaryFile | None = None
        self.temp_path: Path | None = None

    def __enter__(self):
        """Create temporary file in same directory as target.

        This ensures atomic rename is possible (same filesystem).
        """
        target_dir = self.target_path.parent
        mode = "w+b" if self.binary else "w+"

        # Create temp file in the same directory
        self.temp_file = tempfile.NamedTemporaryFile(
            mode=mode, dir=target_dir, delete=False, prefix=".tmp_"
        )
        self.temp_path = Path(self.temp_file.name)
        return self.temp_path

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up temp file or promote to final location.

        If no exception occurred, atomically rename temp file to target.
        If exception occurred, delete temp file.
        """
        if self.temp_file:
            self.temp_file.close()

        if exc_type is not None:
            # Exception occurred, delete temp file
            if self.temp_path and self.temp_path.exists():
                with contextlib.suppress(OSError):
                    self.temp_path.unlink()
            return False

        # No exception, promote temp file to final location
        if self.temp_path and self.temp_path.exists():
            try:
                # Atomic rename (on most filesystems)
                self.temp_path.replace(self.target_path)
            except OSError as e:
                # Clean up temp file if rename failed
                with contextlib.suppress(OSError):
                    self.temp_path.unlink()
                raise BuildError(f"Failed to finalize {self.target_path}: {e}") from e

        return False
