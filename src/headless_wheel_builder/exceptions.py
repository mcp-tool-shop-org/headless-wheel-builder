"""Custom exceptions for Headless Wheel Builder.

Error contract (Shipcheck Tier 1):
    All HWBError subclasses emit { code, message, hint, cause?, retryable? }

Exit codes (CLI):
    0 = ok
    1 = user error (bad input, invalid config, missing arguments)
    2 = runtime error (build failure, IO, network, unexpected crash)
    130 = interrupted (KeyboardInterrupt)
"""

from __future__ import annotations

# Exit code constants
EXIT_OK = 0
EXIT_USER = 1
EXIT_RUNTIME = 2


class HWBError(Exception):
    """Base exception for Headless Wheel Builder."""

    error_code: str = "RUNTIME_UNKNOWN"
    hint: str | None = None
    retryable: bool = False
    exit_code: int = EXIT_RUNTIME

    def __init__(
        self,
        message: str,
        *,
        hint: str | None = None,
        retryable: bool | None = None,
    ):
        super().__init__(message)
        if hint is not None:
            self.hint = hint
        if retryable is not None:
            self.retryable = retryable


class SourceError(HWBError):
    """Error resolving or accessing source."""

    error_code = "IO_SOURCE"


class GitError(SourceError):
    """Git operation failed."""

    error_code = "IO_GIT"

    def __init__(self, message: str, stderr: str = "", **kwargs: object):
        super().__init__(message, **kwargs)  # type: ignore[arg-type]
        self.stderr = stderr


class ProjectError(HWBError):
    """Error analyzing project."""

    error_code = "CONFIG_PROJECT"
    exit_code = EXIT_USER


class BuildError(HWBError):
    """Build-related error."""

    error_code = "RUNTIME_BUILD"

    def __init__(self, message: str, build_log: str = "", **kwargs: object):
        super().__init__(message, **kwargs)  # type: ignore[arg-type]
        self.build_log = build_log


class IsolationError(HWBError):
    """Error creating or managing isolated environment."""

    error_code = "RUNTIME_ISOLATION"


class DependencyError(HWBError):
    """Error installing dependencies."""

    error_code = "DEP_INSTALL"

    def __init__(self, message: str, package: str | None = None, **kwargs: object):
        super().__init__(message, **kwargs)  # type: ignore[arg-type]
        self.package = package


class PublishError(HWBError):
    """Error publishing package."""

    error_code = "RUNTIME_PUBLISH"


class AuthenticationError(PublishError):
    """Authentication failed."""

    error_code = "PERM_AUTH"
    exit_code = EXIT_USER


class VersionError(HWBError):
    """Error with version management."""

    error_code = "INPUT_VERSION"
    exit_code = EXIT_USER


class ConfigError(HWBError):
    """Configuration error."""

    error_code = "CONFIG_INVALID"
    exit_code = EXIT_USER


# =============================================================================
# GitHub Errors
# =============================================================================


class GitHubError(HWBError):
    """GitHub API or operation error."""

    error_code = "RUNTIME_GITHUB"

    def __init__(self, message: str, status_code: int | None = None, **kwargs: object):
        super().__init__(message, **kwargs)  # type: ignore[arg-type]
        self.status_code = status_code


class GitHubAuthError(GitHubError):
    """GitHub authentication failed."""

    error_code = "PERM_GITHUB_AUTH"
    exit_code = EXIT_USER

    def __init__(self, message: str = "GitHub authentication failed"):
        super().__init__(message, status_code=401)


class GitHubRateLimitError(GitHubError):
    """GitHub API rate limit exceeded."""

    error_code = "RUNTIME_RATE_LIMIT"
    retryable = True

    def __init__(self, message: str, reset_timestamp: int = 0):
        super().__init__(message, status_code=403)
        self.reset_timestamp = reset_timestamp


# =============================================================================
# Pipeline Errors
# =============================================================================


class PipelineError(HWBError):
    """Pipeline execution error."""

    error_code = "RUNTIME_PIPELINE"

    def __init__(self, message: str, stage: str | None = None, **kwargs: object):
        super().__init__(message, **kwargs)  # type: ignore[arg-type]
        self.stage = stage


class StageError(PipelineError):
    """Error in a specific pipeline stage."""

    error_code = "RUNTIME_STAGE"


# =============================================================================
# Notification Errors
# =============================================================================


class NotificationError(HWBError):
    """Notification delivery error."""

    error_code = "RUNTIME_NOTIFY"

    def __init__(self, message: str, provider: str | None = None, **kwargs: object):
        super().__init__(message, **kwargs)  # type: ignore[arg-type]
        self.provider = provider
