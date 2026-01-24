"""Conventional Commits parser and version bump detection."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from headless_wheel_builder.version.semver import BumpType

if TYPE_CHECKING:
    from collections.abc import Sequence


class CommitType(Enum):
    """Conventional commit types."""

    FEAT = "feat"  # New feature
    FIX = "fix"  # Bug fix
    DOCS = "docs"  # Documentation
    STYLE = "style"  # Formatting, no code change
    REFACTOR = "refactor"  # Code change without fix/feature
    PERF = "perf"  # Performance improvement
    TEST = "test"  # Adding tests
    BUILD = "build"  # Build system changes
    CI = "ci"  # CI configuration
    CHORE = "chore"  # Maintenance
    REVERT = "revert"  # Revert previous commit
    BREAKING = "breaking"  # Breaking change (special)


# Commit types that trigger version bumps
BUMP_TYPES = {
    CommitType.FEAT: BumpType.MINOR,
    CommitType.FIX: BumpType.PATCH,
    CommitType.PERF: BumpType.PATCH,
    CommitType.REFACTOR: BumpType.PATCH,
    CommitType.REVERT: BumpType.PATCH,
}

# Conventional commit regex
# Format: type(scope)!: description
COMMIT_PATTERN = re.compile(
    r"^(?P<type>\w+)"
    r"(?:\((?P<scope>[^)]+)\))?"
    r"(?P<breaking>!)?"
    r":\s*"
    r"(?P<description>.+)$",
    re.MULTILINE,
)

# Breaking change footer pattern
BREAKING_FOOTER_PATTERN = re.compile(r"^BREAKING[ -]CHANGE:\s*(.+)$", re.MULTILINE | re.IGNORECASE)


@dataclass
class Commit:
    """Parsed conventional commit."""

    type: CommitType | str
    description: str
    scope: str | None = None
    body: str | None = None
    footers: dict[str, str] = field(default_factory=dict)
    breaking: bool = False
    breaking_description: str | None = None
    raw_message: str = ""
    hash: str | None = None  # Git commit hash

    @property
    def is_conventional(self) -> bool:
        """Check if commit follows conventional commit format."""
        return isinstance(self.type, CommitType)

    @property
    def bump_type(self) -> BumpType | None:
        """Get the version bump type for this commit."""
        if self.breaking:
            return BumpType.MAJOR

        if isinstance(self.type, CommitType) and self.type in BUMP_TYPES:
            return BUMP_TYPES[self.type]

        return None


def parse_commit(message: str, hash: str | None = None) -> Commit:
    """
    Parse a commit message into a Commit object.

    Args:
        message: Full commit message
        hash: Optional git commit hash

    Returns:
        Commit object (may be non-conventional)

    Examples:
        >>> commit = parse_commit("feat(auth): add login endpoint")
        >>> commit.type
        <CommitType.FEAT: 'feat'>
        >>> commit.scope
        'auth'

        >>> commit = parse_commit("fix!: critical security fix")
        >>> commit.breaking
        True
    """
    if not message:
        return Commit(type="unknown", description="", raw_message=message, hash=hash)

    lines = message.strip().split("\n")
    first_line = lines[0].strip()

    # Try to parse as conventional commit
    match = COMMIT_PATTERN.match(first_line)

    if match:
        groups = match.groupdict()
        commit_type_str = groups["type"].lower()

        # Try to convert to CommitType enum
        try:
            commit_type = CommitType(commit_type_str)
        except ValueError:
            commit_type = commit_type_str  # Keep as string

        # Check for breaking change indicator
        breaking = groups.get("breaking") == "!"

        # Parse body and footers
        body = None
        footers = {}
        breaking_description = None

        if len(lines) > 1:
            # Find body (after blank line)
            body_lines = []
            footer_start = len(lines)

            for i, line in enumerate(lines[1:], 1):
                stripped = line.strip()

                # Check for footer patterns
                if ":" in stripped and not stripped.startswith(" "):
                    key, _, value = stripped.partition(":")
                    key = key.strip()
                    value = value.strip()

                    # Check for breaking change footer
                    if key.upper() in ("BREAKING CHANGE", "BREAKING-CHANGE"):
                        breaking = True
                        breaking_description = value
                        footer_start = min(footer_start, i)
                    elif key and value:
                        footers[key] = value
                        footer_start = min(footer_start, i)
                elif stripped and i < footer_start:
                    body_lines.append(line)

            if body_lines:
                body = "\n".join(body_lines).strip()
                if body.startswith("\n"):
                    body = body[1:]

        # Check for breaking change in body
        if body:
            match = BREAKING_FOOTER_PATTERN.search(body)
            if match:
                breaking = True
                breaking_description = breaking_description or match.group(1)

        return Commit(
            type=commit_type,
            description=groups["description"],
            scope=groups.get("scope"),
            body=body,
            footers=footers,
            breaking=breaking,
            breaking_description=breaking_description,
            raw_message=message,
            hash=hash,
        )

    # Non-conventional commit - just use the first line as description
    return Commit(
        type="other",
        description=first_line,
        body="\n".join(lines[1:]).strip() if len(lines) > 1 else None,
        raw_message=message,
        hash=hash,
    )


def determine_bump_from_commits(commits: Sequence[Commit]) -> BumpType | None:
    """
    Determine the version bump type from a list of commits.

    Rules (highest priority wins):
    1. Any breaking change -> major
    2. Any feat -> minor
    3. Any fix/perf/refactor -> patch
    4. Otherwise -> None

    Args:
        commits: List of commits to analyze

    Returns:
        The bump type, or None if no bump needed

    Examples:
        >>> commits = [
        ...     parse_commit("feat: new feature"),
        ...     parse_commit("fix: bug fix"),
        ... ]
        >>> determine_bump_from_commits(commits)
        <BumpType.MINOR: 'minor'>
    """
    if not commits:
        return None

    has_breaking = False
    has_feat = False
    has_fix = False

    for commit in commits:
        if commit.breaking:
            has_breaking = True
            break  # Major is highest priority

        if isinstance(commit.type, CommitType):
            if commit.type == CommitType.FEAT:
                has_feat = True
            elif commit.type in (
                CommitType.FIX,
                CommitType.PERF,
                CommitType.REFACTOR,
                CommitType.REVERT,
            ):
                has_fix = True

    if has_breaking:
        return BumpType.MAJOR
    elif has_feat:
        return BumpType.MINOR
    elif has_fix:
        return BumpType.PATCH

    return None


def format_commit(commit: Commit, include_hash: bool = True) -> str:
    """
    Format a commit for display.

    Args:
        commit: Commit to format
        include_hash: Include short hash if available

    Returns:
        Formatted string
    """
    parts = []

    if include_hash and commit.hash:
        parts.append(f"[{commit.hash[:7]}]")

    type_str = commit.type.value if isinstance(commit.type, CommitType) else str(commit.type)

    if commit.scope:
        parts.append(f"{type_str}({commit.scope}):")
    else:
        parts.append(f"{type_str}:")

    parts.append(commit.description)

    if commit.breaking:
        parts.append("[BREAKING]")

    return " ".join(parts)


def group_commits_by_type(
    commits: Sequence[Commit],
) -> dict[str, list[Commit]]:
    """
    Group commits by their type.

    Args:
        commits: List of commits to group

    Returns:
        Dict mapping type names to lists of commits
    """
    groups: dict[str, list[Commit]] = {}

    for commit in commits:
        key = commit.type.value if isinstance(commit.type, CommitType) else str(commit.type)

        if key not in groups:
            groups[key] = []
        groups[key].append(commit)

    return groups
