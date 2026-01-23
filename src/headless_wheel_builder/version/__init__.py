"""Versioning module for automatic version management."""

from headless_wheel_builder.version.semver import (
    Version,
    BumpType,
    parse_version,
    bump_version,
)
from headless_wheel_builder.version.conventional import (
    Commit,
    CommitType,
    parse_commit,
    determine_bump_from_commits,
)
from headless_wheel_builder.version.git import (
    get_latest_tag,
    get_commits_since_tag,
    create_tag,
)
from headless_wheel_builder.version.changelog import (
    ChangelogEntry,
    generate_changelog,
)

__all__ = [
    # SemVer
    "Version",
    "BumpType",
    "parse_version",
    "bump_version",
    # Conventional Commits
    "Commit",
    "CommitType",
    "parse_commit",
    "determine_bump_from_commits",
    # Git
    "get_latest_tag",
    "get_commits_since_tag",
    "create_tag",
    # Changelog
    "ChangelogEntry",
    "generate_changelog",
]
