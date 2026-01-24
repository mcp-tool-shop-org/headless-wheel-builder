"""Configuration for multi-repository operations."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RepoConfig:
    """Configuration for a single repository.

    Attributes:
        name: Repository name (owner/repo)
        path: Local path to repository (optional)
        url: Git URL for cloning (optional)
        branch: Default branch name
        python_version: Python version to use for builds
        dependencies: List of repo names this depends on
        build_args: Additional arguments for build
        enabled: Whether this repo is enabled for operations
        tags: Tags for filtering/grouping
    """

    name: str
    path: str | None = None
    url: str | None = None
    branch: str = "main"
    python_version: str = "3.12"
    dependencies: list[str] = field(default_factory=lambda: [])
    build_args: dict[str, Any] = field(default_factory=lambda: {})
    enabled: bool = True
    tags: list[str] = field(default_factory=lambda: [])

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "path": self.path,
            "url": self.url,
            "branch": self.branch,
            "python_version": self.python_version,
            "dependencies": self.dependencies,
            "build_args": self.build_args,
            "enabled": self.enabled,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RepoConfig:
        """Create from dictionary."""
        return cls(
            name=data["name"],
            path=data.get("path"),
            url=data.get("url"),
            branch=data.get("branch", "main"),
            python_version=data.get("python_version", "3.12"),
            dependencies=data.get("dependencies", []),
            build_args=data.get("build_args", {}),
            enabled=data.get("enabled", True),
            tags=data.get("tags", []),
        )


@dataclass
class MultiRepoConfig:
    """Configuration for multi-repository operations.

    Attributes:
        name: Configuration name
        repos: List of repository configurations
        parallel: Maximum parallel operations
        fail_fast: Stop on first failure
        output_dir: Base output directory
        github_token_env: Environment variable for GitHub token
    """

    name: str = "default"
    repos: list[RepoConfig] = field(default_factory=lambda: [])
    parallel: int = 4
    fail_fast: bool = False
    output_dir: str = "dist"
    github_token_env: str = "GITHUB_TOKEN"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "repos": [r.to_dict() for r in self.repos],
            "parallel": self.parallel,
            "fail_fast": self.fail_fast,
            "output_dir": self.output_dir,
            "github_token_env": self.github_token_env,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MultiRepoConfig:
        """Create from dictionary."""
        repos = [RepoConfig.from_dict(r) for r in data.get("repos", [])]
        return cls(
            name=data.get("name", "default"),
            repos=repos,
            parallel=data.get("parallel", 4),
            fail_fast=data.get("fail_fast", False),
            output_dir=data.get("output_dir", "dist"),
            github_token_env=data.get("github_token_env", "GITHUB_TOKEN"),
        )

    def get_repo(self, name: str) -> RepoConfig | None:
        """Get repository by name."""
        for repo in self.repos:
            if repo.name == name:
                return repo
        return None

    def get_enabled_repos(self) -> list[RepoConfig]:
        """Get list of enabled repositories."""
        return [r for r in self.repos if r.enabled]

    def get_repos_by_tag(self, tag: str) -> list[RepoConfig]:
        """Get repositories with a specific tag."""
        return [r for r in self.repos if tag in r.tags]

    def add_repo(self, repo: RepoConfig) -> None:
        """Add a repository configuration."""
        # Check for duplicates
        existing = self.get_repo(repo.name)
        if existing:
            # Replace existing
            self.repos = [r for r in self.repos if r.name != repo.name]
        self.repos.append(repo)

    def remove_repo(self, name: str) -> bool:
        """Remove a repository by name."""
        original_len = len(self.repos)
        self.repos = [r for r in self.repos if r.name != name]
        return len(self.repos) < original_len


def load_config(path: str | Path) -> MultiRepoConfig:
    """Load configuration from file.

    Args:
        path: Path to configuration file (JSON or TOML)

    Returns:
        Loaded configuration
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    content = path.read_text(encoding="utf-8")

    data: dict[str, Any]
    if path.suffix == ".toml":
        try:
            import tomllib

            data = dict(tomllib.loads(content))
        except ImportError:
            try:
                import tomli  # type: ignore[import-not-found,reportUnknownMemberType]

                data = dict(tomli.loads(content))  # type: ignore[reportUnknownMemberType]
            except ImportError:
                raise ImportError("tomllib or tomli required for TOML support")
    else:
        data = json.loads(content)

    return MultiRepoConfig.from_dict(data)


def save_config(config: MultiRepoConfig, path: str | Path) -> None:
    """Save configuration to file.

    Args:
        config: Configuration to save
        path: Path to save to (JSON format)
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = config.to_dict()
    content = json.dumps(data, indent=2)
    path.write_text(content, encoding="utf-8")
