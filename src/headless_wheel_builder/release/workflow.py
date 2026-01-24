"""Approval workflow management."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from headless_wheel_builder.release.models import (
    ApprovalState,
    ApprovalStep,
    DraftRelease,
    ReleaseStatus,
)


@dataclass
class WorkflowTemplate:
    """Template for approval workflows.

    Attributes:
        name: Template name
        description: Template description
        steps: List of step configurations
    """

    name: str
    description: str = ""
    steps: list[dict[str, Any]] = field(default_factory=lambda: [])

    def create_steps(self) -> list[ApprovalStep]:
        """Create approval steps from template.

        Returns:
            List of ApprovalStep instances
        """
        return [
            ApprovalStep(
                name=step.get("name", f"Step {i + 1}"),
                approvers=step.get("approvers", []),
                required_approvals=step.get("required_approvals", 1),
            )
            for i, step in enumerate(self.steps)
        ]


# Common workflow templates
WORKFLOW_TEMPLATES: dict[str, WorkflowTemplate] = {
    "simple": WorkflowTemplate(
        name="Simple",
        description="Single approval required",
        steps=[
            {"name": "Review", "required_approvals": 1},
        ],
    ),
    "two-stage": WorkflowTemplate(
        name="Two-Stage",
        description="Review then approval",
        steps=[
            {"name": "Code Review", "required_approvals": 1},
            {"name": "Release Approval", "required_approvals": 1},
        ],
    ),
    "enterprise": WorkflowTemplate(
        name="Enterprise",
        description="QA, Security, and Release approval",
        steps=[
            {"name": "QA Review", "required_approvals": 1},
            {"name": "Security Review", "required_approvals": 1},
            {"name": "Release Approval", "required_approvals": 2},
        ],
    ),
}


ApprovalCallback = Callable[[DraftRelease, ApprovalStep], None]


class ApprovalWorkflow:
    """Manages approval workflow for releases.

    Handles the multi-stage approval process with callbacks
    for workflow events.
    """

    def __init__(
        self,
        on_step_approved: ApprovalCallback | None = None,
        on_step_rejected: ApprovalCallback | None = None,
        on_release_approved: Callable[[DraftRelease], None] | None = None,
        on_release_rejected: Callable[[DraftRelease], None] | None = None,
    ) -> None:
        """Initialize workflow.

        Args:
            on_step_approved: Callback when step is approved
            on_step_rejected: Callback when step is rejected
            on_release_approved: Callback when release is fully approved
            on_release_rejected: Callback when release is rejected
        """
        self.on_step_approved = on_step_approved
        self.on_step_rejected = on_step_rejected
        self.on_release_approved = on_release_approved
        self.on_release_rejected = on_release_rejected

    def approve_step(
        self,
        release: DraftRelease,
        approver: str,
        step_name: str | None = None,
        comment: str = "",
    ) -> bool:
        """Approve a step in the workflow.

        Args:
            release: Release to approve
            approver: Approver identifier
            step_name: Specific step name (or current step if None)
            comment: Optional approval comment

        Returns:
            True if approval was recorded
        """
        # Find the step
        step: ApprovalStep | None = None
        if step_name:
            for s in release.approval_steps:
                if s.name == step_name:
                    step = s
                    break
        else:
            step = release.current_step

        if not step:
            return False

        # Record approval
        fully_approved = step.approve(approver, comment)

        # Trigger callback if step is now approved
        if fully_approved and self.on_step_approved:
            self.on_step_approved(release, step)

        # Check if release is fully approved
        if release.is_approved:
            release.mark_approved()
            if self.on_release_approved:
                self.on_release_approved(release)

        return True

    def reject_step(
        self,
        release: DraftRelease,
        rejector: str,
        step_name: str | None = None,
        comment: str = "",
    ) -> bool:
        """Reject a step in the workflow.

        Args:
            release: Release to reject
            rejector: Rejector identifier
            step_name: Specific step name (or current step if None)
            comment: Optional rejection reason

        Returns:
            True if rejection was recorded
        """
        # Find the step
        step: ApprovalStep | None = None
        if step_name:
            for s in release.approval_steps:
                if s.name == step_name:
                    step = s
                    break
        else:
            step = release.current_step

        if not step:
            return False

        # Record rejection
        step.reject(rejector, comment)

        # Trigger callbacks
        if self.on_step_rejected:
            self.on_step_rejected(release, step)

        release.mark_rejected()
        if self.on_release_rejected:
            self.on_release_rejected(release)

        return True

    def skip_step(
        self,
        release: DraftRelease,
        step_name: str,
        reason: str = "",
    ) -> bool:
        """Skip an approval step.

        Args:
            release: Release
            step_name: Step to skip
            reason: Reason for skipping

        Returns:
            True if step was skipped
        """
        for step in release.approval_steps:
            if step.name == step_name and step.state == ApprovalState.PENDING:
                step.state = ApprovalState.SKIPPED
                if reason:
                    step.comments["skip_reason"] = reason
                return True
        return False

    def reset_workflow(self, release: DraftRelease) -> None:
        """Reset workflow to draft state.

        Args:
            release: Release to reset
        """
        release.status = ReleaseStatus.DRAFT
        for step in release.approval_steps:
            step.state = ApprovalState.PENDING
            step.approved_by = []
            step.rejected_by = ""
            step.comments = {}
            step.approved_at = None
            step.rejected_at = None

    def get_workflow_status(self, release: DraftRelease) -> dict[str, Any]:
        """Get detailed workflow status.

        Args:
            release: Release to check

        Returns:
            Status dictionary
        """
        completed_steps = sum(1 for s in release.approval_steps if s.is_complete)
        total_steps = len(release.approval_steps)

        return {
            "release_id": release.id,
            "status": release.status.value,
            "current_step": release.current_step.name if release.current_step else None,
            "completed_steps": completed_steps,
            "total_steps": total_steps,
            "progress_percent": (completed_steps / total_steps * 100) if total_steps else 100,
            "is_approved": release.is_approved,
            "is_rejected": release.is_rejected,
            "steps": [
                {
                    "name": step.name,
                    "state": step.state.value,
                    "approved_by": step.approved_by,
                    "rejected_by": step.rejected_by,
                    "approvals_remaining": step.approvals_remaining,
                }
                for step in release.approval_steps
            ],
        }

    @classmethod
    def create_from_template(
        cls,
        template_name: str,
        approvers: dict[str, list[str]] | None = None,
    ) -> tuple[ApprovalWorkflow, list[ApprovalStep]]:
        """Create workflow and steps from template.

        Args:
            template_name: Name of template to use
            approvers: Map of step name -> approvers

        Returns:
            Tuple of (workflow, steps)
        """
        template = WORKFLOW_TEMPLATES.get(template_name)
        if not template:
            raise ValueError(f"Unknown template: {template_name}")

        steps = template.create_steps()

        # Assign approvers if provided
        if approvers:
            for step in steps:
                if step.name in approvers:
                    step.approvers = approvers[step.name]

        return cls(), steps
