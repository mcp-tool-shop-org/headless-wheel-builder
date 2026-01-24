"""Release manager for draft releases."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from headless_wheel_builder.release.models import (
    ApprovalStep,
    DraftRelease,
    ReleaseConfig,
    ReleaseStatus,
)
from headless_wheel_builder.release.workflow import WORKFLOW_TEMPLATES, ApprovalWorkflow

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class ReleaseManager:
    """Manages draft releases and their lifecycle.

    Attributes:
        config: Release configuration
        workflow: Approval workflow manager
    """

    config: ReleaseConfig = field(default_factory=ReleaseConfig)
    workflow: ApprovalWorkflow = field(default_factory=ApprovalWorkflow)
    _releases: dict[str, DraftRelease] = field(default_factory=lambda: {})

    def __post_init__(self) -> None:
        """Initialize storage."""
        self.config.storage_path.mkdir(parents=True, exist_ok=True)
        self._load_releases()

    def _load_releases(self) -> None:
        """Load releases from storage."""
        index_path = self.config.storage_path / "index.json"
        if index_path.exists():
            try:
                content = index_path.read_text(encoding="utf-8")
                data = json.loads(content)
                for release_id, release_data in data.get("releases", {}).items():
                    self._releases[release_id] = DraftRelease.from_dict(release_data)
            except (json.JSONDecodeError, OSError):
                pass

    def _save_releases(self) -> None:
        """Save releases to storage."""
        index_path = self.config.storage_path / "index.json"
        data = {
            "version": 1,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "releases": {rid: release.to_dict() for rid, release in self._releases.items()},
        }
        content = json.dumps(data, indent=2)
        index_path.write_text(content, encoding="utf-8")

    def create_draft(
        self,
        name: str,
        version: str,
        package: str,
        wheel_paths: list[Path] | None = None,
        changelog: str = "",
        created_by: str = "",
        template: str | None = None,
        approval_steps: list[dict[str, Any]] | None = None,
    ) -> DraftRelease:
        """Create a new draft release.

        Args:
            name: Release name
            version: Version being released
            package: Package name
            wheel_paths: Paths to wheel files
            changelog: Release notes
            created_by: Creator identifier
            template: Workflow template name
            approval_steps: Custom approval steps

        Returns:
            Created draft release
        """
        release_id = str(uuid.uuid4())[:8]

        # Determine approval steps
        steps: list[ApprovalStep] = []
        if self.config.require_approval:
            if template:
                tmpl = WORKFLOW_TEMPLATES.get(template)
                if tmpl:
                    steps = tmpl.create_steps()
            elif approval_steps:
                steps = [
                    ApprovalStep(
                        name=s.get("name", f"Step {i + 1}"),
                        approvers=s.get("approvers", []),
                        required_approvals=s.get("required_approvals", 1),
                    )
                    for i, s in enumerate(approval_steps)
                ]
            elif self.config.approval_steps:
                steps = [
                    ApprovalStep(
                        name=s.get("name", f"Step {i + 1}"),
                        approvers=s.get("approvers", []),
                        required_approvals=s.get("required_approvals", 1),
                    )
                    for i, s in enumerate(self.config.approval_steps)
                ]
            else:
                # Default single approval step
                steps = [ApprovalStep(name="Release Approval")]

        release = DraftRelease(
            id=release_id,
            name=name,
            version=version,
            package=package,
            created_by=created_by,
            wheel_paths=[str(p) for p in (wheel_paths or [])],
            changelog=changelog,
            approval_steps=steps,
        )

        self._releases[release_id] = release
        self._save_releases()

        return release

    def get_release(self, release_id: str) -> DraftRelease | None:
        """Get a release by ID.

        Args:
            release_id: Release ID

        Returns:
            Release or None
        """
        return self._releases.get(release_id)

    def list_releases(
        self,
        status: ReleaseStatus | None = None,
        package: str | None = None,
        limit: int = 20,
    ) -> list[DraftRelease]:
        """List releases with optional filtering.

        Args:
            status: Filter by status
            package: Filter by package
            limit: Maximum results

        Returns:
            List of releases
        """
        releases = list(self._releases.values())

        if status:
            releases = [r for r in releases if r.status == status]

        if package:
            releases = [r for r in releases if r.package == package]

        # Sort by created_at (newest first)
        releases.sort(key=lambda r: r.created_at or "", reverse=True)

        return releases[:limit]

    def submit_for_approval(self, release_id: str) -> bool:
        """Submit a release for approval.

        Args:
            release_id: Release ID

        Returns:
            True if submitted
        """
        release = self._releases.get(release_id)
        if not release:
            return False

        if release.status != ReleaseStatus.DRAFT:
            return False

        release.submit_for_approval()
        self._save_releases()
        return True

    def approve(
        self,
        release_id: str,
        approver: str,
        step_name: str | None = None,
        comment: str = "",
    ) -> bool:
        """Approve a release step.

        Args:
            release_id: Release ID
            approver: Approver identifier
            step_name: Step name (or current step)
            comment: Approval comment

        Returns:
            True if approved
        """
        release = self._releases.get(release_id)
        if not release:
            return False

        result = self.workflow.approve_step(release, approver, step_name, comment)
        if result:
            self._save_releases()

            # Auto-publish if configured
            if self.config.auto_publish and release.is_approved:
                self._publish_release(release, approver)

        return result

    def reject(
        self,
        release_id: str,
        rejector: str,
        step_name: str | None = None,
        comment: str = "",
    ) -> bool:
        """Reject a release.

        Args:
            release_id: Release ID
            rejector: Rejector identifier
            step_name: Step name (or current step)
            comment: Rejection reason

        Returns:
            True if rejected
        """
        release = self._releases.get(release_id)
        if not release:
            return False

        result = self.workflow.reject_step(release, rejector, step_name, comment)
        if result:
            self._save_releases()
        return result

    def publish(self, release_id: str, publisher: str) -> bool:
        """Publish an approved release.

        Args:
            release_id: Release ID
            publisher: Publisher identifier

        Returns:
            True if published
        """
        release = self._releases.get(release_id)
        if not release:
            return False

        if not release.is_approved and self.config.require_approval:
            return False

        return self._publish_release(release, publisher)

    def _publish_release(self, release: DraftRelease, publisher: str) -> bool:
        """Internal publish logic.

        Args:
            release: Release to publish
            publisher: Publisher identifier

        Returns:
            True if published
        """
        try:
            # Mark as published
            release.mark_published(publisher)
            self._save_releases()
            return True
        except Exception as e:
            release.mark_failed(str(e))
            self._save_releases()
            return False

    def rollback(self, release_id: str) -> bool:
        """Rollback a published release.

        Args:
            release_id: Release ID

        Returns:
            True if rolled back
        """
        release = self._releases.get(release_id)
        if not release:
            return False

        if release.status != ReleaseStatus.PUBLISHED:
            return False

        release.rollback()
        self._save_releases()
        return True

    def delete(self, release_id: str) -> bool:
        """Delete a draft release.

        Args:
            release_id: Release ID

        Returns:
            True if deleted
        """
        release = self._releases.get(release_id)
        if not release:
            return False

        # Only allow deleting drafts and rejected releases
        if release.status not in (ReleaseStatus.DRAFT, ReleaseStatus.REJECTED):
            return False

        del self._releases[release_id]
        self._save_releases()
        return True

    def update_changelog(self, release_id: str, changelog: str) -> bool:
        """Update release changelog.

        Args:
            release_id: Release ID
            changelog: New changelog

        Returns:
            True if updated
        """
        release = self._releases.get(release_id)
        if not release:
            return False

        if release.status not in (ReleaseStatus.DRAFT, ReleaseStatus.REJECTED):
            return False

        release.changelog = changelog
        self._save_releases()
        return True

    def get_pending_approvals(self, approver: str) -> list[DraftRelease]:
        """Get releases pending approval by a specific approver.

        Args:
            approver: Approver identifier

        Returns:
            List of releases needing approval
        """
        pending: list[DraftRelease] = []

        for release in self._releases.values():
            if release.status != ReleaseStatus.PENDING_APPROVAL:
                continue

            current_step = release.current_step
            if not current_step:
                continue

            # Check if this approver can approve
            if approver in current_step.approvers and approver not in current_step.approved_by:
                pending.append(release)

        return pending

    def get_statistics(self) -> dict[str, Any]:
        """Get release statistics.

        Returns:
            Statistics dictionary
        """
        releases = list(self._releases.values())

        by_status: dict[str, int] = {}
        for release in releases:
            status = release.status.value
            by_status[status] = by_status.get(status, 0) + 1

        by_package: dict[str, int] = {}
        for release in releases:
            pkg = release.package
            by_package[pkg] = by_package.get(pkg, 0) + 1

        return {
            "total": len(releases),
            "by_status": by_status,
            "by_package": by_package,
            "pending_approval": sum(
                1 for r in releases if r.status == ReleaseStatus.PENDING_APPROVAL
            ),
        }
