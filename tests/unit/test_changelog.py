"""Tests for changelog generation."""

from __future__ import annotations

from headless_wheel_builder.changelog.generator import (
    Changelog,
    ChangelogConfig,
    ChangelogEntry,
    ChangelogFormat,
)
from headless_wheel_builder.changelog.parser import (
    CommitType,
    ConventionalCommit,
    parse_commits,
)


class TestCommitType:
    """Tests for CommitType enum."""

    def test_from_string_valid(self) -> None:
        """Test parsing valid commit types."""
        assert CommitType.from_string("feat") == CommitType.FEAT
        assert CommitType.from_string("fix") == CommitType.FIX
        assert CommitType.from_string("docs") == CommitType.DOCS
        assert CommitType.from_string("FEAT") == CommitType.FEAT  # case insensitive

    def test_from_string_invalid(self) -> None:
        """Test parsing invalid commit type."""
        assert CommitType.from_string("unknown") == CommitType.OTHER
        assert CommitType.from_string("") == CommitType.OTHER


class TestConventionalCommit:
    """Tests for ConventionalCommit parsing."""

    def test_parse_simple(self) -> None:
        """Test parsing simple commit."""
        commit = ConventionalCommit.parse("feat: add new feature")
        assert commit is not None
        assert commit.type == CommitType.FEAT
        assert commit.scope is None
        assert commit.description == "add new feature"
        assert commit.breaking is False

    def test_parse_with_scope(self) -> None:
        """Test parsing commit with scope."""
        commit = ConventionalCommit.parse("fix(api): resolve endpoint issue")
        assert commit is not None
        assert commit.type == CommitType.FIX
        assert commit.scope == "api"
        assert commit.description == "resolve endpoint issue"

    def test_parse_breaking_indicator(self) -> None:
        """Test parsing breaking change with ! indicator."""
        commit = ConventionalCommit.parse("feat!: major breaking change")
        assert commit is not None
        assert commit.type == CommitType.FEAT
        assert commit.breaking is True

    def test_parse_breaking_with_scope(self) -> None:
        """Test parsing breaking change with scope."""
        commit = ConventionalCommit.parse("feat(api)!: breaking api change")
        assert commit is not None
        assert commit.scope == "api"
        assert commit.breaking is True

    def test_parse_with_body(self) -> None:
        """Test parsing commit with body."""
        message = """feat: add user authentication

This commit adds a complete authentication system
with JWT tokens and refresh logic."""
        commit = ConventionalCommit.parse(message)
        assert commit is not None
        assert commit.description == "add user authentication"
        assert commit.body is not None
        assert "JWT tokens" in commit.body

    def test_parse_with_footer(self) -> None:
        """Test parsing commit with footer."""
        message = """fix: resolve memory leak

Fixed the memory leak in cache handler.

Fixes: #123
Reviewed-by: Alice"""
        commit = ConventionalCommit.parse(message)
        assert commit is not None
        assert "Fixes" in commit.footers
        assert commit.footers["Fixes"] == "#123"
        assert "Reviewed-by" in commit.footers

    def test_parse_breaking_change_footer(self) -> None:
        """Test parsing BREAKING CHANGE footer."""
        message = """refactor: restructure api

BREAKING CHANGE: The API endpoints have been renamed"""
        commit = ConventionalCommit.parse(message)
        assert commit is not None
        assert commit.breaking is True
        assert commit.breaking_description == "The API endpoints have been renamed"

    def test_parse_invalid(self) -> None:
        """Test parsing invalid commit message."""
        assert ConventionalCommit.parse("") is None
        assert ConventionalCommit.parse("just a regular commit") is None
        assert ConventionalCommit.parse("no colon here") is None

    def test_parse_with_sha(self) -> None:
        """Test parsing with SHA."""
        commit = ConventionalCommit.parse("feat: new feature", sha="abc1234")
        assert commit is not None
        assert commit.sha == "abc1234"

    def test_summary(self) -> None:
        """Test summary generation."""
        commit = ConventionalCommit.parse("feat(ui): add button")
        assert commit is not None
        assert commit.summary == "feat(ui): add button"

        commit2 = ConventionalCommit.parse("fix: bug fix")
        assert commit2 is not None
        assert commit2.summary == "fix: bug fix"

    def test_is_feature(self) -> None:
        """Test is_feature property."""
        feat = ConventionalCommit.parse("feat: new feature")
        fix = ConventionalCommit.parse("fix: bug fix")
        assert feat is not None and feat.is_feature is True
        assert fix is not None and fix.is_feature is False

    def test_is_fix(self) -> None:
        """Test is_fix property."""
        feat = ConventionalCommit.parse("feat: new feature")
        fix = ConventionalCommit.parse("fix: bug fix")
        assert feat is not None and feat.is_fix is False
        assert fix is not None and fix.is_fix is True

    def test_is_notable(self) -> None:
        """Test is_notable property."""
        feat = ConventionalCommit.parse("feat: new feature")
        fix = ConventionalCommit.parse("fix: bug fix")
        chore = ConventionalCommit.parse("chore: update deps")
        breaking = ConventionalCommit.parse("chore!: breaking chore")

        assert feat is not None and feat.is_notable is True
        assert fix is not None and fix.is_notable is True
        assert chore is not None and chore.is_notable is False
        assert breaking is not None and breaking.is_notable is True


