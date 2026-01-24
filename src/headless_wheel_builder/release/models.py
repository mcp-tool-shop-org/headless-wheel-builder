"""Models for release management."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class ReleaseStatus(Enum):
    """Status of a release."""

    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ApprovalState(Enum):
    """State of an approval step."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SKIPPED = "skipped"


@dataclass
class ApprovalStep:
    """A single approval step in a workflow.

    Attributes:
        name: Step name
        approvers: List of approvers (usernames or emails)
        required_approvals: Number of approvals needed
        state: Current state
        approved_by: List of approvers who approved
        rejected_by: Who rejected (if any)
        comments: Approval comments
        approved_at: When approved
        rejected_at: When rejected
    """

    name: str
    approvers: list[str] = field(default_factory=lambda: [])
    required_approvals: int = 1
    state: ApprovalState = ApprovalState.PENDING
    approved_by: list[str] = field(default_factory=lambda: [])
    rejected_by: str = ""
    comments: dict[str, str] = field(default_factory=lambda: {})
    approved_at: str | None = None
    rejected_at: str | None = None

    @property
    def is_complete(self) -> bool:
        """Check if step is complete (approved or rejected)."""
        return self.state in (ApprovalState.APPROVED, ApprovalState.REJECTED, ApprovalState.SKIPPED)

    @property
    def approvals_remaining(self) -> int:
        """Number of approvals still needed."""
        return max(0, self.required_approvals - len(self.approved_by))

    def approve(self, approver: str, comment: str = "") -> bool:
        """Record an approval.

        Args:
            approver: Approver identifier
            comment: Optional comment

        Returns:
            True if step is now fully approved
        """
        if self.state != ApprovalState.PENDING:
            return False

        if approver not in self.approvers:
            return False

        if approver in self.approved_by:
            return False

        self.approved_by.append(approver)
        if comment:
            self.comments[approver] = comment

        if len(self.approved_by) >= self.required_approvals:
            self.state = ApprovalState.APPROVED
            self.approved_at = datetime.now(timezone.utc).isoformat()
            return True

        return False

    def reject(self, rejector: str, comment: str = "") -> None:
        """Record a rejection.

        Args:
            rejector: Rejector identifier
            comment: Optional comment
        """
        if self.state != ApprovalState.PENDING:
            return

        self.state = ApprovalState.REJECTED
        self.rejected_by = rejector
        self.rejected_at = datetime.now(timezone.utc).isoformat()
        if comment:
            self.comments[rejector] = comment

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "approvers": self.approvers,
            "required_approvals": self.required_approvals,
            "state": self.state.value,
            "approved_by": self.approved_by,
            "rejected_by": self.rejected_by,
            "comments": self.comments,
            "approved_at": self.approved_at,
            "rejected_at": self.rejected_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApprovalStep:
        """Create from dictionary."""
        return cls(
            name=data["name"],
            approvers=data.get("approvers", []),
            required_approvals=data.get("required_approvals", 1),
            state=ApprovalState(data.get("state", "pending")),
            approved_by=data.get("approved_by", []),
            rejected_by=data.get("rejected_by", ""),
            comments=data.get("comments", {}),
            approved_at=data.get("approved_at"),
            rejected_at=data.get("rejected_at"),
        )


