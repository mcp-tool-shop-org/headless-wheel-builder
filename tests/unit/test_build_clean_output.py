from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from headless_wheel_builder.core.builder import (
    BuildConfig,
    BuildEngine,
    _is_dangerous_cleanup_path,
)
from headless_wheel_builder.exceptions import BuildError


@pytest.mark.asyncio
async def test_clean_output_removes_prior_artifacts(tmp_path: Path) -> None:
    out = tmp_path / "dist"
    out.mkdir()

    (out / "old.whl").write_text("x")
    (out / "old-1.0.0.tar.gz").write_text("y")
    assert any(out.glob("*.whl"))
    assert any(out.glob("*.tar.gz"))

    cfg = BuildConfig(output_dir=out, clean_output=True)
    engine = BuildEngine(cfg)

    # Stop after cleanup by raising inside resolve step (cleanup happens before try/except)
    # BuildErrors propagate, so we expect the exception to be raised
    engine._resolve_source = AsyncMock(side_effect=BuildError("stop"))  # type: ignore[attr-defined]

    with pytest.raises(BuildError, match="stop"):
        await engine.build(source=".")

    # Cleanup should have happened before the error
    assert not any(out.glob("*.whl"))
    assert not any(out.glob("*.tar.gz"))


# =============================================================================
# P0: Ensure clean_output cannot delete outside configured output_dir
# =============================================================================


def test_is_dangerous_cleanup_path_root() -> None:
    """Root directory should be dangerous."""
    # Unix root
    assert _is_dangerous_cleanup_path(Path("/"))
    # Windows drive root (may vary by platform)
    if Path("C:/").exists():
        assert _is_dangerous_cleanup_path(Path("C:/"))


def test_is_dangerous_cleanup_path_home() -> None:
    """Home directory should be dangerous."""
    assert _is_dangerous_cleanup_path(Path.home())


def test_is_dangerous_cleanup_path_system_dirs() -> None:
    """Common system directories should be dangerous."""
    # These should be dangerous regardless of whether they exist
    assert _is_dangerous_cleanup_path(Path("/usr"))
    assert _is_dangerous_cleanup_path(Path("/etc"))
    assert _is_dangerous_cleanup_path(Path("/var"))
    assert _is_dangerous_cleanup_path(Path("/bin"))


def test_is_dangerous_cleanup_path_safe_dir(tmp_path: Path) -> None:
    """Normal directories should not be dangerous."""
    safe = tmp_path / "dist"
    safe.mkdir()
    assert not _is_dangerous_cleanup_path(safe)


def test_is_dangerous_cleanup_path_nested_dist(tmp_path: Path) -> None:
    """Nested dist directory should be safe."""
    nested = tmp_path / "project" / "dist"
    nested.mkdir(parents=True)
    assert not _is_dangerous_cleanup_path(nested)


@pytest.mark.asyncio
async def test_clean_output_refuses_dangerous_directory() -> None:
    """Cleanup should refuse to clean dangerous directories."""
    # Try to use home directory as output
    cfg = BuildConfig(output_dir=Path.home(), clean_output=True)
    engine = BuildEngine(cfg)

    with pytest.raises(BuildError, match="Refusing to clean dangerous directory"):
        await engine.build(source=".")


@pytest.mark.asyncio
async def test_clean_output_only_removes_wheel_and_tarball(tmp_path: Path) -> None:
    """Cleanup should only remove .whl and .tar.gz files, not other files."""
    out = tmp_path / "dist"
    out.mkdir()

    # Create various files
    (out / "keep.py").write_text("important")
    (out / "keep.txt").write_text("also important")
    (out / "old.whl").write_text("wheel")
    (out / "old.tar.gz").write_text("tarball")

    cfg = BuildConfig(output_dir=out, clean_output=True)
    engine = BuildEngine(cfg)
    engine._resolve_source = AsyncMock(side_effect=BuildError("stop"))  # type: ignore[attr-defined]

    with pytest.raises(BuildError, match="stop"):
        await engine.build(source=".")

    # Wheels and tarballs should be gone
    assert not any(out.glob("*.whl"))
    assert not any(out.glob("*.tar.gz"))
    # Other files should remain
    assert (out / "keep.py").exists()
    assert (out / "keep.txt").exists()