class TestParseCommits:
    """Tests for parse_commits function."""

    def test_parse_multiple(self) -> None:
        """Test parsing multiple commits."""
        commits = [
            ("abc1234", "feat: first feature"),
            ("def5678", "fix: bug fix"),
            ("ghi9012", "not conventional"),
        ]
        result = parse_commits(commits)
        assert len(result) == 2  # Only conventional commits
        assert result[0].sha == "abc1234"
        assert result[1].sha == "def5678"

    def test_parse_include_non_conventional(self) -> None:
        """Test including non-conventional commits."""
        commits = [
            ("abc1234", "feat: feature"),
            ("def5678", "regular commit message"),
        ]
        result = parse_commits(commits, include_non_conventional=True)
        assert len(result) == 2
        assert result[1].type == CommitType.OTHER


class TestChangelogEntry:
    """Tests for ChangelogEntry."""

    def test_from_commit_basic(self) -> None:
        """Test creating entry from commit."""
        commit = ConventionalCommit.parse("feat: new feature", sha="abc1234")
        assert commit is not None
        entry = ChangelogEntry.from_commit(commit)
        assert "new feature" in entry.formatted
        assert "abc1234" in entry.formatted

    def test_from_commit_with_scope(self) -> None:
        """Test entry with scope."""
        commit = ConventionalCommit.parse("feat(api): api feature", sha="abc1234")
        assert commit is not None
        entry = ChangelogEntry.from_commit(commit, show_scope=True)
        assert "**api:**" in entry.formatted

    def test_from_commit_no_sha(self) -> None:
        """Test entry without SHA."""
        commit = ConventionalCommit.parse("feat: feature", sha="abc1234")
        assert commit is not None
        entry = ChangelogEntry.from_commit(commit, show_sha=False)
        assert "abc1234" not in entry.formatted

    def test_from_commit_no_scope(self) -> None:
        """Test entry without scope display."""
        commit = ConventionalCommit.parse("feat(api): feature", sha="abc1234")
        assert commit is not None
        entry = ChangelogEntry.from_commit(commit, show_scope=False)
        assert "**api:**" not in entry.formatted


class TestChangelogConfig:
    """Tests for ChangelogConfig."""

    def test_defaults(self) -> None:
        """Test default configuration."""
        config = ChangelogConfig()
        assert config.repo_path == "."
        assert config.to_ref == "HEAD"
        assert config.format == ChangelogFormat.MARKDOWN
        assert config.group_by_type is True
        assert config.show_sha is True

    def test_custom_config(self) -> None:
        """Test custom configuration."""
        config = ChangelogConfig(
            tag="v1.0.0",
            format=ChangelogFormat.GITHUB,
            show_sha=False,
        )
        assert config.tag == "v1.0.0"
        assert config.format == ChangelogFormat.GITHUB
        assert config.show_sha is False


