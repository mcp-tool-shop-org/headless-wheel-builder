"""Semantic versioning utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from headless_wheel_builder.exceptions import VersionError


class BumpType(Enum):
    """Type of version bump."""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    PRERELEASE = "prerelease"
    BUILD = "build"


# SemVer regex pattern
# https://semver.org/#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string
SEMVER_PATTERN = re.compile(
    r"^v?"  # Optional v prefix
    r"(?P<major>0|[1-9]\d*)"
    r"\.(?P<minor>0|[1-9]\d*)"
    r"\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<build>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)

# Relaxed pattern for common version formats
RELAXED_PATTERN = re.compile(
    r"^v?"
    r"(?P<major>\d+)"
    r"(?:\.(?P<minor>\d+))?"
    r"(?:\.(?P<patch>\d+))?"
    r"(?:[.-]?(?P<prerelease>(?:alpha|beta|rc|dev|a|b|c)\.?\d*))?"
    r"(?:\+(?P<build>.+))?$",
    re.IGNORECASE,
)


@dataclass(frozen=True, order=True)
class Version:
    """
    Semantic version representation.

    Follows SemVer 2.0.0 specification: https://semver.org/

    Examples:
        >>> v = Version(1, 2, 3)
        >>> str(v)
        '1.2.3'

        >>> v = Version(2, 0, 0, prerelease="alpha.1")
        >>> str(v)
        '2.0.0-alpha.1'
    """

    major: int
    minor: int
    patch: int
    prerelease: str | None = None
    build: str | None = None

    def __post_init__(self):
        """Validate version components."""
        if self.major < 0 or self.minor < 0 or self.patch < 0:
            raise VersionError("Version components cannot be negative")

    def __str__(self) -> str:
        """Return string representation."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    def __repr__(self) -> str:
        return f"Version({self.major}, {self.minor}, {self.patch}, prerelease={self.prerelease!r}, build={self.build!r})"

    @property
    def is_prerelease(self) -> bool:
        """Check if this is a prerelease version."""
        return self.prerelease is not None

    @property
    def is_stable(self) -> bool:
        """Check if this is a stable release (>= 1.0.0 and not prerelease)."""
        return self.major >= 1 and not self.is_prerelease

    @property
    def base_version(self) -> Version:
        """Get base version without prerelease/build."""
        return Version(self.major, self.minor, self.patch)

    def bump(self, bump_type: BumpType | str) -> Version:
        """
        Create a new version with the specified bump.

        Args:
            bump_type: Type of version bump

        Returns:
            New Version instance

        Examples:
            >>> v = Version(1, 2, 3)
            >>> v.bump("patch")
            Version(1, 2, 4)
            >>> v.bump("minor")
            Version(1, 3, 0)
            >>> v.bump("major")
            Version(2, 0, 0)
        """
        if isinstance(bump_type, str):
            bump_type = BumpType(bump_type)

        if bump_type == BumpType.MAJOR:
            return Version(self.major + 1, 0, 0)
        elif bump_type == BumpType.MINOR:
            return Version(self.major, self.minor + 1, 0)
        elif bump_type == BumpType.PATCH:
            return Version(self.major, self.minor, self.patch + 1)
        elif bump_type == BumpType.PRERELEASE:
            # Increment prerelease or add one
            new_pre = _increment_prerelease(self.prerelease) if self.prerelease else "alpha.1"
            return Version(self.major, self.minor, self.patch, prerelease=new_pre)
        else:
            raise VersionError(f"Unsupported bump type: {bump_type}")

    def with_prerelease(self, prerelease: str) -> Version:
        """Create version with prerelease identifier."""
        return Version(self.major, self.minor, self.patch, prerelease=prerelease, build=self.build)

    def with_build(self, build: str) -> Version:
        """Create version with build metadata."""
        return Version(self.major, self.minor, self.patch, prerelease=self.prerelease, build=build)

    def to_pep440(self) -> str:
        """Convert to PEP 440 compatible version string."""
        version = f"{self.major}.{self.minor}.{self.patch}"

        if self.prerelease:
            # Convert common prerelease formats to PEP 440
            pre = self.prerelease.lower()
            if pre.startswith("alpha"):
                version += f"a{_extract_prerelease_num(pre)}"
            elif pre.startswith("beta"):
                version += f"b{_extract_prerelease_num(pre)}"
            elif pre.startswith("rc"):
                version += f"rc{_extract_prerelease_num(pre)}"
            elif pre.startswith("dev"):
                version += f".dev{_extract_prerelease_num(pre)}"
            else:
                # Generic prerelease
                version += f".dev{_extract_prerelease_num(pre)}"

        if self.build:
            version += f"+{self.build}"

        return version


