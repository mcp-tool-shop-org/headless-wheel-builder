"""Changelog generator from git commits."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any

from headless_wheel_builder.changelog.parser import (
    CommitType,
    ConventionalCommit,
    parse_commits,
)

if TYPE_CHECKING:
    from pathlib import Path


class ChangelogFormat(Enum):
    """Output format for changelog."""

    MARKDOWN = "markdown"
    PLAIN = "plain"
    JSON = "json"
    GITHUB = "github"  # GitHub release format


@dataclass
class ChangelogConfig:
    """Configuration for changelog generation.

    Attributes:
        repo_path: Path to git repository
        from_ref: Starting ref (tag, commit, or branch)
        to_ref: Ending ref (default: HEAD)
        tag: Release tag for header
        include_all: Include non-conventional commits
        group_by_type: Group commits by type
        show_sha: Show commit SHAs
        show_scope: Show commit scopes
        format: Output format
        breaking_header: Header for breaking changes
        sections: Custom section order and headers
    """

    repo_path: str | Path = "."
    from_ref: str | None = None
    to_ref: str = "HEAD"
    tag: str | None = None
    include_all: bool = False
    group_by_type: bool = True
    show_sha: bool = True
    show_scope: bool = True
    format: ChangelogFormat = ChangelogFormat.MARKDOWN
    breaking_header: str = "⚠️ BREAKING CHANGES"
    sections: dict[CommitType, str] = field(
        default_factory=lambda: {
            CommitType.FEAT: "✨ Features",
            CommitType.FIX: "🐛 Bug Fixes",
            CommitType.PERF: "⚡ Performance",
            CommitType.DOCS: "📚 Documentation",
            CommitType.REFACTOR: "♻️ Refactoring",
            CommitType.TEST: "✅ Tests",
            CommitType.BUILD: "📦 Build",
            CommitType.CI: "🔧 CI/CD",
            CommitType.CHORE: "🧹 Chores",
            CommitType.REVERT: "⏪ Reverts",
            CommitType.OTHER: "📝 Other Changes",
        }
    )


@dataclass
class ChangelogEntry:
    """Single changelog entry."""

    commit: ConventionalCommit
    formatted: str

    @classmethod
    def from_commit(
        cls,
        commit: ConventionalCommit,
        show_sha: bool = True,
        show_scope: bool = True,
    ) -> ChangelogEntry:
        """Create entry from commit.

        Args:
            commit: Parsed conventional commit
            show_sha: Include commit SHA
            show_scope: Include scope in output

        Returns:
            Formatted ChangelogEntry
        """
        parts: list[str] = []

        # Scope
        if show_scope and commit.scope:
            parts.append(f"**{commit.scope}:**")

        # Description
        parts.append(commit.description)

        # SHA
        if show_sha and commit.sha:
            short_sha = commit.sha[:7]
            parts.append(f"({short_sha})")

        formatted = " ".join(parts)
        return cls(commit=commit, formatted=formatted)


@dataclass
class Changelog:
    """Generated changelog."""

    config: ChangelogConfig
    commits: list[ConventionalCommit]
    breaking_changes: list[ConventionalCommit] = field(default_factory=lambda: [])
    entries_by_type: dict[CommitType, list[ChangelogEntry]] = field(default_factory=lambda: {})
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Process commits into entries."""
        # Extract breaking changes
        self.breaking_changes = [c for c in self.commits if c.breaking]

        # Group by type
        for commit in self.commits:
            if commit.type not in self.entries_by_type:
                self.entries_by_type[commit.type] = []
            entry = ChangelogEntry.from_commit(
                commit,
                show_sha=self.config.show_sha,
                show_scope=self.config.show_scope,
            )
            self.entries_by_type[commit.type].append(entry)

    def to_markdown(self) -> str:
        """Generate markdown changelog."""
        lines: list[str] = []

        # Header
        if self.config.tag:
            lines.append(f"## {self.config.tag}")
            lines.append("")

        # Breaking changes first
        if self.breaking_changes:
            lines.append(f"### {self.config.breaking_header}")
            lines.append("")
            for commit in self.breaking_changes:
                desc = commit.breaking_description or commit.description
                if commit.scope:
                    lines.append(f"- **{commit.scope}:** {desc}")
                else:
                    lines.append(f"- {desc}")
            lines.append("")

        # Grouped sections
        if self.config.group_by_type:
            # Order by configured sections
            for commit_type, header in self.config.sections.items():
                entries = self.entries_by_type.get(commit_type, [])
                if entries:
                    lines.append(f"### {header}")
                    lines.append("")
                    for entry in entries:
                        lines.append(f"- {entry.formatted}")
                    lines.append("")
        else:
            # Flat list
            for entries in self.entries_by_type.values():
                for entry in entries:
                    lines.append(f"- {entry.formatted}")
            if self.entries_by_type:
                lines.append("")

        return "\n".join(lines)

    def to_plain(self) -> str:
        """Generate plain text changelog."""
        lines: list[str] = []

        if self.config.tag:
            lines.append(f"Release {self.config.tag}")
            lines.append("=" * (8 + len(self.config.tag)))
            lines.append("")

        if self.breaking_changes:
            lines.append("BREAKING CHANGES:")
            for commit in self.breaking_changes:
                desc = commit.breaking_description or commit.description
                lines.append(f"  * {desc}")
            lines.append("")

        if self.config.group_by_type:
            for commit_type, header in self.config.sections.items():
                entries = self.entries_by_type.get(commit_type, [])
                if entries:
                    # Strip emoji from header
                    clean_header = header.split(" ", 1)[-1] if " " in header else header
                    lines.append(f"{clean_header}:")
                    for entry in entries:
                        lines.append(f"  * {entry.formatted}")
                    lines.append("")
        else:
            for entries in self.entries_by_type.values():
                for entry in entries:
                    lines.append(f"* {entry.formatted}")

        return "\n".join(lines)

    def to_github(self) -> str:
        """Generate GitHub release notes format."""
        lines: list[str] = []

        # What's Changed header
        lines.append("## What's Changed")
        lines.append("")

        # Breaking changes
        if self.breaking_changes:
            lines.append(f"### {self.config.breaking_header}")
            lines.append("")
            for commit in self.breaking_changes:
                desc = commit.breaking_description or commit.description
                lines.append(f"* {desc}")
            lines.append("")

        # Group by type with GitHub-friendly format
        for commit_type in [CommitType.FEAT, CommitType.FIX, CommitType.PERF]:
            entries = self.entries_by_type.get(commit_type, [])
            if entries:
                header = self.config.sections.get(commit_type, commit_type.value)
                lines.append(f"### {header}")
                lines.append("")
                for entry in entries:
                    lines.append(f"* {entry.formatted}")
                lines.append("")

        # Other changes (collapsed)
        other_types = [
            t for t in CommitType if t not in (CommitType.FEAT, CommitType.FIX, CommitType.PERF)
        ]
        other_entries: list[ChangelogEntry] = []
        for commit_type in other_types:
            other_entries.extend(self.entries_by_type.get(commit_type, []))

        if other_entries:
            lines.append("### 📝 Other Changes")
            lines.append("")
            for entry in other_entries:
                lines.append(f"* {entry.formatted}")
            lines.append("")

        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        """Generate JSON changelog."""
        return {
            "tag": self.config.tag,
            "generated_at": self.generated_at.isoformat(),
            "breaking_changes": [
                {
                    "type": c.type.value,
                    "scope": c.scope,
                    "description": c.breaking_description or c.description,
                    "sha": c.sha,
                }
                for c in self.breaking_changes
            ],
            "sections": {
                commit_type.value: [
                    {
                        "description": e.commit.description,
                        "scope": e.commit.scope,
                        "sha": e.commit.sha,
                        "breaking": e.commit.breaking,
                    }
                    for e in entries
                ]
                for commit_type, entries in self.entries_by_type.items()
            },
            "stats": {
                "total_commits": len(self.commits),
                "breaking_changes": len(self.breaking_changes),
                "features": len(self.entries_by_type.get(CommitType.FEAT, [])),
                "fixes": len(self.entries_by_type.get(CommitType.FIX, [])),
            },
        }

    def render(self) -> str:
        """Render changelog in configured format."""
        if self.config.format == ChangelogFormat.MARKDOWN:
            return self.to_markdown()
        elif self.config.format == ChangelogFormat.PLAIN:
            return self.to_plain()
        elif self.config.format == ChangelogFormat.GITHUB:
            return self.to_github()
        elif self.config.format == ChangelogFormat.JSON:
            import json

            return json.dumps(self.to_json(), indent=2)
        else:
            return self.to_markdown()


