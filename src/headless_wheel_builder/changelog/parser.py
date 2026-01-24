"""Parser for Conventional Commits."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar


class CommitType(Enum):
    """Conventional commit types."""

    FEAT = "feat"
    FIX = "fix"
    DOCS = "docs"
    STYLE = "style"
    REFACTOR = "refactor"
    PERF = "perf"
    TEST = "test"
    BUILD = "build"
    CI = "ci"
    CHORE = "chore"
    REVERT = "revert"
    OTHER = "other"

    @classmethod
    def from_string(cls, value: str) -> CommitType:
        """Parse commit type from string."""
        value_lower = value.lower()
        for member in cls:
            if member.value == value_lower:
                return member
        return cls.OTHER


@dataclass
class ConventionalCommit:
    """Parsed conventional commit.

    Follows the Conventional Commits specification:
    https://www.conventionalcommits.org/

    Format: <type>[optional scope]: <description>

    [optional body]

    [optional footer(s)]
    """

    raw: str
    type: CommitType
    scope: str | None
    description: str
    body: str | None = None
    breaking: bool = False
    breaking_description: str | None = None
    footers: dict[str, str] = field(default_factory=lambda: {})
    sha: str | None = None

    # Regex pattern for parsing conventional commits
    PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"^(?P<type>\w+)"  # type (feat, fix, etc.)
        r"(?:\((?P<scope>[^)]+)\))?"  # optional scope in parentheses
        r"(?P<breaking>!)?"  # optional breaking change indicator
        r":\s*"  # colon separator
        r"(?P<description>.+)$",  # description
        re.MULTILINE,
    )

    # Footer patterns
    FOOTER_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"^(?P<token>[\w-]+|BREAKING CHANGE)(?::\s*|\s+#)(?P<value>.+)$",
        re.MULTILINE,
    )

    @classmethod
    def parse(cls, message: str, sha: str | None = None) -> ConventionalCommit | None:
        """Parse a commit message into a ConventionalCommit.

        Args:
            message: Git commit message
            sha: Optional commit SHA

        Returns:
            ConventionalCommit if message follows convention, None otherwise
        """
        if not message:
            return None

        lines = message.strip().split("\n")
        first_line = lines[0].strip()

        match = cls.PATTERN.match(first_line)
        if not match:
            return None

        type_str = match.group("type")
        scope = match.group("scope")
        breaking_indicator = match.group("breaking") == "!"
        description = match.group("description").strip()

        # Parse body and footers
        body = None
        footers: dict[str, str] = {}
        breaking_description = None

        if len(lines) > 1:
            # Skip empty lines after first line
            content_start = 1
            while content_start < len(lines) and not lines[content_start].strip():
                content_start += 1

            if content_start < len(lines):
                remaining = "\n".join(lines[content_start:])

                # Find footers (at the end)
                footer_section: list[str] = []
                body_lines: list[str] = []
                in_footer = False

                for line in remaining.split("\n"):
                    footer_match = cls.FOOTER_PATTERN.match(line)
                    if footer_match:
                        in_footer = True
                        token = footer_match.group("token")
                        value = footer_match.group("value")
                        footers[token] = value
                        footer_section.append(line)

                        if token == "BREAKING CHANGE":
                            breaking_description = value
                    elif in_footer and line.startswith(" "):
                        # Continuation of previous footer
                        if footer_section:
                            last_token = list(footers.keys())[-1]
                            footers[last_token] += "\n" + line.strip()
                            if last_token == "BREAKING CHANGE":
                                breaking_description = footers[last_token]
                    else:
                        if in_footer:
                            # Footer section ended, this is unexpected content
                            body_lines.append(line)
                        else:
                            body_lines.append(line)

                if body_lines:
                    body = "\n".join(body_lines).strip() or None

        breaking = breaking_indicator or "BREAKING CHANGE" in footers

        return cls(
            raw=message,
            type=CommitType.from_string(type_str),
            scope=scope,
            description=description,
            body=body,
            breaking=breaking,
            breaking_description=breaking_description,
            footers=footers,
            sha=sha,
        )

    @property
    def summary(self) -> str:
        """Get one-line summary of the commit."""
        if self.scope:
            return f"{self.type.value}({self.scope}): {self.description}"
        return f"{self.type.value}: {self.description}"

    @property
    def is_feature(self) -> bool:
        """Check if this is a feature commit."""
        return self.type == CommitType.FEAT

    @property
    def is_fix(self) -> bool:
        """Check if this is a fix commit."""
        return self.type == CommitType.FIX

    @property
    def is_notable(self) -> bool:
        """Check if this commit should appear in changelog."""
        return (
            self.type
            in (
                CommitType.FEAT,
                CommitType.FIX,
                CommitType.PERF,
                CommitType.REVERT,
            )
            or self.breaking
        )


def parse_commit(message: str, sha: str | None = None) -> ConventionalCommit | None:
    """Parse a single commit message.

    Args:
        message: Git commit message
        sha: Optional commit SHA

    Returns:
        ConventionalCommit if valid, None otherwise
    """
    return ConventionalCommit.parse(message, sha)


def parse_commits(
    commits: list[tuple[str, str]],
    include_non_conventional: bool = False,
) -> list[ConventionalCommit]:
    """Parse multiple commit messages.

    Args:
        commits: List of (sha, message) tuples
        include_non_conventional: If True, create OTHER type for non-conventional commits

    Returns:
        List of parsed ConventionalCommits
    """
    result: list[ConventionalCommit] = []

    for sha, message in commits:
        parsed = ConventionalCommit.parse(message, sha)
        if parsed:
            result.append(parsed)
        elif include_non_conventional and message:
            # Create an OTHER type commit for non-conventional messages
            first_line = message.strip().split("\n")[0]
            result.append(
                ConventionalCommit(
                    raw=message,
                    type=CommitType.OTHER,
                    scope=None,
                    description=first_line,
                    sha=sha,
                )
            )

    return result