def parse_version(version_str: str, strict: bool = False) -> Version:
    """
    Parse a version string into a Version object.

    Args:
        version_str: Version string to parse
        strict: If True, only accept strict SemVer format

    Returns:
        Version object

    Raises:
        VersionError: If version string is invalid

    Examples:
        >>> parse_version("1.2.3")
        Version(1, 2, 3)
        >>> parse_version("v2.0.0-alpha.1+build.123")
        Version(2, 0, 0, prerelease='alpha.1', build='build.123')
    """
    if not version_str:
        raise VersionError("Version string cannot be empty")

    # Try strict SemVer first
    match = SEMVER_PATTERN.match(version_str.strip())

    if match:
        groups = match.groupdict()
        return Version(
            major=int(groups["major"]),
            minor=int(groups["minor"]),
            patch=int(groups["patch"]),
            prerelease=groups.get("prerelease"),
            build=groups.get("build"),
        )

    if strict:
        raise VersionError(f"Invalid SemVer: {version_str}")

    # Try relaxed pattern
    match = RELAXED_PATTERN.match(version_str.strip())

    if match:
        groups = match.groupdict()
        return Version(
            major=int(groups["major"]),
            minor=int(groups["minor"] or 0),
            patch=int(groups["patch"] or 0),
            prerelease=groups.get("prerelease"),
            build=groups.get("build"),
        )

    raise VersionError(f"Unable to parse version: {version_str}")


def bump_version(
    version: str | Version,
    bump_type: BumpType | str,
) -> Version:
    """
    Bump a version.

    Args:
        version: Current version (string or Version)
        bump_type: Type of bump to apply

    Returns:
        New bumped Version

    Examples:
        >>> bump_version("1.2.3", "patch")
        Version(1, 2, 4)
        >>> bump_version("1.2.3", "minor")
        Version(1, 3, 0)
    """
    if isinstance(version, str):
        version = parse_version(version)

    return version.bump(bump_type)


def compare_versions(v1: str | Version, v2: str | Version) -> int:
    """
    Compare two versions.

    Returns:
        -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
    """
    if isinstance(v1, str):
        v1 = parse_version(v1)
    if isinstance(v2, str):
        v2 = parse_version(v2)

    # Compare major.minor.patch
    for a, b in [(v1.major, v2.major), (v1.minor, v2.minor), (v1.patch, v2.patch)]:
        if a < b:
            return -1
        if a > b:
            return 1

    # Prerelease comparison
    # No prerelease > prerelease
    if v1.prerelease is None and v2.prerelease is not None:
        return 1
    if v1.prerelease is not None and v2.prerelease is None:
        return -1
    if v1.prerelease and v2.prerelease:
        if v1.prerelease < v2.prerelease:
            return -1
        if v1.prerelease > v2.prerelease:
            return 1

    return 0


def _increment_prerelease(prerelease: str) -> str:
    """Increment prerelease identifier."""
    # Try to find a number at the end
    match = re.search(r"(\d+)$", prerelease)
    if match:
        num = int(match.group(1))
        return prerelease[: match.start()] + str(num + 1)

    # No number found, add .1
    return f"{prerelease}.1"


def _extract_prerelease_num(prerelease: str) -> int:
    """Extract number from prerelease string."""
    match = re.search(r"(\d+)", prerelease)
    if match:
        return int(match.group(1))
    return 0
