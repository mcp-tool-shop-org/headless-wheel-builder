"""Source resolution - handles local paths, git repos, and archives."""

from __future__ import annotations

import asyncio
import hashlib
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from headless_wheel_builder.exceptions import GitError, SourceError

if TYPE_CHECKING:
    from collections.abc import Callable


class SourceType(Enum):
    """Types of source locations."""

    LOCAL_PATH = "local_path"  # /path/to/project
    GIT_HTTPS = "git_https"  # https://github.com/user/repo
    GIT_SSH = "git_ssh"  # git@github.com:user/repo
    TARBALL = "tarball"  # https://example.com/pkg.tar.gz
    SDIST = "sdist"  # package-1.0.0.tar.gz


@dataclass
class SourceSpec:
    """Specification for a source location."""

    type: SourceType
    location: str
    ref: str | None = None  # Git branch/tag/commit
    subdirectory: str | None = None  # For monorepos
    editable: bool = False

    def __post_init__(self) -> None:
        """Validate the spec after initialization."""
        if self.type in (SourceType.GIT_HTTPS, SourceType.GIT_SSH) and not self.location:
            raise SourceError("Git URL cannot be empty")


@dataclass
class ResolvedSource:
    """A source that has been resolved to a local path."""

    spec: SourceSpec
    local_path: Path
    is_temporary: bool  # Should be cleaned up after build
    commit_hash: str | None = None  # For git sources
    _cleanup_callbacks: list[Callable[[], None]] = field(default_factory=list, repr=False)

    def add_cleanup(self, callback: Callable[[], None]) -> None:
        """Add a cleanup callback."""
        self._cleanup_callbacks.append(callback)

    def cleanup(self) -> None:
        """Clean up temporary resources."""
        for callback in self._cleanup_callbacks:
            try:
                callback()
            except Exception:
                pass  # Best effort cleanup

    def __enter__(self) -> ResolvedSource:
        return self

    def __exit__(self, *args: object) -> None:
        if self.is_temporary:
            self.cleanup()


# Git URL patterns
GIT_HTTPS_PATTERN = re.compile(
    r"^https?://(?:www\.)?(?:github\.com|gitlab\.com|bitbucket\.org)/[\w.-]+/[\w.-]+(?:\.git)?(?:@[\w./-]+)?(?:#.*)?$"
)
GIT_SSH_PATTERN = re.compile(r"^git@[\w.-]+:[\w.-]+/[\w.-]+(?:\.git)?(?:@[\w./-]+)?(?:#.*)?$")
URL_WITH_REF_PATTERN = re.compile(r"^(.+?)(?:@([\w./-]+))?(?:#subdirectory=([\w./-]+))?$")


