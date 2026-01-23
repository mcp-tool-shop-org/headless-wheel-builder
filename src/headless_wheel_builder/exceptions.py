"""Custom exceptions for Headless Wheel Builder."""

from __future__ import annotations


class HWBError(Exception):
    """Base exception for Headless Wheel Builder."""

    pass


class SourceError(HWBError):
    """Error resolving or accessing source."""

    pass


class GitError(SourceError):
    """Git operation failed."""

    def __init__(self, message: str, stderr: str = ""):
        super().__init__(message)
        self.stderr = stderr


class ProjectError(HWBError):
    """Error analyzing project."""

    pass


class BuildError(HWBError):
    """Build-related error."""

    def __init__(self, message: str, build_log: str = ""):
        super().__init__(message)
        self.build_log = build_log


class IsolationError(HWBError):
    """Error creating or managing isolated environment."""

    pass


class DependencyError(HWBError):
    """Error installing dependencies."""

    def __init__(self, message: str, package: str | None = None):
        super().__init__(message)
        self.package = package


class PublishError(HWBError):
    """Error publishing package."""

    pass


class AuthenticationError(PublishError):
    """Authentication failed."""

    pass


class VersionError(HWBError):
    """Error with version management."""

    pass


class ConfigError(HWBError):
    """Configuration error."""

    pass
