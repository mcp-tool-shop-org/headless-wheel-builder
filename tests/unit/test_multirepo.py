"""Tests for multi-repository operations."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from headless_wheel_builder.multirepo.config import (
    MultiRepoConfig,
    RepoConfig,
    load_config,
    save_config,
)
from headless_wheel_builder.multirepo.manager import (
    BatchResult,
    MultiRepoManager,
    OperationType,
    RepoResult,
)


class TestRepoConfig:
    """Tests for RepoConfig model."""

    def test_defaults(self) -> None:
        """Test default configuration."""
        config = RepoConfig(name="owner/repo")
        assert config.name == "owner/repo"
        assert config.path is None
        assert config.url is None
        assert config.branch == "main"
        assert config.python_version == "3.12"
        assert config.dependencies == []
        assert config.build_args == {}
        assert config.enabled is True
        assert config.tags == []

    def test_custom_values(self) -> None:
        """Test custom configuration."""
        config = RepoConfig(
            name="owner/repo",
            path="/path/to/repo",
            url="https://github.com/owner/repo",
            branch="develop",
            python_version="3.11",
            dependencies=["other/repo"],
            build_args={"wheel": True},
            enabled=False,
            tags=["core", "lib"],
        )
        assert config.path == "/path/to/repo"
        assert config.url == "https://github.com/owner/repo"
        assert config.branch == "develop"
        assert config.python_version == "3.11"
        assert config.dependencies == ["other/repo"]
        assert config.build_args == {"wheel": True}
        assert config.enabled is False
        assert config.tags == ["core", "lib"]

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        config = RepoConfig(
            name="owner/repo",
            path="/path/to/repo",
            dependencies=["dep1", "dep2"],
        )
        data = config.to_dict()
        assert data["name"] == "owner/repo"
        assert data["path"] == "/path/to/repo"
        assert data["dependencies"] == ["dep1", "dep2"]

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        data = {
            "name": "owner/repo",
            "path": "/path/to/repo",
            "branch": "develop",
            "dependencies": ["dep1"],
        }
        config = RepoConfig.from_dict(data)
        assert config.name == "owner/repo"
        assert config.path == "/path/to/repo"
        assert config.branch == "develop"
        assert config.dependencies == ["dep1"]

    def test_from_dict_minimal(self) -> None:
        """Test creation from minimal dictionary."""
        data = {"name": "owner/repo"}
        config = RepoConfig.from_dict(data)
        assert config.name == "owner/repo"
        assert config.branch == "main"
        assert config.python_version == "3.12"


class TestMultiRepoConfig:
    """Tests for MultiRepoConfig model."""

    def test_defaults(self) -> None:
        """Test default configuration."""
        config = MultiRepoConfig()
        assert config.name == "default"
        assert config.repos == []
        assert config.parallel == 4
        assert config.fail_fast is False
        assert config.output_dir == "dist"
        assert config.github_token_env == "GITHUB_TOKEN"

    def test_add_repo(self) -> None:
        """Test adding a repository."""
        config = MultiRepoConfig()
        repo = RepoConfig(name="owner/repo")
        config.add_repo(repo)
        assert len(config.repos) == 1
        assert config.repos[0].name == "owner/repo"

    def test_add_repo_replaces_existing(self) -> None:
        """Test adding a repo with same name replaces existing."""
        config = MultiRepoConfig()
        repo1 = RepoConfig(name="owner/repo", python_version="3.10")
        repo2 = RepoConfig(name="owner/repo", python_version="3.11")
        config.add_repo(repo1)
        config.add_repo(repo2)
        assert len(config.repos) == 1
        assert config.repos[0].python_version == "3.11"

    def test_remove_repo(self) -> None:
        """Test removing a repository."""
        config = MultiRepoConfig()
        config.add_repo(RepoConfig(name="repo1"))
        config.add_repo(RepoConfig(name="repo2"))
        removed = config.remove_repo("repo1")
        assert removed is True
        assert len(config.repos) == 1
        assert config.repos[0].name == "repo2"

    def test_remove_repo_not_found(self) -> None:
        """Test removing non-existent repository."""
        config = MultiRepoConfig()
        removed = config.remove_repo("nonexistent")
        assert removed is False

    def test_get_repo(self) -> None:
        """Test getting a repository by name."""
        config = MultiRepoConfig()
        config.add_repo(RepoConfig(name="owner/repo"))
        repo = config.get_repo("owner/repo")
        assert repo is not None
        assert repo.name == "owner/repo"

    def test_get_repo_not_found(self) -> None:
        """Test getting non-existent repository."""
        config = MultiRepoConfig()
        repo = config.get_repo("nonexistent")
        assert repo is None

    def test_get_enabled_repos(self) -> None:
        """Test getting enabled repositories."""
        config = MultiRepoConfig()
        config.add_repo(RepoConfig(name="enabled1", enabled=True))
        config.add_repo(RepoConfig(name="disabled", enabled=False))
        config.add_repo(RepoConfig(name="enabled2", enabled=True))
        enabled = config.get_enabled_repos()
        assert len(enabled) == 2
        names = [r.name for r in enabled]
        assert "enabled1" in names
        assert "enabled2" in names
        assert "disabled" not in names

    def test_get_repos_by_tag(self) -> None:
        """Test getting repositories by tag."""
        config = MultiRepoConfig()
        config.add_repo(RepoConfig(name="core1", tags=["core"]))
        config.add_repo(RepoConfig(name="ext1", tags=["extension"]))
        config.add_repo(RepoConfig(name="both", tags=["core", "extension"]))
        core = config.get_repos_by_tag("core")
        assert len(core) == 2
        names = [r.name for r in core]
        assert "core1" in names
        assert "both" in names

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        config = MultiRepoConfig(name="test", parallel=2)
        config.add_repo(RepoConfig(name="repo1"))
        data = config.to_dict()
        assert data["name"] == "test"
        assert data["parallel"] == 2
        assert len(data["repos"]) == 1

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        data = {
            "name": "test",
            "parallel": 2,
            "repos": [{"name": "repo1"}, {"name": "repo2"}],
        }
        config = MultiRepoConfig.from_dict(data)
        assert config.name == "test"
        assert config.parallel == 2
        assert len(config.repos) == 2


class TestConfigIO:
    """Tests for configuration file I/O."""

    def test_save_and_load_json(self) -> None:
        """Test saving and loading JSON config."""
        config = MultiRepoConfig(name="test")
        config.add_repo(RepoConfig(name="repo1"))

        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "config.json"
            save_config(config, path)
            loaded = load_config(path)

        assert loaded.name == "test"
        assert len(loaded.repos) == 1
        assert loaded.repos[0].name == "repo1"

    def test_load_not_found(self) -> None:
        """Test loading non-existent file."""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path.json")

    def test_save_creates_directory(self) -> None:
        """Test save creates parent directories."""
        config = MultiRepoConfig()
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nested" / "dir" / "config.json"
            save_config(config, path)
            assert path.exists()


class TestRepoResult:
    """Tests for RepoResult model."""

    def test_success_result(self) -> None:
        """Test successful result."""
        repo = RepoConfig(name="owner/repo")
        result = RepoResult(
            repo=repo,
            operation=OperationType.BUILD,
            success=True,
            message="Built successfully",
            duration_seconds=5.0,
        )
        assert result.success is True
        assert result.error is None

    def test_failure_result(self) -> None:
        """Test failed result."""
        repo = RepoConfig(name="owner/repo")
        result = RepoResult(
            repo=repo,
            operation=OperationType.BUILD,
            success=False,
            message="Build failed",
            error="Missing dependency",
        )
        assert result.success is False
        assert result.error == "Missing dependency"

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        repo = RepoConfig(name="owner/repo")
        result = RepoResult(
            repo=repo,
            operation=OperationType.BUILD,
            success=True,
            message="OK",
            duration_seconds=1.5,
        )
        data = result.to_dict()
        assert data["repo"] == "owner/repo"
        assert data["operation"] == "build"
        assert data["success"] is True
        assert data["duration_seconds"] == 1.5


class TestBatchResult:
    """Tests for BatchResult model."""

    def test_empty_result(self) -> None:
        """Test empty batch result."""
        result = BatchResult(operation=OperationType.BUILD)
        assert result.success is True
        assert len(result.results) == 0
        assert len(result.succeeded) == 0
        assert len(result.failed) == 0

    def test_all_success(self) -> None:
        """Test batch with all successes."""
        repo1 = RepoConfig(name="repo1")
        repo2 = RepoConfig(name="repo2")
        result = BatchResult(
            operation=OperationType.BUILD,
            results=[
                RepoResult(repo=repo1, operation=OperationType.BUILD, success=True),
                RepoResult(repo=repo2, operation=OperationType.BUILD, success=True),
            ],
            success=True,
        )
        assert len(result.succeeded) == 2
        assert len(result.failed) == 0

    def test_some_failures(self) -> None:
        """Test batch with some failures."""
        repo1 = RepoConfig(name="repo1")
        repo2 = RepoConfig(name="repo2")
        result = BatchResult(
            operation=OperationType.BUILD,
            results=[
                RepoResult(repo=repo1, operation=OperationType.BUILD, success=True),
                RepoResult(repo=repo2, operation=OperationType.BUILD, success=False),
            ],
            success=False,
        )
        assert len(result.succeeded) == 1
        assert len(result.failed) == 1

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        result = BatchResult(
            operation=OperationType.BUILD,
            success=True,
            total_duration_seconds=10.0,
        )
        data = result.to_dict()
        assert data["operation"] == "build"
        assert data["success"] is True
        assert data["total_duration_seconds"] == 10.0


class TestMultiRepoManager:
    """Tests for MultiRepoManager."""

    def test_init(self) -> None:
        """Test manager initialization."""
        config = MultiRepoConfig()
        manager = MultiRepoManager(config)
        assert manager.config is config

    def test_get_build_order_no_deps(self) -> None:
        """Test build order with no dependencies."""
        config = MultiRepoConfig()
        config.add_repo(RepoConfig(name="repo1"))
        config.add_repo(RepoConfig(name="repo2"))
        config.add_repo(RepoConfig(name="repo3"))
        manager = MultiRepoManager(config)
        order = manager.get_build_order()
        assert len(order) == 3

    def test_get_build_order_with_deps(self) -> None:
        """Test build order respects dependencies."""
        config = MultiRepoConfig()
        config.add_repo(RepoConfig(name="base"))
        config.add_repo(RepoConfig(name="lib", dependencies=["base"]))
        config.add_repo(RepoConfig(name="app", dependencies=["lib"]))
        manager = MultiRepoManager(config)
        order = manager.get_build_order()
        names = [r.name for r in order]
        # base should come before lib, lib before app
        assert names.index("base") < names.index("lib")
        assert names.index("lib") < names.index("app")

    def test_get_build_order_complex_deps(self) -> None:
        """Test build order with complex dependencies."""
        config = MultiRepoConfig()
        config.add_repo(RepoConfig(name="a"))
        config.add_repo(RepoConfig(name="b", dependencies=["a"]))
        config.add_repo(RepoConfig(name="c", dependencies=["a"]))
        config.add_repo(RepoConfig(name="d", dependencies=["b", "c"]))
        manager = MultiRepoManager(config)
        order = manager.get_build_order()
        names = [r.name for r in order]
        assert names.index("a") < names.index("b")
        assert names.index("a") < names.index("c")
        assert names.index("b") < names.index("d")
        assert names.index("c") < names.index("d")

    def test_get_build_order_disabled_repos(self) -> None:
        """Test build order excludes disabled repos."""
        config = MultiRepoConfig()
        config.add_repo(RepoConfig(name="enabled1", enabled=True))
        config.add_repo(RepoConfig(name="disabled", enabled=False))
        config.add_repo(RepoConfig(name="enabled2", enabled=True))
        manager = MultiRepoManager(config)
        order = manager.get_build_order()
        names = [r.name for r in order]
        assert "enabled1" in names
        assert "enabled2" in names
        assert "disabled" not in names

    def test_group_by_level_no_deps(self) -> None:
        """Test grouping with no dependencies."""
        config = MultiRepoConfig()
        repos = [
            RepoConfig(name="a"),
            RepoConfig(name="b"),
            RepoConfig(name="c"),
        ]
        for r in repos:
            config.add_repo(r)
        manager = MultiRepoManager(config)
        levels = manager._group_by_level(repos)
        # All repos at same level (0)
        assert len(levels) == 1
        assert len(levels[0]) == 3

    def test_group_by_level_with_deps(self) -> None:
        """Test grouping with dependencies."""
        config = MultiRepoConfig()
        repos = [
            RepoConfig(name="base"),
            RepoConfig(name="lib1", dependencies=["base"]),
            RepoConfig(name="lib2", dependencies=["base"]),
            RepoConfig(name="app", dependencies=["lib1", "lib2"]),
        ]
        for r in repos:
            config.add_repo(r)
        manager = MultiRepoManager(config)
        levels = manager._group_by_level(repos)
        # Level 0: base
        # Level 1: lib1, lib2
        # Level 2: app
        assert len(levels) == 3
        assert len(levels[0]) == 1  # base
        assert len(levels[1]) == 2  # lib1, lib2
        assert len(levels[2]) == 1  # app


class TestOperationType:
    """Tests for OperationType enum."""

    def test_values(self) -> None:
        """Test operation type values."""
        assert OperationType.BUILD.value == "build"
        assert OperationType.RELEASE.value == "release"
        assert OperationType.TEST.value == "test"
        assert OperationType.SYNC.value == "sync"
