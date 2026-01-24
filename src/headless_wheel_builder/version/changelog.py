"""Changelog generation from conventional commits."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING

from headless_wheel_builder.version.conventional import (
    Commit,
    CommitType,
    group_commits_by_type,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from headless_wheel_builder.version.semver import Version

# Section order and titles for changelog
SECTION_ORDER = [
    (CommitType.BREAKING, "Breaking Changes"),
    (CommitType.FEAT, "Features"),
    (CommitType.FIX, "Bug Fixes"),
    (CommitType.PERF, "Performance Improvements"),
    (CommitType.REFACTOR, "Code Refactoring"),
    (CommitType.DOCS, "Documentation"),
    (CommitType.TEST, "Tests"),
    (CommitType.BUILD, "Build System"),
    (CommitType.CI, "CI/CD"),
    (CommitType.CHORE, "Chores"),
    (CommitType.REVERT, "Reverts"),
]


@dataclass
class ChangelogEntry:
    """A single changelog entry (version release)."""

    version: Version | str
    date: date | None = None
    commits: list[Commit] = field(default_factory=list)
    breaking_changes: list[Commit] = field(default_factory=list)
    compare_url: str | None = None  # URL to compare with previous version

    @property
    def version_str(self) -> str:
        """Get version as string."""
        return str(self.version)

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return bool(self.commits) or bool(self.breaking_changes)


def generate_changelog(
    commits: Sequence[Commit],
    version: Version | str,
    previous_version: Version | str | None = None,
    release_date: date | None = None,
    repo_url: str | None = None,
    include_hash: bool = True,
    group_by_scope: bool = False,
) -> str:
    """
    Generate markdown changelog from commits.

    Args:
        commits: List of commits to include
        version: Version being released
        previous_version: Previous version (for compare URL)
        release_date: Release date (defaults to today)
        repo_url: Repository URL for commit links
        include_hash: Include commit hashes
        group_by_scope: Group by scope within each type

    Returns:
        Markdown formatted changelog
    """
    if release_date is None:
        release_date = date.today()

    lines = []

    # Header
    version_str = str(version)
    date_str = release_date.isoformat()

    if repo_url and previous_version:
        compare_url = f"{repo_url}/compare/v{previous_version}...v{version_str}"
        lines.append(f"## [{version_str}]({compare_url}) ({date_str})")
    else:
        lines.append(f"## {version_str} ({date_str})")

    lines.append("")

    # Collect breaking changes
    breaking_changes = [c for c in commits if c.breaking]

    # Group commits by type
    groups = group_commits_by_type(commits)

    # Add breaking changes section first
    if breaking_changes:
        lines.append("### Breaking Changes")
        lines.append("")
        for commit in breaking_changes:
            lines.append(_format_commit_line(commit, repo_url, include_hash))
            if commit.breaking_description:
                lines.append(f"  - {commit.breaking_description}")
        lines.append("")

    # Add other sections in order
    for commit_type, section_title in SECTION_ORDER:
        if commit_type == CommitType.BREAKING:
            continue  # Already handled

        type_key = commit_type.value
        if type_key not in groups:
            continue

        type_commits = groups[type_key]
        # Filter out commits already shown in breaking
        type_commits = [c for c in type_commits if not c.breaking]

        if not type_commits:
            continue

        lines.append(f"### {section_title}")
        lines.append("")

        if group_by_scope:
            # Group by scope
            scoped = {}
            unscoped = []
            for commit in type_commits:
                if commit.scope:
                    if commit.scope not in scoped:
                        scoped[commit.scope] = []
                    scoped[commit.scope].append(commit)
                else:
                    unscoped.append(commit)

            for scope in sorted(scoped.keys()):
                lines.append(f"**{scope}:**")
                for commit in scoped[scope]:
                    lines.append(_format_commit_line(commit, repo_url, include_hash, indent=True))
                lines.append("")

            if unscoped:
                for commit in unscoped:
                    lines.append(_format_commit_line(commit, repo_url, include_hash))
        else:
            for commit in type_commits:
                lines.append(_format_commit_line(commit, repo_url, include_hash))

        lines.append("")

    # Handle "other" commits (non-conventional)
    if "other" in groups:
        other_commits = [c for c in groups["other"] if not c.breaking]
        if other_commits:
            lines.append("### Other Changes")
            lines.append("")
            for commit in other_commits:
                lines.append(_format_commit_line(commit, repo_url, include_hash))
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def generate_full_changelog(
    entries: Sequence[ChangelogEntry],
    title: str = "Changelog",
    description: str | None = None,
    repo_url: str | None = None,
    include_hash: bool = True,
) -> str:
    """
    Generate a complete changelog file from multiple entries.

    Args:
        entries: List of changelog entries (newest first)
        title: Changelog title
        description: Optional description text
        repo_url: Repository URL for commit links
        include_hash: Include commit hashes

    Returns:
        Full markdown changelog
    """
    lines = [f"# {title}", ""]

    if description:
        lines.extend([description, ""])

    for entry in entries:
        previous = None
        # Find previous entry for compare URL
        idx = list(entries).index(entry)
        if idx < len(entries) - 1:
            previous = entries[idx + 1].version

        entry_md = generate_changelog(
            commits=entry.commits,
            version=entry.version,
            previous_version=previous,
            release_date=entry.date,
            repo_url=repo_url,
            include_hash=include_hash,
        )
        lines.append(entry_md)

    return "\n".join(lines)


def _format_commit_line(
    commit: Commit,
    repo_url: str | None = None,
    include_hash: bool = True,
    indent: bool = False,
) -> str:
    """Format a single commit as a markdown list item."""
    prefix = "  -" if indent else "-"
    parts = [prefix]

    # Scope
    if commit.scope:
        parts.append(f"**{commit.scope}:**")

    # Description
    parts.append(commit.description)

    # Commit link
    if include_hash and commit.hash:
        if repo_url:
            parts.append(f"([{commit.hash[:7]}]({repo_url}/commit/{commit.hash}))")
        else:
            parts.append(f"({commit.hash[:7]})")

    return " ".join(parts)


def create_changelog_entry(
    version: Version | str,
    commits: Sequence[Commit],
    release_date: date | None = None,
) -> ChangelogEntry:
    """
    Create a changelog entry from commits.

    Args:
        version: Version for this release
        commits: Commits in this release
        release_date: Release date (defaults to today)

    Returns:
        ChangelogEntry object
    """
    breaking = [c for c in commits if c.breaking]

    return ChangelogEntry(
        version=version,
        date=release_date or date.today(),
        commits=list(commits),
        breaking_changes=breaking,
    )
