"""Git operations for version management."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from headless_wheel_builder.exceptions import GitError, VersionError
from headless_wheel_builder.version.semver import Version, parse_version


@dataclass
class GitTag:
    """Git tag information."""

    name: str
    version: Version | None
    commit_hash: str
    message: str | None = None


async def get_latest_tag(
    repo_path: Path | str = ".",
    pattern: str = "v*",
    include_prereleases: bool = True,
) -> GitTag | None:
    """
    Get the latest version tag from the repository.

    Args:
        repo_path: Path to git repository
        pattern: Tag pattern to match (default: "v*")
        include_prereleases: Include prerelease tags

    Returns:
        GitTag with version info, or None if no tags found
    """
    repo_path = Path(repo_path)

    # Get all tags matching pattern, sorted by version
    cmd = [
        "git",
        "tag",
        "-l",
        pattern,
        "--sort=-v:refname",  # Sort by version, newest first
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=repo_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        error_msg = stderr.decode().strip()
        if "not a git repository" in error_msg.lower():
            return None
        raise GitError(f"Failed to list tags: {error_msg}", stderr=error_msg)

    tags = stdout.decode().strip().split("\n")
    tags = [t.strip() for t in tags if t.strip()]

    if not tags:
        return None

    # Find the first valid version tag
    for tag_name in tags:
        try:
            version = parse_version(tag_name)

            # Skip prereleases if requested
            if not include_prereleases and version.is_prerelease:
                continue

            # Get commit hash for this tag
            commit_hash = await _get_tag_commit(repo_path, tag_name)
            message = await _get_tag_message(repo_path, tag_name)

            return GitTag(
                name=tag_name,
                version=version,
                commit_hash=commit_hash,
                message=message,
            )
        except VersionError:
            continue  # Not a valid version tag

    return None


async def get_commits_since_tag(
    repo_path: Path | str = ".",
    tag: str | None = None,
    include_hash: bool = True,
) -> list[tuple[str, str]]:
    """
    Get all commits since a tag.

    Args:
        repo_path: Path to git repository
        tag: Tag to start from (None for all commits)
        include_hash: Include commit hash

    Returns:
        List of (hash, message) tuples
    """
    repo_path = Path(repo_path)

    # Build git log command
    range_spec = f"{tag}..HEAD" if tag else "HEAD"

    cmd = [
        "git",
        "log",
        range_spec,
        "--pretty=format:%H%x00%B%x00",  # Hash and full message separated by null
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=repo_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        error_msg = stderr.decode().strip()
        raise GitError(f"Failed to get commits: {error_msg}", stderr=error_msg)

    output = stdout.decode()
    commits = []

    # Parse commits
    parts = output.split("\x00")
    i = 0
    while i < len(parts) - 1:
        hash_val = parts[i].strip()
        message = parts[i + 1].strip() if i + 1 < len(parts) else ""

        if hash_val:
            commits.append((hash_val, message))

        i += 2

    return commits


async def create_tag(
    repo_path: Path | str = ".",
    tag_name: str = "",
    message: str | None = None,
    commit: str = "HEAD",
    sign: bool = False,
    force: bool = False,
) -> GitTag:
    """
    Create a new git tag.

    Args:
        repo_path: Path to git repository
        tag_name: Name for the tag
        message: Optional tag message (creates annotated tag)
        commit: Commit to tag (default: HEAD)
        sign: GPG sign the tag
        force: Overwrite existing tag

    Returns:
        Created GitTag
    """
    if not tag_name:
        raise VersionError("Tag name is required")

    repo_path = Path(repo_path)

    cmd = ["git", "tag"]

    if force:
        cmd.append("-f")

    if message:
        cmd.extend(["-a", "-m", message])

    if sign:
        cmd.append("-s")

    cmd.append(tag_name)
    cmd.append(commit)

    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=repo_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _stdout, stderr = await process.communicate()

    if process.returncode != 0:
        error_msg = stderr.decode().strip()
        raise GitError(f"Failed to create tag: {error_msg}", stderr=error_msg)

    # Get tag info
    commit_hash = await _get_tag_commit(repo_path, tag_name)

    try:
        version = parse_version(tag_name)
    except VersionError:
        version = None

    return GitTag(
        name=tag_name,
        version=version,
        commit_hash=commit_hash,
        message=message,
    )


async def push_tag(
    repo_path: Path | str = ".",
    tag_name: str = "",
    remote: str = "origin",
    force: bool = False,
) -> None:
    """
    Push a tag to remote.

    Args:
        repo_path: Path to git repository
        tag_name: Tag to push
        remote: Remote name
        force: Force push
    """
    if not tag_name:
        raise VersionError("Tag name is required")

    repo_path = Path(repo_path)

    cmd = ["git", "push", remote, tag_name]
    if force:
        cmd.insert(2, "-f")

    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=repo_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _stdout, stderr = await process.communicate()

    if process.returncode != 0:
        error_msg = stderr.decode().strip()
        raise GitError(f"Failed to push tag: {error_msg}", stderr=error_msg)


async def get_current_branch(repo_path: Path | str = ".") -> str:
    """Get the current branch name."""
    repo_path = Path(repo_path)

    process = await asyncio.create_subprocess_exec(
        "git",
        "rev-parse",
        "--abbrev-ref",
        "HEAD",
        cwd=repo_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise GitError(f"Failed to get branch: {stderr.decode()}")

    return stdout.decode().strip()


async def get_head_commit(repo_path: Path | str = ".") -> str:
    """Get the HEAD commit hash."""
    repo_path = Path(repo_path)

    process = await asyncio.create_subprocess_exec(
        "git",
        "rev-parse",
        "HEAD",
        cwd=repo_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise GitError(f"Failed to get HEAD: {stderr.decode()}")

    return stdout.decode().strip()


async def is_dirty(repo_path: Path | str = ".") -> bool:
    """Check if working directory has uncommitted changes."""
    repo_path = Path(repo_path)

    process = await asyncio.create_subprocess_exec(
        "git",
        "status",
        "--porcelain",
        cwd=repo_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise GitError(f"Failed to check status: {stderr.decode()}")

    return bool(stdout.decode().strip())


async def _get_tag_commit(repo_path: Path, tag_name: str) -> str:
    """Get the commit hash for a tag."""
    process = await asyncio.create_subprocess_exec(
        "git",
        "rev-list",
        "-n",
        "1",
        tag_name,
        cwd=repo_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise GitError(f"Failed to get tag commit: {stderr.decode()}")

    return stdout.decode().strip()


async def _get_tag_message(repo_path: Path, tag_name: str) -> str | None:
    """Get the message for an annotated tag."""
    process = await asyncio.create_subprocess_exec(
        "git",
        "tag",
        "-l",
        "--format=%(contents)",
        tag_name,
        cwd=repo_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _stderr = await process.communicate()

    if process.returncode != 0:
        return None

    message = stdout.decode().strip()
    return message if message else None
