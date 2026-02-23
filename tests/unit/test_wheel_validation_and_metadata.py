from __future__ import annotations

import zipfile
from typing import TYPE_CHECKING

import pytest

from headless_wheel_builder.core.builder import BuildEngine, BuildResult
from headless_wheel_builder.exceptions import BuildError

if TYPE_CHECKING:
    from pathlib import Path


def _write_minimal_wheel(path: Path, unsafe: bool = False) -> None:
    # Minimal wheel contents: dist-info/WHEEL and dist-info/METADATA
    dist_info = "demo_pkg-0.1.0.dist-info"
    wheel_name = f"{dist_info}/WHEEL"
    meta_name = f"{dist_info}/METADATA"

    with zipfile.ZipFile(path, "w") as z:
        z.writestr(wheel_name, "Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
        z.writestr(meta_name, "Metadata-Version: 2.1\nName: demo-pkg\nVersion: 0.1.0\n")
        if unsafe:
            z.writestr("../evil.txt", "nope")


def test_validate_wheel_rejects_unsafe_paths(tmp_path: Path) -> None:
    wheel = tmp_path / "demo_pkg-0.1.0-py3-none-any.whl"
    _write_minimal_wheel(wheel, unsafe=True)

    engine = BuildEngine()
    with pytest.raises(BuildError, match="unsafe path"):
        engine._validate_wheel(wheel)


def test_extract_wheel_metadata_sets_tags_and_hash(tmp_path: Path) -> None:
    wheel = tmp_path / "demo_pkg-0.1.0-py3-none-any.whl"
    _write_minimal_wheel(wheel, unsafe=False)

    engine = BuildEngine()
    result = BuildResult(success=True, wheel_path=wheel)

    # Validate should pass
    engine._validate_wheel(wheel)
    engine._extract_wheel_metadata(wheel, result)

    assert result.name == "demo-pkg"
    assert result.version == "0.1.0"
    assert result.python_tag == "py3"
    assert result.abi_tag == "none"
    assert result.platform_tag == "any"
    assert isinstance(result.sha256, str) and len(result.sha256) == 64
    assert result.size_bytes == wheel.stat().st_size


# =============================================================================
# P0: Harden wheel validation against unsafe paths and missing metadata
# =============================================================================


def _write_wheel_with_contents(path: Path, contents: dict[str, str]) -> None:
    """Helper to create a wheel with specific file contents."""
    with zipfile.ZipFile(path, "w") as z:
        for name, content in contents.items():
            z.writestr(name, content)


def test_validate_wheel_rejects_absolute_path(tmp_path: Path) -> None:
    """Wheel with absolute path should raise BuildError with the offending path."""
    wheel = tmp_path / "bad.whl"
    _write_wheel_with_contents(wheel, {
        "demo_pkg-0.1.0.dist-info/WHEEL": "Wheel-Version: 1.0",
        "demo_pkg-0.1.0.dist-info/METADATA": "Name: demo-pkg\nVersion: 0.1.0",
        "/etc/passwd": "root:x:0:0:root",
    })

    engine = BuildEngine()
    with pytest.raises(BuildError, match="unsafe path") as exc_info:
        engine._validate_wheel(wheel)
    # Error should include the offending path
    assert "/etc/passwd" in str(exc_info.value)


def test_validate_wheel_rejects_path_traversal(tmp_path: Path) -> None:
    """Wheel with .. path traversal should raise BuildError."""
    wheel = tmp_path / "bad.whl"
    _write_wheel_with_contents(wheel, {
        "demo_pkg-0.1.0.dist-info/WHEEL": "Wheel-Version: 1.0",
        "demo_pkg-0.1.0.dist-info/METADATA": "Name: demo-pkg\nVersion: 0.1.0",
        "../../etc/shadow": "malicious",
    })

    engine = BuildEngine()
    with pytest.raises(BuildError, match="unsafe path") as exc_info:
        engine._validate_wheel(wheel)
    assert ".." in str(exc_info.value)


def test_validate_wheel_rejects_missing_wheel_file(tmp_path: Path) -> None:
    """Wheel without WHEEL file should raise BuildError."""
    wheel = tmp_path / "bad.whl"
    _write_wheel_with_contents(wheel, {
        "demo_pkg-0.1.0.dist-info/METADATA": "Name: demo-pkg\nVersion: 0.1.0",
        "demo_pkg/__init__.py": "",
    })

    engine = BuildEngine()
    with pytest.raises(BuildError, match="missing WHEEL"):
        engine._validate_wheel(wheel)


def test_validate_wheel_rejects_missing_metadata_file(tmp_path: Path) -> None:
    """Wheel without METADATA file should raise BuildError."""
    wheel = tmp_path / "bad.whl"
    _write_wheel_with_contents(wheel, {
        "demo_pkg-0.1.0.dist-info/WHEEL": "Wheel-Version: 1.0",
        "demo_pkg/__init__.py": "",
    })

    engine = BuildEngine()
    with pytest.raises(BuildError, match="missing METADATA"):
        engine._validate_wheel(wheel)


def test_validate_wheel_accepts_valid_wheel(tmp_path: Path) -> None:
    """Valid wheel should pass validation without error."""
    wheel = tmp_path / "good.whl"
    _write_wheel_with_contents(wheel, {
        "demo_pkg-0.1.0.dist-info/WHEEL": "Wheel-Version: 1.0\nGenerator: test",
        "demo_pkg-0.1.0.dist-info/METADATA": "Metadata-Version: 2.1\nName: demo-pkg\nVersion: 0.1.0",
        "demo_pkg-0.1.0.dist-info/RECORD": "",
        "demo_pkg/__init__.py": "# demo package",
    })

    engine = BuildEngine()
    # Should not raise
    engine._validate_wheel(wheel)