def get_commits_between(
    from_ref: str | None,
    to_ref: str = "HEAD",
    repo_path: str | Path = ".",
) -> list[tuple[str, str]]:
    """Get git commits between two refs.

    Args:
        from_ref: Starting ref (exclusive). If None, gets last 20 commits.
        to_ref: Ending ref (inclusive)
        repo_path: Path to repository

    Returns:
        List of (sha, message) tuples
    """
    git_range = f"{from_ref}..{to_ref}" if from_ref else f"-20 {to_ref}"

    try:
        result = subprocess.run(
            ["git", "log", "--pretty=format:%H%x00%B%x00", git_range],
            capture_output=True,
            text=True,
            cwd=str(repo_path),
            check=False,
        )

        if result.returncode != 0:
            return []

        commits: list[tuple[str, str]] = []
        parts = result.stdout.split("\x00")

        i = 0
        while i < len(parts) - 1:
            sha = parts[i].strip()
            message = parts[i + 1].strip()
            if sha and message:
                commits.append((sha, message))
            i += 2

        return commits

    except Exception:
        return []


def find_previous_tag(repo_path: str | Path = ".") -> str | None:
    """Find the most recent tag before HEAD.

    Args:
        repo_path: Path to repository

    Returns:
        Tag name or None if not found
    """
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0", "HEAD^"],
            capture_output=True,
            text=True,
            cwd=str(repo_path),
            check=False,
        )

        if result.returncode == 0:
            return result.stdout.strip()
        return None

    except Exception:
        return None


def generate_changelog(
    config: ChangelogConfig | None = None,
    *,
    from_ref: str | None = None,
    to_ref: str = "HEAD",
    tag: str | None = None,
    repo_path: str | Path = ".",
    format: ChangelogFormat = ChangelogFormat.MARKDOWN,
) -> Changelog:
    """Generate a changelog from git commits.

    Args:
        config: Full configuration (overrides other args if provided)
        from_ref: Starting ref (finds previous tag if None)
        to_ref: Ending ref
        tag: Release tag for header
        repo_path: Path to repository
        format: Output format

    Returns:
        Generated Changelog
    """
    if config is None:
        # Auto-detect from_ref if not provided
        if from_ref is None:
            from_ref = find_previous_tag(repo_path)

        config = ChangelogConfig(
            repo_path=repo_path,
            from_ref=from_ref,
            to_ref=to_ref,
            tag=tag,
            format=format,
        )

    # Get commits
    commits_raw = get_commits_between(
        config.from_ref,
        config.to_ref,
        config.repo_path,
    )

    # Parse commits
    commits = parse_commits(commits_raw, include_non_conventional=config.include_all)

    # Filter to notable commits unless including all
    if not config.include_all:
        commits = [c for c in commits if c.is_notable]

    return Changelog(config=config, commits=commits)
