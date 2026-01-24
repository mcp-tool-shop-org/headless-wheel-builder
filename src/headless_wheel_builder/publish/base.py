"""Base classes for publishing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class PublishConfig:
    """Configuration for publishing."""

    # Files to publish
    files: list[Path] = field(default_factory=list)

    # Skip existing versions (don't fail if already published)
    skip_existing: bool = False

    # Dry run mode (validate but don't upload)
    dry_run: bool = False

    # Verbose output
    verbose: bool = False

    # Custom metadata overrides
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class PublishResult:
    """Result of a publish operation."""

    success: bool
    files_published: list[Path] = field(default_factory=list)
    files_skipped: list[Path] = field(default_factory=list)
    files_failed: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)  # URLs where files are available

    @classmethod
    def failure(cls, error: str) -> PublishResult:
        """Create a failure result."""
        return cls(success=False, errors=[error])

    def add_published(self, path: Path, url: str | None = None) -> None:
        """Record a successfully published file."""
        self.files_published.append(path)
        if url:
            self.urls.append(url)

    def add_skipped(self, path: Path, reason: str = "") -> None:
        """Record a skipped file."""
        self.files_skipped.append(path)
        if reason:
            self.errors.append(f"Skipped {path.name}: {reason}")

    def add_failed(self, path: Path, error: str) -> None:
        """Record a failed file."""
        self.files_failed.append(path)
        self.errors.append(f"Failed {path.name}: {error}")
        self.success = False


@runtime_checkable
class Publisher(Protocol):
    """Protocol for package publishers."""

    async def publish(self, config: PublishConfig) -> PublishResult:
        """Publish packages according to config."""
        ...

    async def check_credentials(self) -> bool:
        """Check if credentials are valid."""
        ...


class BasePublisher(ABC):
    """Base class for publishers with common functionality."""

    @abstractmethod
    async def publish(self, config: PublishConfig) -> PublishResult:
        """Publish packages."""
        ...

    @abstractmethod
    async def check_credentials(self) -> bool:
        """Check if credentials are valid."""
        ...

    def _validate_files(self, files: list[Path]) -> list[str]:
        """Validate files exist and are valid packages."""
        errors = []

        for path in files:
            if not path.exists():
                errors.append(f"File not found: {path}")
                continue

            if path.suffix == ".whl":
                # Basic wheel validation
                if not self._is_valid_wheel(path):
                    errors.append(f"Invalid wheel file: {path}")
            elif path.suffix == ".gz" and ".tar" in path.name:
                # Basic sdist validation
                if not self._is_valid_sdist(path):
                    errors.append(f"Invalid sdist file: {path}")
            else:
                errors.append(f"Unknown file type: {path}")

        return errors

    def _is_valid_wheel(self, path: Path) -> bool:
        """Check if path is a valid wheel file."""
        import zipfile

        try:
            with zipfile.ZipFile(path) as whl:
                names = whl.namelist()
                return any("WHEEL" in n for n in names) and any("METADATA" in n for n in names)
        except (zipfile.BadZipFile, Exception):
            return False

    def _is_valid_sdist(self, path: Path) -> bool:
        """Check if path is a valid sdist file."""
        import tarfile

        try:
            with tarfile.open(path, "r:gz") as tar:
                # Should have at least a PKG-INFO or pyproject.toml
                names = tar.getnames()
                return any("PKG-INFO" in n or "pyproject.toml" in n for n in names)
        except (tarfile.TarError, Exception):
            return False

    def _get_package_info(self, path: Path) -> dict[str, str]:
        """Extract package info from wheel or sdist."""
        import zipfile

        info = {"name": "", "version": ""}

        if path.suffix == ".whl":
            # Parse wheel filename: {name}-{version}-{tags}.whl
            parts = path.stem.split("-")
            if len(parts) >= 2:
                info["name"] = parts[0].replace("_", "-")
                info["version"] = parts[1]

            # Try to read METADATA for more info
            try:
                with zipfile.ZipFile(path) as whl:
                    for name in whl.namelist():
                        if name.endswith("METADATA"):
                            content = whl.read(name).decode()
                            for line in content.split("\n"):
                                if line.startswith("Name:"):
                                    info["name"] = line.split(":", 1)[1].strip()
                                elif line.startswith("Version:"):
                                    info["version"] = line.split(":", 1)[1].strip()
                            break
            except Exception:
                pass

        elif path.suffix == ".gz":
            # Parse sdist filename: {name}-{version}.tar.gz
            stem = path.name.replace(".tar.gz", "")
            parts = stem.rsplit("-", 1)
            if len(parts) == 2:
                info["name"] = parts[0]
                info["version"] = parts[1]

        return info
