"""Tests for release management module."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from headless_wheel_builder.release.cli import release
from headless_wheel_builder.release.manager import ReleaseManager
from headless_wheel_builder.release.models import (
    ApprovalState,
    ApprovalStep,
    DraftRelease,
    ReleaseConfig,
    ReleaseStatus,
)
from headless_wheel_builder.release.workflow import (
    WORKFLOW_TEMPLATES,
    ApprovalWorkflow,
    WorkflowTemplate,
)

if TYPE_CHECKING:
    from pathlib import Path

# =============================================================================
# Model Tests
# =============================================================================


class TestApprovalState:
    """Tests for ApprovalState enum."""

    def test_enum_values(self) -> None:
        """Test all enum values exist."""
        assert ApprovalState.PENDING.value == "pending"
        assert ApprovalState.APPROVED.value == "approved"
        assert ApprovalState.REJECTED.value == "rejected"
        assert ApprovalState.SKIPPED.value == "skipped"


class TestReleaseStatus:
    """Tests for ReleaseStatus enum."""

    def test_enum_values(self) -> None:
        """Test all enum values exist."""
        assert ReleaseStatus.DRAFT.value == "draft"
        assert ReleaseStatus.PENDING_APPROVAL.value == "pending_approval"
        assert ReleaseStatus.APPROVED.value == "approved"
        assert ReleaseStatus.REJECTED.value == "rejected"
        assert ReleaseStatus.PUBLISHED.value == "published"
        assert ReleaseStatus.FAILED.value == "failed"
        assert ReleaseStatus.ROLLED_BACK.value == "rolled_back"


class TestApprovalStep:
    """Tests for ApprovalStep model."""

    def test_create_step(self) -> None:
        """Test creating an approval step."""
        step = ApprovalStep(name="review", required_approvals=2)
        assert step.name == "review"
        assert step.required_approvals == 2
        assert step.state == ApprovalState.PENDING
        assert step.approved_by == []
        assert step.rejected_by == ""  # Default is empty string

    def test_is_complete_pending(self) -> None:
        """Test is_complete for pending step."""
        step = ApprovalStep(name="review")
        assert not step.is_complete

    def test_is_complete_approved(self) -> None:
        """Test is_complete for approved step."""
        step = ApprovalStep(name="review", state=ApprovalState.APPROVED)
        assert step.is_complete

    def test_is_complete_rejected(self) -> None:
        """Test is_complete for rejected step."""
        step = ApprovalStep(name="review", state=ApprovalState.REJECTED)
        assert step.is_complete

    def test_is_complete_skipped(self) -> None:
        """Test is_complete for skipped step."""
        step = ApprovalStep(name="review", state=ApprovalState.SKIPPED)
        assert step.is_complete

    def test_approvals_remaining(self) -> None:
        """Test approvals_remaining property."""
        step = ApprovalStep(name="review", required_approvals=2)
        assert step.approvals_remaining == 2

        step.approved_by.append("alice")
        assert step.approvals_remaining == 1

    def test_approve_success(self) -> None:
        """Test approving a step."""
        step = ApprovalStep(name="review", approvers=["alice", "bob"])
        result = step.approve("alice", "Looks good")

        assert result is True
        assert "alice" in step.approved_by
        assert step.state == ApprovalState.APPROVED

    def test_approve_multiple_required(self) -> None:
        """Test approving with multiple required."""
        step = ApprovalStep(
            name="review",
            approvers=["alice", "bob"],
            required_approvals=2,
        )

        result1 = step.approve("alice")
        assert result1 is False  # Not yet complete
        assert step.state == ApprovalState.PENDING

        result2 = step.approve("bob")
        assert result2 is True
        assert step.state == ApprovalState.APPROVED

    def test_approve_not_in_approvers(self) -> None:
        """Test approval by non-approver fails."""
        step = ApprovalStep(name="review", approvers=["alice"])
        result = step.approve("bob")

        assert result is False
        assert "bob" not in step.approved_by

    def test_approve_already_approved(self) -> None:
        """Test duplicate approval fails."""
        step = ApprovalStep(
            name="review",
            approvers=["alice", "bob"],
            required_approvals=2,
        )
        step.approve("alice")
        result = step.approve("alice")  # Try again

        assert result is False
        assert step.approved_by.count("alice") == 1

    def test_reject(self) -> None:
        """Test rejecting a step."""
        step = ApprovalStep(name="review")
        step.reject("alice", "Not ready")

        assert step.state == ApprovalState.REJECTED
        assert step.rejected_by == "alice"
        assert step.rejected_at is not None

    def test_to_dict(self) -> None:
        """Test converting step to dict."""
        step = ApprovalStep(
            name="review",
            required_approvals=2,
            approvers=["alice", "bob"],
        )
        data = step.to_dict()
        assert data["name"] == "review"
        assert data["required_approvals"] == 2
        assert data["approvers"] == ["alice", "bob"]

    def test_from_dict(self) -> None:
        """Test creating step from dict."""
        data = {
            "name": "review",
            "required_approvals": 2,
            "state": "approved",
            "approved_by": ["alice"],
        }
        step = ApprovalStep.from_dict(data)
        assert step.name == "review"
        assert step.required_approvals == 2
        assert step.state == ApprovalState.APPROVED
        assert step.approved_by == ["alice"]


class TestDraftRelease:
    """Tests for DraftRelease model."""

    def test_create_release(self) -> None:
        """Test creating a draft release."""
        rel = DraftRelease(
            id="rel-123",
            name="Test Release",
            version="1.0.0",
            package="my-package",
        )
        assert rel.name == "Test Release"
        assert rel.version == "1.0.0"
        assert rel.package == "my-package"
        assert rel.status == ReleaseStatus.DRAFT
        assert rel.id == "rel-123"
        assert rel.created_at is not None

    def test_current_step_no_steps(self) -> None:
        """Test current_step with no approval steps."""
        rel = DraftRelease(id="r1", name="Test", version="1.0.0", package="pkg")
        assert rel.current_step is None

    def test_current_step_with_steps(self) -> None:
        """Test current_step returns first pending step."""
        steps = [
            ApprovalStep(name="step1", state=ApprovalState.APPROVED),
            ApprovalStep(name="step2", state=ApprovalState.PENDING),
            ApprovalStep(name="step3", state=ApprovalState.PENDING),
        ]
        rel = DraftRelease(
            id="r1",
            name="Test",
            version="1.0.0",
            package="pkg",
            approval_steps=steps,
        )
        assert rel.current_step is not None
        assert rel.current_step.name == "step2"

    def test_is_approved_no_steps(self) -> None:
        """Test is_approved with no steps."""
        rel = DraftRelease(id="r1", name="Test", version="1.0.0", package="pkg")
        assert rel.is_approved

    def test_is_approved_all_complete(self) -> None:
        """Test is_approved when all steps complete."""
        steps = [
            ApprovalStep(name="step1", state=ApprovalState.APPROVED),
            ApprovalStep(name="step2", state=ApprovalState.APPROVED),
        ]
        rel = DraftRelease(
            id="r1",
            name="Test",
            version="1.0.0",
            package="pkg",
            approval_steps=steps,
        )
        assert rel.is_approved

    def test_is_approved_pending_steps(self) -> None:
        """Test is_approved with pending steps."""
        steps = [
            ApprovalStep(name="step1", state=ApprovalState.APPROVED),
            ApprovalStep(name="step2", state=ApprovalState.PENDING),
        ]
        rel = DraftRelease(
            id="r1",
            name="Test",
            version="1.0.0",
            package="pkg",
            approval_steps=steps,
        )
        assert not rel.is_approved

    def test_is_rejected(self) -> None:
        """Test is_rejected property."""
        steps = [
            ApprovalStep(name="step1", state=ApprovalState.REJECTED),
        ]
        rel = DraftRelease(
            id="r1",
            name="Test",
            version="1.0.0",
            package="pkg",
            approval_steps=steps,
        )
        assert rel.is_rejected

    def test_submit_for_approval(self) -> None:
        """Test submitting for approval."""
        rel = DraftRelease(id="r1", name="Test", version="1.0.0", package="pkg")
        rel.submit_for_approval()
        assert rel.status == ReleaseStatus.PENDING_APPROVAL

    def test_mark_published(self) -> None:
        """Test marking as published."""
        rel = DraftRelease(id="r1", name="Test", version="1.0.0", package="pkg")
        rel.mark_published("publisher")

        assert rel.status == ReleaseStatus.PUBLISHED
        assert rel.published_by == "publisher"
        assert rel.published_at is not None

    def test_rollback(self) -> None:
        """Test rollback."""
        rel = DraftRelease(id="r1", name="Test", version="1.0.0", package="pkg")
        rel.mark_published("publisher")
        rel.rollback()
        assert rel.status == ReleaseStatus.ROLLED_BACK

    def test_to_dict(self) -> None:
        """Test converting release to dict."""
        rel = DraftRelease(
            id="rel-123",
            name="Test Release",
            version="1.0.0",
            package="my-package",
            changelog="Changes here",
        )
        data = rel.to_dict()
        assert data["name"] == "Test Release"
        assert data["version"] == "1.0.0"
        assert data["package"] == "my-package"
        assert data["changelog"] == "Changes here"
        assert data["id"] == "rel-123"

    def test_from_dict(self) -> None:
        """Test creating release from dict."""
        data = {
            "id": "rel-123",
            "name": "Test Release",
            "version": "1.0.0",
            "package": "my-package",
            "status": "pending_approval",
            "approval_steps": [{"name": "review", "state": "pending"}],
        }
        rel = DraftRelease.from_dict(data)
        assert rel.id == "rel-123"
        assert rel.name == "Test Release"
        assert rel.status == ReleaseStatus.PENDING_APPROVAL
        assert len(rel.approval_steps) == 1


class TestReleaseConfig:
    """Tests for ReleaseConfig model."""

    def test_default_config(self) -> None:
        """Test default configuration."""
        config = ReleaseConfig()
        assert config.require_approval is True
        assert config.auto_publish is False

    def test_custom_config(self) -> None:
        """Test custom configuration."""
        config = ReleaseConfig(
            require_approval=False,
            auto_publish=True,
        )
        assert config.require_approval is False
        assert config.auto_publish is True


# =============================================================================
# Workflow Tests
# =============================================================================


class TestWorkflowTemplate:
    """Tests for WorkflowTemplate."""

    def test_create_template(self) -> None:
        """Test creating a workflow template."""
        template = WorkflowTemplate(
            name="custom",
            description="Custom workflow",
            steps=[
                {"name": "review", "required_approvals": 1},
            ],
        )
        assert template.name == "custom"
        assert template.description == "Custom workflow"
        assert len(template.steps) == 1

    def test_create_steps(self) -> None:
        """Test creating steps from template."""
        template = WorkflowTemplate(
            name="custom",
            steps=[
                {"name": "review", "required_approvals": 2},
            ],
        )
        steps = template.create_steps()
        assert len(steps) == 1
        assert steps[0].name == "review"
        assert steps[0].required_approvals == 2

    def test_builtin_templates_exist(self) -> None:
        """Test that built-in templates exist."""
        assert "simple" in WORKFLOW_TEMPLATES
        assert "two-stage" in WORKFLOW_TEMPLATES
        assert "enterprise" in WORKFLOW_TEMPLATES


class TestApprovalWorkflow:
    """Tests for ApprovalWorkflow."""

    def test_create_workflow(self) -> None:
        """Test creating a workflow."""
        workflow = ApprovalWorkflow()
        assert workflow is not None

    def test_create_from_template(self) -> None:
        """Test creating workflow from template."""
        workflow, steps = ApprovalWorkflow.create_from_template("simple")
        assert len(steps) >= 1
        assert workflow is not None

    def test_create_from_invalid_template(self) -> None:
        """Test creating workflow from invalid template."""
        with pytest.raises(ValueError, match="Unknown template"):
            ApprovalWorkflow.create_from_template("nonexistent")

    def test_approve_step(self) -> None:
        """Test approving a step."""
        workflow = ApprovalWorkflow()
        release = DraftRelease(
            id="r1",
            name="Test",
            version="1.0.0",
            package="pkg",
            approval_steps=[
                ApprovalStep(name="review", approvers=["alice"]),
            ],
        )

        result = workflow.approve_step(release, "alice")
        assert result is True
        assert release.approval_steps[0].state == ApprovalState.APPROVED

    def test_reject_step(self) -> None:
        """Test rejecting a step."""
        workflow = ApprovalWorkflow()
        release = DraftRelease(
            id="r1",
            name="Test",
            version="1.0.0",
            package="pkg",
            approval_steps=[
                ApprovalStep(name="review"),
            ],
        )

        result = workflow.reject_step(release, "alice", comment="Not ready")
        assert result is True
        assert release.approval_steps[0].state == ApprovalState.REJECTED
        assert release.status == ReleaseStatus.REJECTED

    def test_skip_step(self) -> None:
        """Test skipping a step."""
        workflow = ApprovalWorkflow()
        release = DraftRelease(
            id="r1",
            name="Test",
            version="1.0.0",
            package="pkg",
            approval_steps=[
                ApprovalStep(name="review"),
            ],
        )

        result = workflow.skip_step(release, "review", "Not needed")
        assert result is True
        assert release.approval_steps[0].state == ApprovalState.SKIPPED

    def test_reset_workflow(self) -> None:
        """Test resetting workflow."""
        workflow = ApprovalWorkflow()
        release = DraftRelease(
            id="r1",
            name="Test",
            version="1.0.0",
            package="pkg",
            status=ReleaseStatus.REJECTED,
            approval_steps=[
                ApprovalStep(name="review", state=ApprovalState.REJECTED),
            ],
        )

        workflow.reset_workflow(release)
        assert release.status == ReleaseStatus.DRAFT
        assert release.approval_steps[0].state == ApprovalState.PENDING

    def test_get_workflow_status(self) -> None:
        """Test getting workflow status."""
        workflow = ApprovalWorkflow()
        release = DraftRelease(
            id="r1",
            name="Test",
            version="1.0.0",
            package="pkg",
            approval_steps=[
                ApprovalStep(name="step1", state=ApprovalState.APPROVED),
                ApprovalStep(name="step2", state=ApprovalState.PENDING),
            ],
        )

        status = workflow.get_workflow_status(release)
        assert status["completed_steps"] == 1
        assert status["total_steps"] == 2
        assert status["current_step"] == "step2"


# =============================================================================
# Manager Tests
# =============================================================================


class TestReleaseManager:
    """Tests for ReleaseManager."""

    def test_create_manager(self, tmp_path: Path) -> None:
        """Test creating a manager."""
        config = ReleaseConfig(storage_path=tmp_path)
        manager = ReleaseManager(config=config)
        assert manager.config.storage_path == tmp_path

    def test_create_draft(self, tmp_path: Path) -> None:
        """Test creating a draft release."""
        config = ReleaseConfig(storage_path=tmp_path)
        manager = ReleaseManager(config=config)

        draft = manager.create_draft(
            name="Test Release",
            version="1.0.0",
            package="my-package",
            changelog="Changes here",
        )

        assert draft.name == "Test Release"
        assert draft.version == "1.0.0"
        assert draft.status == ReleaseStatus.DRAFT

    def test_create_draft_with_template(self, tmp_path: Path) -> None:
        """Test creating a draft with workflow template."""
        config = ReleaseConfig(storage_path=tmp_path)
        manager = ReleaseManager(config=config)

        draft = manager.create_draft(
            name="Test Release",
            version="1.0.0",
            package="my-package",
            template="two-stage",
        )

        assert len(draft.approval_steps) >= 2

    def test_get_release(self, tmp_path: Path) -> None:
        """Test getting a release by ID."""
        config = ReleaseConfig(storage_path=tmp_path)
        manager = ReleaseManager(config=config)

        draft = manager.create_draft(
            name="Test",
            version="1.0.0",
            package="pkg",
        )

        retrieved = manager.get_release(draft.id)
        assert retrieved is not None
        assert retrieved.id == draft.id

    def test_get_nonexistent_release(self, tmp_path: Path) -> None:
        """Test getting a nonexistent release."""
        config = ReleaseConfig(storage_path=tmp_path)
        manager = ReleaseManager(config=config)
        assert manager.get_release("nonexistent") is None

    def test_list_releases(self, tmp_path: Path) -> None:
        """Test listing releases."""
        config = ReleaseConfig(storage_path=tmp_path)
        manager = ReleaseManager(config=config)

        manager.create_draft(name="R1", version="1.0.0", package="pkg1")
        manager.create_draft(name="R2", version="2.0.0", package="pkg2")

        releases = manager.list_releases()
        assert len(releases) == 2

    def test_list_releases_by_status(self, tmp_path: Path) -> None:
        """Test listing releases filtered by status."""
        config = ReleaseConfig(storage_path=tmp_path)
        manager = ReleaseManager(config=config)

        d1 = manager.create_draft(name="R1", version="1.0.0", package="pkg1")
        manager.create_draft(name="R2", version="2.0.0", package="pkg2")
        manager.submit_for_approval(d1.id)

        drafts = manager.list_releases(status=ReleaseStatus.DRAFT)
        pending = manager.list_releases(status=ReleaseStatus.PENDING_APPROVAL)

        assert len(drafts) == 1
        assert len(pending) == 1

    def test_list_releases_by_package(self, tmp_path: Path) -> None:
        """Test listing releases filtered by package."""
        config = ReleaseConfig(storage_path=tmp_path)
        manager = ReleaseManager(config=config)

        manager.create_draft(name="R1", version="1.0.0", package="pkg1")
        manager.create_draft(name="R2", version="2.0.0", package="pkg2")
        manager.create_draft(name="R3", version="3.0.0", package="pkg1")

        pkg1_releases = manager.list_releases(package="pkg1")
        assert len(pkg1_releases) == 2

    def test_submit_for_approval(self, tmp_path: Path) -> None:
        """Test submitting for approval."""
        config = ReleaseConfig(storage_path=tmp_path)
        manager = ReleaseManager(config=config)

        draft = manager.create_draft(name="Test", version="1.0.0", package="pkg")
        result = manager.submit_for_approval(draft.id)

        assert result is True
        updated = manager.get_release(draft.id)
        assert updated is not None
        assert updated.status == ReleaseStatus.PENDING_APPROVAL

    def test_submit_nonexistent_release(self, tmp_path: Path) -> None:
        """Test submitting nonexistent release."""
        config = ReleaseConfig(storage_path=tmp_path)
        manager = ReleaseManager(config=config)
        result = manager.submit_for_approval("nonexistent")
        assert result is False

    def test_approve_release(self, tmp_path: Path) -> None:
        """Test approving a release."""
        config = ReleaseConfig(storage_path=tmp_path)
        manager = ReleaseManager(config=config)

        draft = manager.create_draft(
            name="Test",
            version="1.0.0",
            package="pkg",
            template="simple",
        )
        manager.submit_for_approval(draft.id)

        # Need to add approver to the step
        release = manager.get_release(draft.id)
        assert release is not None
        if release.current_step:
            release.current_step.approvers.append("alice")
            manager._save_releases()

        result = manager.approve(draft.id, "alice")
        assert result is True

    def test_reject_release(self, tmp_path: Path) -> None:
        """Test rejecting a release."""
        config = ReleaseConfig(storage_path=tmp_path)
        manager = ReleaseManager(config=config)

        draft = manager.create_draft(
            name="Test",
            version="1.0.0",
            package="pkg",
            template="simple",
        )
        manager.submit_for_approval(draft.id)

        result = manager.reject(draft.id, "alice", comment="Not ready")
        assert result is True

        updated = manager.get_release(draft.id)
        assert updated is not None
        assert updated.status == ReleaseStatus.REJECTED

    def test_publish_approved_release(self, tmp_path: Path) -> None:
        """Test publishing an approved release."""
        config = ReleaseConfig(storage_path=tmp_path, require_approval=False)
        manager = ReleaseManager(config=config)

        draft = manager.create_draft(
            name="Test",
            version="1.0.0",
            package="pkg",
        )

        result = manager.publish(draft.id, "publisher")
        assert result is True

        updated = manager.get_release(draft.id)
        assert updated is not None
        assert updated.status == ReleaseStatus.PUBLISHED

    def test_publish_unapproved_release(self, tmp_path: Path) -> None:
        """Test publishing an unapproved release fails."""
        config = ReleaseConfig(storage_path=tmp_path, require_approval=True)
        manager = ReleaseManager(config=config)

        draft = manager.create_draft(
            name="Test",
            version="1.0.0",
            package="pkg",
            template="simple",
        )
        manager.submit_for_approval(draft.id)

        result = manager.publish(draft.id, "publisher")
        assert result is False

    def test_rollback_release(self, tmp_path: Path) -> None:
        """Test rolling back a release."""
        config = ReleaseConfig(storage_path=tmp_path, require_approval=False)
        manager = ReleaseManager(config=config)

        draft = manager.create_draft(
            name="Test",
            version="1.0.0",
            package="pkg",
        )
        manager.publish(draft.id, "publisher")

        result = manager.rollback(draft.id)
        assert result is True

        updated = manager.get_release(draft.id)
        assert updated is not None
        assert updated.status == ReleaseStatus.ROLLED_BACK

    def test_delete_draft(self, tmp_path: Path) -> None:
        """Test deleting a draft release."""
        config = ReleaseConfig(storage_path=tmp_path)
        manager = ReleaseManager(config=config)

        draft = manager.create_draft(name="Test", version="1.0.0", package="pkg")
        result = manager.delete(draft.id)

        assert result is True
        assert manager.get_release(draft.id) is None

    def test_delete_published_release(self, tmp_path: Path) -> None:
        """Test deleting a published release fails."""
        config = ReleaseConfig(storage_path=tmp_path, require_approval=False)
        manager = ReleaseManager(config=config)

        draft = manager.create_draft(name="Test", version="1.0.0", package="pkg")
        manager.publish(draft.id, "publisher")

        result = manager.delete(draft.id)
        assert result is False

    def test_get_pending_approvals(self, tmp_path: Path) -> None:
        """Test getting pending approvals for an approver."""
        config = ReleaseConfig(storage_path=tmp_path)
        manager = ReleaseManager(config=config)

        draft = manager.create_draft(
            name="Test",
            version="1.0.0",
            package="pkg",
            approval_steps=[{"name": "review", "approvers": ["alice"]}],
        )
        manager.submit_for_approval(draft.id)

        pending = manager.get_pending_approvals("alice")
        assert len(pending) == 1
        assert pending[0].id == draft.id

    def test_get_statistics(self, tmp_path: Path) -> None:
        """Test getting release statistics."""
        config = ReleaseConfig(storage_path=tmp_path)
        manager = ReleaseManager(config=config)

        manager.create_draft(name="R1", version="1.0.0", package="pkg1")
        d2 = manager.create_draft(name="R2", version="2.0.0", package="pkg2")
        manager.submit_for_approval(d2.id)

        stats = manager.get_statistics()
        assert stats["total"] == 2
        assert stats["pending_approval"] == 1
        assert "by_status" in stats
        assert "by_package" in stats

    def test_update_changelog(self, tmp_path: Path) -> None:
        """Test updating changelog."""
        config = ReleaseConfig(storage_path=tmp_path)
        manager = ReleaseManager(config=config)

        draft = manager.create_draft(name="Test", version="1.0.0", package="pkg")
        result = manager.update_changelog(draft.id, "New changelog")

        assert result is True
        updated = manager.get_release(draft.id)
        assert updated is not None
        assert updated.changelog == "New changelog"

    def test_persistence(self, tmp_path: Path) -> None:
        """Test that releases persist across manager instances."""
        config = ReleaseConfig(storage_path=tmp_path)
        manager1 = ReleaseManager(config=config)
        draft = manager1.create_draft(name="Test", version="1.0.0", package="pkg")

        # Create new manager instance
        manager2 = ReleaseManager(config=config)
        retrieved = manager2.get_release(draft.id)

        assert retrieved is not None
        assert retrieved.id == draft.id
        assert retrieved.name == "Test"


# =============================================================================
# CLI Tests
# =============================================================================


class TestReleaseCLI:
    """Tests for release CLI commands."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI runner."""
        return CliRunner()

    def test_create_release(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test creating a release via CLI."""
        with patch("headless_wheel_builder.release.cli.get_manager") as mock:
            mock_manager = MagicMock()
            mock_draft = DraftRelease(
                id="rel-123",
                name="Test Release",
                version="1.0.0",
                package="my-package",
            )
            mock_manager.create_draft.return_value = mock_draft
            mock.return_value = mock_manager

            result = runner.invoke(
                release,
                [
                    "create",
                    "-n",
                    "Test Release",
                    "-v",
                    "1.0.0",
                    "-p",
                    "my-package",
                ],
            )

            assert result.exit_code == 0
            assert "rel-123" in result.output

    def test_create_release_json(self, runner: CliRunner) -> None:
        """Test creating a release with JSON output."""
        with patch("headless_wheel_builder.release.cli.get_manager") as mock:
            mock_manager = MagicMock()
            mock_draft = DraftRelease(
                id="rel-123",
                name="Test",
                version="1.0.0",
                package="pkg",
            )
            mock_manager.create_draft.return_value = mock_draft
            mock.return_value = mock_manager

            result = runner.invoke(
                release,
                [
                    "create",
                    "-n",
                    "Test",
                    "-v",
                    "1.0.0",
                    "-p",
                    "pkg",
                    "--json",
                ],
            )

            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["id"] == "rel-123"

    def test_list_releases(self, runner: CliRunner) -> None:
        """Test listing releases."""
        with patch("headless_wheel_builder.release.cli.get_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.list_releases.return_value = [
                DraftRelease(id="r1", name="R1", version="1.0", package="p1"),
                DraftRelease(id="r2", name="R2", version="2.0", package="p2"),
            ]
            mock.return_value = mock_manager

            result = runner.invoke(release, ["list"])

            assert result.exit_code == 0
            assert "R1" in result.output
            assert "R2" in result.output

    def test_list_releases_empty(self, runner: CliRunner) -> None:
        """Test listing releases when empty."""
        with patch("headless_wheel_builder.release.cli.get_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.list_releases.return_value = []
            mock.return_value = mock_manager

            result = runner.invoke(release, ["list"])

            assert result.exit_code == 0
            assert "No releases found" in result.output

    def test_show_release(self, runner: CliRunner) -> None:
        """Test showing a release."""
        with patch("headless_wheel_builder.release.cli.get_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.get_release.return_value = DraftRelease(
                id="rel-123",
                name="Test Release",
                version="1.0.0",
                package="my-package",
                changelog="Test changes",
            )
            mock.return_value = mock_manager

            result = runner.invoke(release, ["show", "rel-123"])

            assert result.exit_code == 0
            assert "rel-123" in result.output
            assert "Test Release" in result.output

    def test_show_release_not_found(self, runner: CliRunner) -> None:
        """Test showing a nonexistent release."""
        with patch("headless_wheel_builder.release.cli.get_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.get_release.return_value = None
            mock.return_value = mock_manager

            result = runner.invoke(release, ["show", "nonexistent"])

            assert result.exit_code == 1
            assert "not found" in result.output

    def test_submit_release(self, runner: CliRunner) -> None:
        """Test submitting a release."""
        with patch("headless_wheel_builder.release.cli.get_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.submit_for_approval.return_value = True
            mock.return_value = mock_manager

            result = runner.invoke(release, ["submit", "rel-123"])

            assert result.exit_code == 0
            assert "submitted" in result.output

    def test_approve_release(self, runner: CliRunner) -> None:
        """Test approving a release."""
        with patch("headless_wheel_builder.release.cli.get_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.approve.return_value = True
            mock_manager.get_release.return_value = DraftRelease(
                id="rel-123",
                name="Test",
                version="1.0.0",
                package="pkg",
            )
            mock.return_value = mock_manager

            result = runner.invoke(
                release,
                [
                    "approve",
                    "rel-123",
                    "-a",
                    "alice",
                ],
            )

            assert result.exit_code == 0
            assert "approved" in result.output.lower()

    def test_reject_release(self, runner: CliRunner) -> None:
        """Test rejecting a release."""
        with patch("headless_wheel_builder.release.cli.get_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.reject.return_value = True
            mock.return_value = mock_manager

            result = runner.invoke(
                release,
                [
                    "reject",
                    "rel-123",
                    "-r",
                    "alice",
                    "-c",
                    "Not ready",
                ],
            )

            assert result.exit_code == 0
            assert "rejected" in result.output.lower()

    def test_publish_release(self, runner: CliRunner) -> None:
        """Test publishing a release."""
        with patch("headless_wheel_builder.release.cli.get_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.publish.return_value = True
            mock.return_value = mock_manager

            result = runner.invoke(
                release,
                [
                    "publish",
                    "rel-123",
                    "-p",
                    "publisher",
                ],
            )

            assert result.exit_code == 0
            assert "published" in result.output.lower()

    def test_rollback_release(self, runner: CliRunner) -> None:
        """Test rolling back a release."""
        with patch("headless_wheel_builder.release.cli.get_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.rollback.return_value = True
            mock.return_value = mock_manager

            result = runner.invoke(release, ["rollback", "rel-123", "-y"])

            assert result.exit_code == 0
            assert "rolled back" in result.output.lower()

    def test_delete_release(self, runner: CliRunner) -> None:
        """Test deleting a release."""
        with patch("headless_wheel_builder.release.cli.get_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.delete.return_value = True
            mock.return_value = mock_manager

            result = runner.invoke(release, ["delete", "rel-123", "-y"])

            assert result.exit_code == 0
            assert "deleted" in result.output.lower()

    def test_pending_approvals(self, runner: CliRunner) -> None:
        """Test showing pending approvals."""
        with patch("headless_wheel_builder.release.cli.get_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.list_releases.return_value = [
                DraftRelease(
                    id="r1",
                    name="R1",
                    version="1.0",
                    package="p1",
                    status=ReleaseStatus.PENDING_APPROVAL,
                ),
            ]
            mock.return_value = mock_manager

            result = runner.invoke(release, ["pending"])

            assert result.exit_code == 0
            assert "R1" in result.output

    def test_stats(self, runner: CliRunner) -> None:
        """Test showing statistics."""
        with patch("headless_wheel_builder.release.cli.get_manager") as mock:
            mock_manager = MagicMock()
            mock_manager.get_statistics.return_value = {
                "total": 5,
                "pending_approval": 2,
                "by_status": {"draft": 3, "pending_approval": 2},
                "by_package": {"pkg1": 3, "pkg2": 2},
            }
            mock.return_value = mock_manager

            result = runner.invoke(release, ["stats"])

            assert result.exit_code == 0
            assert "5" in result.output
            assert "2" in result.output

    def test_templates(self, runner: CliRunner) -> None:
        """Test showing workflow templates."""
        result = runner.invoke(release, ["templates"])

        assert result.exit_code == 0
        assert "simple" in result.output
        assert "two-stage" in result.output
        assert "enterprise" in result.output