class TestChangelog:
    """Tests for Changelog generation."""

    def test_empty_changelog(self) -> None:
        """Test empty changelog."""
        config = ChangelogConfig(tag="v1.0.0")
        log = Changelog(config=config, commits=[])
        assert len(log.commits) == 0
        assert len(log.breaking_changes) == 0

    def test_changelog_grouping(self) -> None:
        """Test commit grouping by type."""
        config = ChangelogConfig(tag="v1.0.0")
        commits = [
            ConventionalCommit.parse("feat: feature 1", sha="a"),
            ConventionalCommit.parse("feat: feature 2", sha="b"),
            ConventionalCommit.parse("fix: bug fix", sha="c"),
        ]
        commits = [c for c in commits if c is not None]
        log = Changelog(config=config, commits=commits)

        assert CommitType.FEAT in log.entries_by_type
        assert len(log.entries_by_type[CommitType.FEAT]) == 2
        assert CommitType.FIX in log.entries_by_type
        assert len(log.entries_by_type[CommitType.FIX]) == 1

    def test_breaking_changes_extracted(self) -> None:
        """Test breaking changes extraction."""
        config = ChangelogConfig()
        commits = [
            ConventionalCommit.parse("feat!: breaking feature", sha="a"),
            ConventionalCommit.parse("fix: normal fix", sha="b"),
        ]
        commits = [c for c in commits if c is not None]
        log = Changelog(config=config, commits=commits)

        assert len(log.breaking_changes) == 1
        assert log.breaking_changes[0].description == "breaking feature"

    def test_to_markdown(self) -> None:
        """Test markdown output."""
        config = ChangelogConfig(tag="v1.0.0")
        commits = [
            ConventionalCommit.parse("feat: new feature", sha="abc1234"),
            ConventionalCommit.parse("fix: bug fix", sha="def5678"),
        ]
        commits = [c for c in commits if c is not None]
        log = Changelog(config=config, commits=commits)
        md = log.to_markdown()

        assert "## v1.0.0" in md
        assert "### ✨ Features" in md
        assert "### 🐛 Bug Fixes" in md
        assert "new feature" in md
        assert "bug fix" in md

    def test_to_plain(self) -> None:
        """Test plain text output."""
        config = ChangelogConfig(tag="v1.0.0")
        commits = [ConventionalCommit.parse("feat: feature", sha="abc")]
        commits = [c for c in commits if c is not None]
        log = Changelog(config=config, commits=commits)
        plain = log.to_plain()

        assert "Release v1.0.0" in plain
        assert "Features:" in plain

    def test_to_github(self) -> None:
        """Test GitHub format output."""
        config = ChangelogConfig(tag="v1.0.0", format=ChangelogFormat.GITHUB)
        commits = [
            ConventionalCommit.parse("feat!: breaking", sha="a"),
            ConventionalCommit.parse("feat: normal", sha="b"),
        ]
        commits = [c for c in commits if c is not None]
        log = Changelog(config=config, commits=commits)
        github = log.to_github()

        assert "## What's Changed" in github
        assert "BREAKING" in github

    def test_to_json(self) -> None:
        """Test JSON output."""
        config = ChangelogConfig(tag="v1.0.0")
        commits = [ConventionalCommit.parse("feat: feature", sha="abc1234")]
        commits = [c for c in commits if c is not None]
        log = Changelog(config=config, commits=commits)
        data = log.to_json()

        assert data["tag"] == "v1.0.0"
        assert "stats" in data
        assert data["stats"]["features"] == 1

    def test_render_markdown(self) -> None:
        """Test render with markdown format."""
        config = ChangelogConfig(format=ChangelogFormat.MARKDOWN)
        log = Changelog(config=config, commits=[])
        output = log.render()
        assert isinstance(output, str)

    def test_render_json(self) -> None:
        """Test render with JSON format."""
        config = ChangelogConfig(format=ChangelogFormat.JSON)
        log = Changelog(config=config, commits=[])
        output = log.render()
        assert "{" in output  # JSON format
