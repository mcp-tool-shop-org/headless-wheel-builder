"""Versioning module for automatic version management."""

from headless_wheel_builder.version.changelog import (
    ChangelogEntry,
    generate_changelog,
)
from headless_wheel_builder.version.conventional import (
    Commit,
    CommitType,
    determine_bump_from_commits,
    parse_commit,
)
from headless_wheel_builder.version.git import (
    create_tag,
    get_commits_since_tag,
    get_latest_tag,
)
from headless_wheel_builder.version.semver import (
    BumpType,
    Version,
    bump_version,
    parse_version,
)

__all__ = [
    "BumpType",
    # Changelog
    "ChangelogEntry",
    # Conventional Commits
    "Commit",
    "CommitType",
    # SemVer
    "Version",
    "bump_version",
    "create_tag",
    "determine_bump_from_commits",
    "generate_changelog",
    "get_commits_since_tag",
    # Git
    "get_latest_tag",
    "parse_commit",
    "parse_version",
]
