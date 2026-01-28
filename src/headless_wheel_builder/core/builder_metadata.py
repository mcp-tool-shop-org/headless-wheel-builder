"""Wheel metadata extraction and handling for BuildEngine.

This module handles extracting and processing metadata from built wheels,
separating this concern from the main build engine.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from headless_wheel_builder.core.builder import BuildResult


def extract_wheel_metadata(wheel_path: Path, result: BuildResult) -> None:
    """Extract metadata from wheel filename and contents.

    Updates the result object with parsed metadata:
    - name: Distribution name
    - version: Package version
    - python_tag: Python version tag
    - abi_tag: ABI tag
    - platform_tag: Platform tag

    Args:
        wheel_path: Path to .whl file
        result: BuildResult to populate

    Raises:
        ValueError: If wheel filename is invalid
    """
    # Parse wheel filename
    # Format: {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
    name = wheel_path.stem
    parts = name.split("-")

    if len(parts) < 5:
        raise ValueError(
            f"Invalid wheel filename format: {wheel_path.name}\n"
            f"Expected: {{distribution}}-{{version}}-{{python}}-{{abi}}-{{platform}}.whl"
        )

    result.name = parts[0].replace("_", "-")
    result.version = parts[1]
    result.python_tag = parts[-3]
    result.abi_tag = parts[-2]
    result.platform_tag = parts[-1]


def parse_wheel_filename(filename: str) -> dict[str, str]:
    """Parse a wheel filename into components.

    Args:
        filename: Wheel filename (e.g., 'package-1.0-py3-none-any.whl')

    Returns:
        Dictionary with keys: name, version, python_tag, abi_tag, platform_tag

    Raises:
        ValueError: If filename is invalid
    """
    name = filename.replace(".whl", "")
    parts = name.split("-")

    if len(parts) < 5:
        raise ValueError(
            f"Invalid wheel filename format: {filename}\n"
            f"Expected: {{distribution}}-{{version}}-{{python}}-{{abi}}-{{platform}}.whl"
        )

    return {
        "name": parts[0].replace("_", "-"),
        "version": parts[1],
        "python_tag": parts[-3],
        "abi_tag": parts[-2],
        "platform_tag": parts[-1],
        "full_filename": filename,
    }


def validate_wheel_filename(filename: str) -> bool:
    """Validate wheel filename format.

    Args:
        filename: Filename to validate

    Returns:
        True if valid, False otherwise
    """
    if not filename.endswith(".whl"):
        return False

    name = filename.replace(".whl", "")
    parts = name.split("-")
    return len(parts) >= 5


def get_wheel_compatibility(filename: str) -> dict[str, str]:
    """Extract compatibility information from wheel filename.

    Args:
        filename: Wheel filename

    Returns:
        Dictionary with python_version, abi, and platform

    Raises:
        ValueError: If filename is invalid
    """
    parsed = parse_wheel_filename(filename)
    return {
        "python_version": parsed["python_tag"],
        "abi": parsed["abi_tag"],
        "platform": parsed["platform_tag"],
    }


def is_universal_wheel(filename: str) -> bool:
    """Check if wheel is universal (py2.py3-none-any).

    Args:
        filename: Wheel filename

    Returns:
        True if wheel is universal, False otherwise
    """
    try:
        parsed = parse_wheel_filename(filename)
        return (
            parsed["python_tag"] in ("py2.py3", "py3")
            and parsed["abi_tag"] == "none"
            and parsed["platform_tag"] == "any"
        )
    except ValueError:
        return False


def is_manylinux_wheel(filename: str) -> bool:
    """Check if wheel is manylinux compatible.

    Args:
        filename: Wheel filename

    Returns:
        True if wheel is manylinux, False otherwise
    """
    try:
        parsed = parse_wheel_filename(filename)
        platform = parsed["platform_tag"].lower()
        return "manylinux" in platform or "musllinux" in platform
    except ValueError:
        return False


def get_wheel_requires_python(wheel_path: Path) -> str | None:
    """Extract Requires-Python metadata from wheel.

    Args:
        wheel_path: Path to .whl file

    Returns:
        Requires-Python string or None if not found

    Raises:
        OSError: If wheel cannot be read
    """
    import zipfile

    try:
        with zipfile.ZipFile(wheel_path) as whl:
            # Find METADATA file
            metadata_files = [n for n in whl.namelist() if "METADATA" in n]
            if not metadata_files:
                return None

            metadata_content = whl.read(metadata_files[0]).decode("utf-8")

            # Parse METADATA file for Requires-Python
            for line in metadata_content.splitlines():
                if line.startswith("Requires-Python:"):
                    return line.split(":", 1)[1].strip()

            return None
    except Exception:
        return None
