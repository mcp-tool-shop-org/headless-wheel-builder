"""Integration tests for versioning workflow.

These tests exercise the versioning module with real git repositories.
"""

from __future__ import annotations

import subprocess
from datetime import date
from typing import TYPE_CHECKING

import pytest

from headless_wheel_builder.version.changelog import (
    create_changelog_entry,
    generate_changelog,
    generate_full_changelog,
)
from headless_wheel_builder.version.conventional import (
    determine_bump_from_commits,
    parse_commit,
)
from headless_wheel_builder.version.git import (
    create_tag,
    get_commits_since_tag,
    get_current_branch,
    get_head_commit,
    get_latest_tag,
    is_dirty,
)
from headless_wheel_builder.version.semver import (
    Version,
    parse_version,
)

if TYPE_CHECKING:
    from pathlib import Path

# Mark all tests as integration tests
pytestmark = pytest.mark.integration


def run_git(repo_path: Path, *args: str) -> str:
    """Run a git command synchronously."""
    result = subprocess.run(
        ["git", *args],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Git command failed: {result.stderr}")
    return result.stdout.strip()


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a git repository for testing."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize git repo
    run_git(repo_path, "init")
    run_git(repo_path, "config", "user.email", "test@example.com")
    run_git(repo_path, "config", "user.name", "Test User")

    # Create initial commit
    (repo_path / "README.md").write_text("# Test Project")
    run_git(repo_path, "add", "README.md")
    run_git(repo_path, "commit", "-m", "chore: initial commit")

    return repo_path


class TestGitIntegration:
    """Test git operations with real repositories."""

    @pytest.mark.asyncio
    async def test_get_current_branch(self, git_repo: Path):
        """Test getting current branch."""
        branch = await get_current_branch(git_repo)
        assert branch in ("main", "master")  # Depends on git config

    @pytest.mark.asyncio
    async def test_get_head_commit(self, git_repo: Path):
        """Test getting HEAD commit hash."""
        commit = await get_head_commit(git_repo)
        assert len(commit) == 40  # Full SHA
        assert all(c in "0123456789abcdef" for c in commit)

    @pytest.mark.asyncio
    async def test_is_dirty_clean_repo(self, git_repo: Path):
        """Test checking clean repository."""
        dirty = await is_dirty(git_repo)
        assert dirty is False

    @pytest.mark.asyncio
    async def test_is_dirty_with_changes(self, git_repo: Path):
        """Test checking repository with uncommitted changes."""
        # Make a change
        (git_repo / "new_file.txt").write_text("content")

        dirty = await is_dirty(git_repo)
        assert dirty is True

    @pytest.mark.asyncio
    async def test_create_and_get_tag(self, git_repo: Path):
        """Test creating and retrieving tags."""
        # Create a tag
        tag = await create_tag(
            git_repo,
            tag_name="v1.0.0",
            message="Release 1.0.0",
        )

        assert tag.name == "v1.0.0"
        assert tag.version == Version(1, 0, 0)
        assert len(tag.commit_hash) == 40

        # Get the tag back
        latest = await get_latest_tag(git_repo)
        assert latest is not None
        assert latest.name == "v1.0.0"
        assert latest.version == Version(1, 0, 0)

    @pytest.mark.asyncio
    async def test_get_latest_tag_no_tags(self, git_repo: Path):
        """Test getting latest tag when none exist."""
        latest = await get_latest_tag(git_repo)
        assert latest is None

    @pytest.mark.asyncio
    async def test_multiple_tags_ordering(self, git_repo: Path):
        """Test that latest tag is returned correctly with multiple tags."""
        # Create v1.0.0
        await create_tag(git_repo, tag_name="v1.0.0", message="Release 1.0.0")

        # Add a commit
        (git_repo / "feature.py").write_text("# feature")
        run_git(git_repo, "add", "feature.py")
        run_git(git_repo, "commit", "-m", "feat: add feature")

        # Create v1.1.0
        await create_tag(git_repo, tag_name="v1.1.0", message="Release 1.1.0")

        # Latest should be v1.1.0
        latest = await get_latest_tag(git_repo)
        assert latest is not None
        assert latest.name == "v1.1.0"
        assert latest.version == Version(1, 1, 0)

    @pytest.mark.asyncio
    async def test_get_commits_since_tag(self, git_repo: Path):
        """Test getting commits since a tag."""
        # Create initial tag
        await create_tag(git_repo, tag_name="v1.0.0", message="Release 1.0.0")

        # Add some commits
        (git_repo / "feat1.py").write_text("# feat 1")
        run_git(git_repo, "add", "feat1.py")
        run_git(git_repo, "commit", "-m", "feat: add feature 1")

        (git_repo / "fix1.py").write_text("# fix 1")
        run_git(git_repo, "add", "fix1.py")
        run_git(git_repo, "commit", "-m", "fix: fix bug 1")

        # Get commits since tag
        commits = await get_commits_since_tag(git_repo, tag="v1.0.0")

        assert len(commits) == 2
        assert any("feat: add feature 1" in msg for _, msg in commits)
        assert any("fix: fix bug 1" in msg for _, msg in commits)

    @pytest.mark.asyncio
    async def test_prerelease_tag_filtering(self, git_repo: Path):
        """Test filtering prerelease tags."""
        # Create stable and prerelease tags
        await create_tag(git_repo, tag_name="v1.0.0", message="Stable")

        (git_repo / "file1.py").write_text("# 1")
        run_git(git_repo, "add", "file1.py")
        run_git(git_repo, "commit", "-m", "feat: feature")

        await create_tag(git_repo, tag_name="v1.1.0-alpha.1", message="Alpha")

        # Include prereleases
        latest = await get_latest_tag(git_repo, include_prereleases=True)
        assert latest.version.is_prerelease

        # Exclude prereleases
        stable = await get_latest_tag(git_repo, include_prereleases=False)
        assert stable.version == Version(1, 0, 0)


class TestVersionBumpWorkflow:
    """Test complete version bump workflows."""

    @pytest.mark.asyncio
    async def test_feature_release_workflow(self, git_repo: Path):
        """Test workflow for feature release."""
        # Create initial release
        await create_tag(git_repo, tag_name="v1.0.0", message="Initial release")

        # Add feature commits
        (git_repo / "feature.py").write_text("# new feature")
        run_git(git_repo, "add", "feature.py")
        run_git(git_repo, "commit", "-m", "feat: add new feature")

        (git_repo / "another.py").write_text("# another")
        run_git(git_repo, "add", "another.py")
        run_git(git_repo, "commit", "-m", "feat(api): add api endpoint")

        # Get commits
        raw_commits = await get_commits_since_tag(git_repo, tag="v1.0.0")
        commits = [parse_commit(msg, hash=h) for h, msg in raw_commits]

        # Determine bump
        bump_type = determine_bump_from_commits(commits)
        assert bump_type.value == "minor"

        # Calculate new version
        current = parse_version("v1.0.0")
        new_version = current.bump(bump_type)
        assert new_version == Version(1, 1, 0)

        # Generate changelog
        changelog = generate_changelog(
            commits=commits,
            version=new_version,
            previous_version=current,
            release_date=date.today(),
        )

        assert "1.1.0" in changelog
        assert "Features" in changelog
        assert "add new feature" in changelog
        assert "add api endpoint" in changelog

        # Create new tag
        tag = await create_tag(
            git_repo,
            tag_name=f"v{new_version}",
            message=f"Release {new_version}",
        )
        assert tag.version == Version(1, 1, 0)

    @pytest.mark.asyncio
    async def test_breaking_change_workflow(self, git_repo: Path):
        """Test workflow for breaking change release."""
        await create_tag(git_repo, tag_name="v1.5.0", message="Current")

        # Add breaking change
        (git_repo / "breaking.py").write_text("# breaking change")
        run_git(git_repo, "add", "breaking.py")
        run_git(git_repo, "commit", "-m", "feat!: breaking api change")

        raw_commits = await get_commits_since_tag(git_repo, tag="v1.5.0")
        commits = [parse_commit(msg, hash=h) for h, msg in raw_commits]

        bump_type = determine_bump_from_commits(commits)
        assert bump_type.value == "major"

        new_version = parse_version("v1.5.0").bump(bump_type)
        assert new_version == Version(2, 0, 0)

    @pytest.mark.asyncio
    async def test_patch_release_workflow(self, git_repo: Path):
        """Test workflow for patch release."""
        await create_tag(git_repo, tag_name="v2.1.0", message="Current")

        # Add bug fixes
        (git_repo / "fix.py").write_text("# bug fix")
        run_git(git_repo, "add", "fix.py")
        run_git(git_repo, "commit", "-m", "fix: fix critical bug")

        raw_commits = await get_commits_since_tag(git_repo, tag="v2.1.0")
        commits = [parse_commit(msg, hash=h) for h, msg in raw_commits]

        bump_type = determine_bump_from_commits(commits)
        assert bump_type.value == "patch"

        new_version = parse_version("v2.1.0").bump(bump_type)
        assert new_version == Version(2, 1, 1)


class TestChangelogGeneration:
    """Test changelog generation with realistic data."""

    @pytest.mark.asyncio
    async def test_generate_release_changelog(self, git_repo: Path):
        """Test generating changelog for a release."""
        await create_tag(git_repo, tag_name="v0.9.0", message="Previous")

        # Various commits
        commits_data = [
            ("feat.py", "feat: add user authentication"),
            ("fix.py", "fix: resolve login timeout"),
            ("docs.py", "docs: update README"),
            ("perf.py", "perf: optimize database queries"),
            ("breaking.py", "feat(api)!: redesign REST endpoints"),
        ]

        for filename, message in commits_data:
            (git_repo / filename).write_text(f"# {filename}")
            run_git(git_repo, "add", filename)
            run_git(git_repo, "commit", "-m", message)

        raw_commits = await get_commits_since_tag(git_repo, tag="v0.9.0")
        commits = [parse_commit(msg, hash=h) for h, msg in raw_commits]

        changelog = generate_changelog(
            commits=commits,
            version="1.0.0",
            previous_version="0.9.0",
            release_date=date(2024, 6, 15),
            repo_url="https://github.com/example/project",
        )

        # Check structure
        assert "## [1.0.0]" in changelog
        assert "2024-06-15" in changelog
        assert "compare/v0.9.0...v1.0.0" in changelog

        # Check sections
        assert "### Breaking Changes" in changelog
        assert "### Features" in changelog
        assert "### Bug Fixes" in changelog
        assert "### Performance" in changelog or "### Performance Improvements" in changelog

        # Check content
        assert "user authentication" in changelog
        assert "login timeout" in changelog
        assert "REST endpoints" in changelog

    def test_generate_full_changelog_multiple_releases(self):
        """Test generating full changelog with multiple releases."""
        entries = [
            create_changelog_entry(
                version=Version(1, 2, 0),
                commits=[
                    parse_commit("feat: feature 3"),
                    parse_commit("fix: fix 3"),
                ],
                release_date=date(2024, 3, 1),
            ),
            create_changelog_entry(
                version=Version(1, 1, 0),
                commits=[
                    parse_commit("feat: feature 2"),
                ],
                release_date=date(2024, 2, 1),
            ),
            create_changelog_entry(
                version=Version(1, 0, 0),
                commits=[
                    parse_commit("feat: initial feature"),
                ],
                release_date=date(2024, 1, 1),
            ),
        ]

        full_changelog = generate_full_changelog(
            entries,
            title="My Project Changelog",
            description="All notable changes to this project.",
            repo_url="https://github.com/example/project",
        )

        # Check structure
        assert "# My Project Changelog" in full_changelog
        assert "All notable changes" in full_changelog

        # Check all versions are present
        assert "1.2.0" in full_changelog
        assert "1.1.0" in full_changelog
        assert "1.0.0" in full_changelog

        # Check chronological order (newest first)
        idx_120 = full_changelog.index("1.2.0")
        idx_110 = full_changelog.index("1.1.0")
        idx_100 = full_changelog.index("1.0.0")
        assert idx_120 < idx_110 < idx_100


class TestPrereleaseWorkflow:
    """Test prerelease version workflows."""

    def test_alpha_beta_rc_workflow(self):
        """Test alpha -> beta -> rc -> stable workflow."""
        # Start with stable
        stable = parse_version("1.0.0")

        # Create alpha for next minor
        alpha1 = stable.bump("minor").with_prerelease("alpha.1")
        assert str(alpha1) == "1.1.0-alpha.1"

        # Bump alpha
        alpha2 = alpha1.bump("prerelease")
        assert str(alpha2) == "1.1.0-alpha.2"

        # Move to beta
        beta1 = alpha2.base_version.with_prerelease("beta.1")
        assert str(beta1) == "1.1.0-beta.1"

        # Move to rc
        rc1 = beta1.base_version.with_prerelease("rc.1")
        assert str(rc1) == "1.1.0-rc.1"

        # Release stable
        new_stable = rc1.base_version
        assert str(new_stable) == "1.1.0"
        assert new_stable.is_stable

    def test_prerelease_to_pep440(self):
        """Test converting prereleases to PEP 440."""
        versions = [
            ("1.0.0-alpha.1", "1.0.0a1"),
            ("1.0.0-beta.2", "1.0.0b2"),
            ("1.0.0-rc.3", "1.0.0rc3"),
            ("1.0.0-dev.1", "1.0.0.dev1"),
        ]

        for semver_str, expected_pep440 in versions:
            version = parse_version(semver_str)
            assert version.to_pep440() == expected_pep440


class TestConventionalCommitParsing:
    """Test parsing various conventional commit formats."""

    def test_parse_complex_commit(self):
        """Test parsing commit with body and footers."""
        message = """feat(authentication): add OAuth2 support

This commit adds OAuth2 authentication support for Google and GitHub.

The implementation includes:
- OAuth2 flow handling
- Token storage and refresh
- User profile fetching

Closes: #123
Reviewed-by: John Doe
"""
        commit = parse_commit(message)

        assert commit.type.value == "feat"
        assert commit.scope == "authentication"
        assert commit.description == "add OAuth2 support"
        assert commit.body is not None
        assert "OAuth2 authentication" in commit.body
        assert commit.breaking is False

    def test_parse_breaking_change_footer(self):
        """Test parsing breaking change in footer."""
        message = """refactor(api): simplify response format

BREAKING CHANGE: Response now returns data directly instead of wrapped in envelope.
"""
        commit = parse_commit(message)

        assert commit.breaking is True
        assert "envelope" in commit.breaking_description or commit.breaking_description is not None

    def test_parse_multiple_scopes(self):
        """Test commits with different scopes."""
        commits_text = [
            "feat(api): add new endpoint",
            "feat(cli): add new command",
            "feat(core): add new utility",
            "fix(api): fix response parsing",
        ]

        parsed = [parse_commit(c) for c in commits_text]

        assert parsed[0].scope == "api"
        assert parsed[1].scope == "cli"
        assert parsed[2].scope == "core"
        assert parsed[3].scope == "api"