@dataclass
class DraftRelease:
    """A draft release waiting for approval.

    Attributes:
        id: Unique release ID
        name: Release name
        version: Version being released
        package: Package name
        status: Current status
        created_at: Creation timestamp
        created_by: Creator
        wheel_paths: Paths to wheel files
        changelog: Release notes/changelog
        approval_steps: Workflow approval steps
        metadata: Additional metadata
        published_at: When published
        published_by: Who published
        error: Error message if failed
    """

    id: str
    name: str
    version: str
    package: str
    status: ReleaseStatus = ReleaseStatus.DRAFT
    created_at: str | None = None
    created_by: str = ""
    wheel_paths: list[str] = field(default_factory=lambda: [])
    changelog: str = ""
    approval_steps: list[ApprovalStep] = field(default_factory=lambda: [])
    metadata: dict[str, Any] = field(default_factory=lambda: {})
    published_at: str | None = None
    published_by: str = ""
    error: str = ""

    def __post_init__(self) -> None:
        """Set timestamps if not provided."""
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).isoformat()

    @property
    def current_step(self) -> ApprovalStep | None:
        """Get current pending approval step."""
        for step in self.approval_steps:
            if step.state == ApprovalState.PENDING:
                return step
        return None

    @property
    def is_approved(self) -> bool:
        """Check if all approval steps are complete."""
        if not self.approval_steps:
            return True
        return all(step.state == ApprovalState.APPROVED for step in self.approval_steps)

    @property
    def is_rejected(self) -> bool:
        """Check if any approval step is rejected."""
        return any(step.state == ApprovalState.REJECTED for step in self.approval_steps)

    def submit_for_approval(self) -> None:
        """Submit release for approval."""
        if self.status != ReleaseStatus.DRAFT:
            return
        self.status = ReleaseStatus.PENDING_APPROVAL

    def mark_approved(self) -> None:
        """Mark release as approved."""
        self.status = ReleaseStatus.APPROVED

    def mark_rejected(self) -> None:
        """Mark release as rejected."""
        self.status = ReleaseStatus.REJECTED

    def mark_published(self, publisher: str) -> None:
        """Mark release as published.

        Args:
            publisher: Who published
        """
        self.status = ReleaseStatus.PUBLISHED
        self.published_at = datetime.now(timezone.utc).isoformat()
        self.published_by = publisher

    def mark_failed(self, error: str) -> None:
        """Mark release as failed.

        Args:
            error: Error message
        """
        self.status = ReleaseStatus.FAILED
        self.error = error

    def rollback(self) -> None:
        """Mark release as rolled back."""
        self.status = ReleaseStatus.ROLLED_BACK

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "package": self.package,
            "status": self.status.value,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "wheel_paths": self.wheel_paths,
            "changelog": self.changelog,
            "approval_steps": [s.to_dict() for s in self.approval_steps],
            "metadata": self.metadata,
            "published_at": self.published_at,
            "published_by": self.published_by,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DraftRelease:
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            version=data["version"],
            package=data["package"],
            status=ReleaseStatus(data.get("status", "draft")),
            created_at=data.get("created_at"),
            created_by=data.get("created_by", ""),
            wheel_paths=data.get("wheel_paths", []),
            changelog=data.get("changelog", ""),
            approval_steps=[ApprovalStep.from_dict(s) for s in data.get("approval_steps", [])],
            metadata=data.get("metadata", {}),
            published_at=data.get("published_at"),
            published_by=data.get("published_by", ""),
            error=data.get("error", ""),
        )


@dataclass
class ReleaseConfig:
    """Configuration for release workflow.

    Attributes:
        require_approval: Whether approval is required
        approval_steps: Default approval steps
        auto_publish: Automatically publish on approval
        notify_on_create: Send notifications on draft creation
        notify_on_approve: Send notifications on approval
        notify_on_publish: Send notifications on publish
        storage_path: Path to store release data
    """

    require_approval: bool = True
    approval_steps: list[dict[str, Any]] = field(default_factory=lambda: [])
    auto_publish: bool = False
    notify_on_create: bool = True
    notify_on_approve: bool = True
    notify_on_publish: bool = True
    storage_path: Path = field(default_factory=lambda: Path.home() / ".hwb" / "releases")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReleaseConfig:
        """Create from dictionary."""
        storage = data.get("storage_path")
        return cls(
            require_approval=data.get("require_approval", True),
            approval_steps=data.get("approval_steps", []),
            auto_publish=data.get("auto_publish", False),
            notify_on_create=data.get("notify_on_create", True),
            notify_on_approve=data.get("notify_on_approve", True),
            notify_on_publish=data.get("notify_on_publish", True),
            storage_path=Path(storage) if storage else Path.home() / ".hwb" / "releases",
        )
