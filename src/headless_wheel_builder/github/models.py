"""Data models for GitHub operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path
    pass


class ReleaseType(Enum):
    """Type of release."""

    RELEASE = "release"
    PRERELEASE = "prerelease"
    DRAFT = "draft"


@dataclass
class GitHubConfig:
    """Configuration for GitHub operations.

    Attributes:
        token: GitHub personal access token or fine-grained token.
               Falls back to GITHUB_TOKEN environment variable.
        base_url: GitHub API base URL. Defaults to api.github.com.
                  Set to your GHE URL for GitHub Enterprise.
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retries for failed requests.
        retry_delay: Initial delay between retries (exponential backoff).
    """

    token: str | None = None
    base_url: str = "https://api.github.com"
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0

    def __post_init__(self) -> None:
        """Resolve token from environment if not provided."""
        import os

        if self.token is None:
            self.token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

        # Normalize base URL
        self.base_url = self.base_url.rstrip("/")


@dataclass
class Repository:
    """GitHub repository information."""

    owner: str
    name: str
    full_name: str
    description: str | None = None
    private: bool = False
    default_branch: str = "main"
    html_url: str = ""
    clone_url: str = ""
    ssh_url: str = ""

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Repository:
        """Create from GitHub API response."""
        return cls(
            owner=data["owner"]["login"],
            name=data["name"],
            full_name=data["full_name"],
            description=data.get("description"),
            private=data.get("private", False),
            default_branch=data.get("default_branch", "main"),
            html_url=data.get("html_url", ""),
            clone_url=data.get("clone_url", ""),
            ssh_url=data.get("ssh_url", ""),
        )

    @classmethod
    def parse(cls, repo_str: str) -> Repository:
        """Parse 'owner/repo' string into Repository.

        Args:
            repo_str: Repository in 'owner/repo' format

        Returns:
            Repository with owner and name populated

        Raises:
            ValueError: If format is invalid
        """
        if "/" not in repo_str:
            raise ValueError(f"Invalid repository format: {repo_str}. Expected 'owner/repo'")

        parts = repo_str.split("/", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(f"Invalid repository format: {repo_str}. Expected 'owner/repo'")

        return cls(
            owner=parts[0],
            name=parts[1],
            full_name=repo_str,
        )


@dataclass
class ReleaseAsset:
    """GitHub release asset."""

    id: int
    name: str
    label: str | None
    content_type: str
    size: int
    download_url: str
    browser_download_url: str
    state: str = "uploaded"
    download_count: int = 0

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ReleaseAsset:
        """Create from GitHub API response."""
        return cls(
            id=data["id"],
            name=data["name"],
            label=data.get("label"),
            content_type=data["content_type"],
            size=data["size"],
            download_url=data.get("url", ""),
            browser_download_url=data.get("browser_download_url", ""),
            state=data.get("state", "uploaded"),
            download_count=data.get("download_count", 0),
        )


@dataclass
class Release:
    """GitHub release."""

    id: int
    tag_name: str
    name: str | None
    body: str | None
    draft: bool
    prerelease: bool
    html_url: str
    upload_url: str
    tarball_url: str | None = None
    zipball_url: str | None = None
    created_at: datetime | None = None
    published_at: datetime | None = None
    assets: list[ReleaseAsset] = field(default_factory=lambda: [])
    target_commitish: str = "main"

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Release:
        """Create from GitHub API response."""
        assets = [ReleaseAsset.from_api(a) for a in data.get("assets", [])]

        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))

        published_at = None
        if data.get("published_at"):
            published_at = datetime.fromisoformat(data["published_at"].replace("Z", "+00:00"))

        return cls(
            id=data["id"],
            tag_name=data["tag_name"],
            name=data.get("name"),
            body=data.get("body"),
            draft=data.get("draft", False),
            prerelease=data.get("prerelease", False),
            html_url=data.get("html_url", ""),
            upload_url=data.get("upload_url", ""),
            tarball_url=data.get("tarball_url"),
            zipball_url=data.get("zipball_url"),
            created_at=created_at,
            published_at=published_at,
            assets=assets,
            target_commitish=data.get("target_commitish", "main"),
        )


@dataclass
class ReleaseResult:
    """Result of a release operation."""

    success: bool
    release: Release | None = None
    assets_uploaded: list[ReleaseAsset] = field(default_factory=lambda: [])
    assets_failed: list[tuple[Path, str]] = field(default_factory=lambda: [])
    errors: list[str] = field(default_factory=lambda: [])

    @classmethod
    def failure(cls, error: str) -> ReleaseResult:
        """Create a failure result."""
        return cls(success=False, errors=[error])

    def add_uploaded(self, asset: ReleaseAsset) -> None:
        """Add successfully uploaded asset."""
        self.assets_uploaded.append(asset)

    def add_failed(self, path: Path, error: str) -> None:
        """Add failed asset upload."""
        self.assets_failed.append((path, error))
        self.errors.append(f"Failed to upload {path.name}: {error}")


@dataclass
class WorkflowRun:
    """GitHub Actions workflow run."""

    id: int
    name: str
    workflow_id: int
    head_branch: str
    head_sha: str
    status: str  # queued, in_progress, completed
    conclusion: str | None  # success, failure, cancelled, skipped, etc.
    html_url: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> WorkflowRun:
        """Create from GitHub API response."""
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))

        updated_at = None
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))

        return cls(
            id=data["id"],
            name=data.get("name", ""),
            workflow_id=data.get("workflow_id", 0),
            head_branch=data.get("head_branch", ""),
            head_sha=data.get("head_sha", ""),
            status=data.get("status", ""),
            conclusion=data.get("conclusion"),
            html_url=data.get("html_url", ""),
            created_at=created_at,
            updated_at=updated_at,
        )


@dataclass
class PullRequest:
    """GitHub pull request."""

    number: int
    title: str
    body: str | None
    state: str  # open, closed
    draft: bool
    html_url: str
    head_ref: str
    base_ref: str
    merged: bool = False
    mergeable: bool | None = None
    labels: list[str] = field(default_factory=lambda: [])

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> PullRequest:
        """Create from GitHub API response."""
        labels = [label["name"] for label in data.get("labels", [])]
        return cls(
            number=data["number"],
            title=data["title"],
            body=data.get("body"),
            state=data["state"],
            draft=data.get("draft", False),
            html_url=data.get("html_url", ""),
            head_ref=data["head"]["ref"],
            base_ref=data["base"]["ref"],
            merged=data.get("merged", False),
            mergeable=data.get("mergeable"),
            labels=labels,
        )


@dataclass
class Issue:
    """GitHub issue."""

    number: int
    title: str
    body: str | None
    state: str  # open, closed
    html_url: str
    labels: list[str] = field(default_factory=lambda: [])
    assignees: list[str] = field(default_factory=lambda: [])

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Issue:
        """Create from GitHub API response."""
        labels = [label["name"] for label in data.get("labels", [])]
        assignees = [user["login"] for user in data.get("assignees", [])]
        return cls(
            number=data["number"],
            title=data["title"],
            body=data.get("body"),
            state=data["state"],
            html_url=data.get("html_url", ""),
            labels=labels,
            assignees=assignees,
        )