class SourceResolver:
    """
    Resolves source specifications to local paths.

    Handles:
    - Local directory detection
    - Git cloning (with sparse checkout for monorepos)
    - Tarball/sdist extraction
    - Temporary directory management
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or Path.home() / ".cache" / "hwb" / "sources"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def parse_source(self, source: str) -> SourceSpec:
        """
        Parse a source string into a SourceSpec.

        Args:
            source: Source string (path, git URL, etc.)

        Returns:
            SourceSpec with type, location, and optional ref/subdirectory

        Raises:
            SourceError: If source type cannot be determined
        """
        # Extract ref and subdirectory from URL
        ref: str | None = None
        subdirectory: str | None = None

        # Check for @ref and #subdirectory=path
        if match := URL_WITH_REF_PATTERN.match(source):
            base_url = match.group(1)
            ref = match.group(2)
            subdirectory = match.group(3)
            source = base_url
        else:
            base_url = source

        # Git SSH: git@github.com:user/repo.git
        if source.startswith("git@"):
            return SourceSpec(
                type=SourceType.GIT_SSH,
                location=source,
                ref=ref,
                subdirectory=subdirectory,
            )

        # Git HTTPS: https://github.com/user/repo
        if source.startswith(("https://", "http://")) and any(
            host in source for host in ("github.com", "gitlab.com", "bitbucket.org")
        ):
            return SourceSpec(
                type=SourceType.GIT_HTTPS,
                location=source,
                ref=ref,
                subdirectory=subdirectory,
            )

        # Archive URLs
        if source.startswith(("https://", "http://")) and source.endswith(
            (".tar.gz", ".tgz", ".zip", ".tar.bz2")
        ):
            return SourceSpec(type=SourceType.TARBALL, location=source)

        # Local archive files
        if source.endswith((".tar.gz", ".tgz", ".zip", ".tar.bz2")):
            path = Path(source)
            if path.exists():
                return SourceSpec(type=SourceType.SDIST, location=str(path.resolve()))
            raise SourceError(f"Archive not found: {source}")

        # Local path
        path = Path(source)
        if path.exists():
            return SourceSpec(
                type=SourceType.LOCAL_PATH,
                location=str(path.resolve()),
                subdirectory=subdirectory,
            )

        raise SourceError(f"Cannot determine source type for: {source}")

    async def resolve(self, spec: SourceSpec) -> ResolvedSource:
        """
        Resolve a source spec to a local path.

        Args:
            spec: Source specification

        Returns:
            ResolvedSource with local path

        Raises:
            SourceError: If source cannot be resolved
        """
        match spec.type:
            case SourceType.LOCAL_PATH:
                return await self._resolve_local(spec)
            case SourceType.GIT_HTTPS | SourceType.GIT_SSH:
                return await self._resolve_git(spec)
            case SourceType.TARBALL:
                return await self._resolve_url_archive(spec)
            case SourceType.SDIST:
                return await self._resolve_local_archive(spec)
            case _:
                raise SourceError(f"Unsupported source type: {spec.type}")

    async def _resolve_local(self, spec: SourceSpec) -> ResolvedSource:
        """Resolve a local path."""
        path = Path(spec.location)

        if not path.exists():
            raise SourceError(f"Path does not exist: {path}")

        if not path.is_dir():
            raise SourceError(f"Path is not a directory: {path}")

        # Handle subdirectory
        if spec.subdirectory:
            path = path / spec.subdirectory
            if not path.exists():
                raise SourceError(f"Subdirectory does not exist: {path}")

        # Check for pyproject.toml or setup.py
        if not (path / "pyproject.toml").exists() and not (path / "setup.py").exists():
            raise SourceError(f"No pyproject.toml or setup.py found in: {path}")

        return ResolvedSource(
            spec=spec,
            local_path=path,
            is_temporary=False,
        )

    async def _resolve_git(self, spec: SourceSpec) -> ResolvedSource:
        """Clone a git repository."""
        # Generate cache key based on URL and ref
        cache_key = hashlib.sha256(f"{spec.location}:{spec.ref or 'HEAD'}".encode()).hexdigest()[
            :12
        ]
        clone_dir = self.cache_dir / f"git_{cache_key}"

        # Clean existing clone for fresh checkout
        if clone_dir.exists():
            shutil.rmtree(clone_dir)

        clone_dir.mkdir(parents=True, exist_ok=True)

        # Build clone command
        clone_args = ["git", "clone", "--depth=1"]

        if spec.ref:
            clone_args.extend(["--branch", spec.ref])

        # Sparse checkout for subdirectory
        if spec.subdirectory:
            clone_args.extend(["--filter=blob:none", "--sparse"])

        clone_args.extend([spec.location, str(clone_dir)])

        # Execute clone
        process = await asyncio.create_subprocess_exec(
            *clone_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()

        if process.returncode != 0:
            raise GitError(f"Git clone failed: {spec.location}", stderr.decode())

        # Configure sparse checkout if needed
        if spec.subdirectory:
            sparse_cmd = [
                "git",
                "-C",
                str(clone_dir),
                "sparse-checkout",
                "set",
                spec.subdirectory,
            ]
            process = await asyncio.create_subprocess_exec(
                *sparse_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()

        # Get commit hash
        commit_hash = await self._get_commit_hash(clone_dir)

        # Determine final path
        final_path = clone_dir / spec.subdirectory if spec.subdirectory else clone_dir

        if not final_path.exists():
            raise SourceError(f"Path after clone does not exist: {final_path}")

        resolved = ResolvedSource(
            spec=spec,
            local_path=final_path,
            is_temporary=True,
            commit_hash=commit_hash,
        )

        # Add cleanup callback
        def cleanup() -> None:
            if clone_dir.exists():
                shutil.rmtree(clone_dir, ignore_errors=True)

        resolved.add_cleanup(cleanup)

        return resolved

    async def _resolve_url_archive(self, spec: SourceSpec) -> ResolvedSource:
        """Download and extract an archive from URL."""
        import httpx

        # Download to temp file
        temp_dir = Path(tempfile.mkdtemp(prefix="hwb_archive_"))

        try:
            # Determine filename from URL
            filename = spec.location.split("/")[-1].split("?")[0]
            archive_path = temp_dir / filename

            # Download
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(spec.location)
                response.raise_for_status()
                archive_path.write_bytes(response.content)

            # Extract
            extract_dir = temp_dir / "extracted"
            extract_dir.mkdir()
            await self._extract_archive(archive_path, extract_dir)

            # Find the actual source directory (usually one level deep)
            contents = list(extract_dir.iterdir())
            source_dir = contents[0] if len(contents) == 1 and contents[0].is_dir() else extract_dir

            resolved = ResolvedSource(
                spec=spec,
                local_path=source_dir,
                is_temporary=True,
            )

            def cleanup() -> None:
                shutil.rmtree(temp_dir, ignore_errors=True)

            resolved.add_cleanup(cleanup)

            return resolved

        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise SourceError(f"Failed to download archive: {e}") from e

    async def _resolve_local_archive(self, spec: SourceSpec) -> ResolvedSource:
        """Extract a local archive."""
        archive_path = Path(spec.location)

        if not archive_path.exists():
            raise SourceError(f"Archive not found: {archive_path}")

        temp_dir = Path(tempfile.mkdtemp(prefix="hwb_sdist_"))

        try:
            await self._extract_archive(archive_path, temp_dir)

            # Find the actual source directory
            contents = list(temp_dir.iterdir())
            source_dir = contents[0] if len(contents) == 1 and contents[0].is_dir() else temp_dir

            resolved = ResolvedSource(
                spec=spec,
                local_path=source_dir,
                is_temporary=True,
            )

            def cleanup() -> None:
                shutil.rmtree(temp_dir, ignore_errors=True)

            resolved.add_cleanup(cleanup)

            return resolved

        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise SourceError(f"Failed to extract archive: {e}") from e

    async def _extract_archive(self, archive_path: Path, dest_dir: Path) -> None:
        """Extract an archive to destination directory."""
        import tarfile
        import zipfile

        suffix = archive_path.suffix.lower()
        suffixes = "".join(archive_path.suffixes).lower()

        if suffix == ".zip":
            with zipfile.ZipFile(archive_path) as zf:
                zf.extractall(dest_dir)
        elif suffixes.endswith((".tar.gz", ".tgz")):
            with tarfile.open(archive_path, "r:gz") as tf:
                tf.extractall(dest_dir)
        elif suffixes.endswith(".tar.bz2"):
            with tarfile.open(archive_path, "r:bz2") as tf:
                tf.extractall(dest_dir)
        else:
            raise SourceError(f"Unsupported archive format: {archive_path}")

    async def _get_commit_hash(self, repo_dir: Path) -> str | None:
        """Get the current commit hash of a git repository."""
        process = await asyncio.create_subprocess_exec(
            "git",
            "-C",
            str(repo_dir),
            "rev-parse",
            "HEAD",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await process.communicate()

        if process.returncode == 0:
            return stdout.decode().strip()
        return None

    def _get_cache_path(self, spec: SourceSpec) -> Path:
        """Generate a cache path for a source spec."""
        key = hashlib.sha256(f"{spec.type}:{spec.location}:{spec.ref}".encode()).hexdigest()[:16]
        return self.cache_dir / key
