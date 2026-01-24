"""Multi-repository manager for coordinated operations."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from headless_wheel_builder.core.builder import BuildConfig, BuildEngine, BuildResult
from headless_wheel_builder.exceptions import HWBError

if TYPE_CHECKING:
    from headless_wheel_builder.multirepo.config import MultiRepoConfig, RepoConfig


class OperationType(Enum):
    """Types of multi-repo operations."""

    BUILD = "build"
    RELEASE = "release"
    TEST = "test"
    SYNC = "sync"


@dataclass
class RepoResult:
    """Result for a single repository operation.

    Attributes:
        repo: Repository configuration
        operation: Type of operation performed
        success: Whether the operation succeeded
        message: Status message
        build_result: Build result if applicable
        duration_seconds: Operation duration
        error: Error message if failed
    """

    repo: RepoConfig
    operation: OperationType
    success: bool
    message: str = ""
    build_result: BuildResult | None = None
    duration_seconds: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "repo": self.repo.name,
            "operation": self.operation.value,
            "success": self.success,
            "message": self.message,
            "duration_seconds": self.duration_seconds,
        }
        if self.error:
            result["error"] = self.error
        if self.build_result:
            result["wheel_path"] = (
                str(self.build_result.wheel_path) if self.build_result.wheel_path else None
            )
        return result


@dataclass
class BatchResult:
    """Result for a batch operation across repositories.

    Attributes:
        operation: Type of operation performed
        results: Results for each repository
        success: Whether all operations succeeded
        total_duration_seconds: Total time for all operations
    """

    operation: OperationType
    results: list[RepoResult] = field(default_factory=lambda: [])
    success: bool = True
    total_duration_seconds: float = 0.0

    @property
    def succeeded(self) -> list[RepoResult]:
        """Get successful results."""
        return [r for r in self.results if r.success]

    @property
    def failed(self) -> list[RepoResult]:
        """Get failed results."""
        return [r for r in self.results if not r.success]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "operation": self.operation.value,
            "success": self.success,
            "total_duration_seconds": self.total_duration_seconds,
            "succeeded_count": len(self.succeeded),
            "failed_count": len(self.failed),
            "results": [r.to_dict() for r in self.results],
        }


class MultiRepoManager:
    """Manager for multi-repository operations.

    Provides coordinated operations across multiple repositories
    with dependency resolution and parallel execution.
    """

    def __init__(self, config: MultiRepoConfig) -> None:
        """Initialize manager.

        Args:
            config: Multi-repository configuration
        """
        self.config = config
        self._semaphore: asyncio.Semaphore | None = None

    def _get_semaphore(self) -> asyncio.Semaphore:
        """Get or create semaphore for parallel execution."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.config.parallel)
        return self._semaphore

    def _resolve_order(self, repos: list[RepoConfig]) -> list[RepoConfig]:
        """Resolve repository order based on dependencies.

        Uses topological sort to ensure dependencies are processed first.

        Args:
            repos: List of repositories to order

        Returns:
            Ordered list of repositories
        """
        # Build dependency graph
        repo_names = {r.name for r in repos}
        graph: dict[str, set[str]] = {}
        for repo in repos:
            # Only include dependencies that are in our repo list
            deps = {d for d in repo.dependencies if d in repo_names}
            graph[repo.name] = deps

        # Topological sort (Kahn's algorithm)
        in_degree: dict[str, int] = dict.fromkeys(graph, 0)
        for deps in graph.values():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1

        # Start with nodes that have no dependencies pointing to them
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result_order: list[str] = []

        while queue:
            name = queue.pop(0)
            result_order.append(name)

            for deps in graph.values():
                if name in deps:
                    # This was a dependency, find who depends on it
                    pass

            # Find repos that depend on this one
            for other_name, deps in graph.items():
                if name in deps:
                    in_degree[other_name] -= 1
                    if in_degree[other_name] == 0:
                        queue.append(other_name)

        # Check for cycles
        if len(result_order) != len(repos):
            # Cycle detected, fall back to original order
            return repos

        # Map back to RepoConfig objects
        name_to_repo = {r.name: r for r in repos}
        return [name_to_repo[name] for name in result_order]

    async def build_all(
        self,
        repos: list[RepoConfig] | None = None,
        *,
        parallel: bool = True,
    ) -> BatchResult:
        """Build all repositories.

        Args:
            repos: Specific repos to build (default: all enabled)
            parallel: Whether to build in parallel

        Returns:
            Batch result with all build results
        """
        import time

        start_time = time.time()

        if repos is None:
            repos = self.config.get_enabled_repos()

        # Resolve order based on dependencies
        ordered = self._resolve_order(repos)

        batch = BatchResult(operation=OperationType.BUILD)

        if parallel:
            # Group by dependency level for parallel execution
            levels = self._group_by_level(ordered)
            for level in levels:
                results = await asyncio.gather(
                    *[self._build_repo(repo) for repo in level],
                    return_exceptions=True,
                )
                for i, result in enumerate(results):
                    if isinstance(result, BaseException):
                        batch.results.append(
                            RepoResult(
                                repo=level[i],
                                operation=OperationType.BUILD,
                                success=False,
                                error=str(result),
                            )
                        )
                        if self.config.fail_fast:
                            batch.success = False
                            batch.total_duration_seconds = time.time() - start_time
                            return batch
                    else:
                        batch.results.append(result)
                        if not result.success and self.config.fail_fast:
                            batch.success = False
                            batch.total_duration_seconds = time.time() - start_time
                            return batch
        else:
            for repo in ordered:
                result = await self._build_repo(repo)
                batch.results.append(result)
                if not result.success and self.config.fail_fast:
                    break

        batch.success = all(r.success for r in batch.results)
        batch.total_duration_seconds = time.time() - start_time

        return batch

    def _group_by_level(self, repos: list[RepoConfig]) -> list[list[RepoConfig]]:
        """Group repositories by dependency level.

        Repos at the same level can be processed in parallel.

        Args:
            repos: Ordered list of repositories

        Returns:
            List of levels, each containing repos that can run in parallel
        """
        repo_names = {r.name for r in repos}
        name_to_repo = {r.name: r for r in repos}

        # Calculate level for each repo
        levels_map: dict[str, int] = {}

        def get_level(name: str) -> int:
            if name in levels_map:
                return levels_map[name]

            repo = name_to_repo.get(name)
            if repo is None:
                return 0

            deps = [d for d in repo.dependencies if d in repo_names]
            if not deps:
                levels_map[name] = 0
            else:
                levels_map[name] = max(get_level(d) for d in deps) + 1

            return levels_map[name]

        for repo in repos:
            get_level(repo.name)

        # Group by level
        max_level = max(levels_map.values()) if levels_map else 0
        grouped: list[list[RepoConfig]] = [[] for _ in range(max_level + 1)]

        for repo in repos:
            level = levels_map.get(repo.name, 0)
            grouped[level].append(repo)

        return grouped

    async def _build_repo(self, repo: RepoConfig) -> RepoResult:
        """Build a single repository.

        Args:
            repo: Repository configuration

        Returns:
            Repository result
        """
        import time

        start_time = time.time()

        async with self._get_semaphore():
            try:
                # Determine source
                source: str
                if repo.path:
                    source = repo.path
                elif repo.url:
                    source = repo.url
                else:
                    # Use GitHub URL from name
                    source = f"https://github.com/{repo.name}"

                # Create build config
                output_dir = Path(self.config.output_dir) / repo.name.replace("/", "_")
                config = BuildConfig(
                    output_dir=output_dir,
                    python_version=repo.python_version,
                    **repo.build_args,
                )

                engine = BuildEngine(config)
                result = await engine.build(source=source)

                duration = time.time() - start_time

                return RepoResult(
                    repo=repo,
                    operation=OperationType.BUILD,
                    success=result.success,
                    message=f"Built {result.name} {result.version}"
                    if result.success
                    else "Build failed",
                    build_result=result,
                    duration_seconds=duration,
                    error=result.error if not result.success else None,
                )

            except HWBError as e:
                return RepoResult(
                    repo=repo,
                    operation=OperationType.BUILD,
                    success=False,
                    message="Build failed",
                    duration_seconds=time.time() - start_time,
                    error=str(e),
                )

            except Exception as e:
                return RepoResult(
                    repo=repo,
                    operation=OperationType.BUILD,
                    success=False,
                    message="Unexpected error",
                    duration_seconds=time.time() - start_time,
                    error=str(e),
                )

    async def sync_all(
        self,
        repos: list[RepoConfig] | None = None,
    ) -> BatchResult:
        """Sync all repositories (clone/pull).

        Args:
            repos: Specific repos to sync (default: all enabled)

        Returns:
            Batch result with sync results
        """
        import time

        start_time = time.time()

        if repos is None:
            repos = self.config.get_enabled_repos()

        batch = BatchResult(operation=OperationType.SYNC)

        results = await asyncio.gather(
            *[self._sync_repo(repo) for repo in repos],
            return_exceptions=True,
        )

        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                batch.results.append(
                    RepoResult(
                        repo=repos[i],
                        operation=OperationType.SYNC,
                        success=False,
                        error=str(result),
                    )
                )
            else:
                batch.results.append(result)

        batch.success = all(r.success for r in batch.results)
        batch.total_duration_seconds = time.time() - start_time

        return batch

    async def _sync_repo(self, repo: RepoConfig) -> RepoResult:
        """Sync a single repository.

        Args:
            repo: Repository configuration

        Returns:
            Repository result
        """
        import time

        start_time = time.time()

        async with self._get_semaphore():
            try:
                if repo.path:
                    path = Path(repo.path)
                    if path.exists():
                        # Pull existing repo
                        process = await asyncio.create_subprocess_exec(
                            "git",
                            "pull",
                            cwd=str(path),
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        _stdout, stderr = await process.communicate()

                        if process.returncode != 0:
                            return RepoResult(
                                repo=repo,
                                operation=OperationType.SYNC,
                                success=False,
                                message="Pull failed",
                                duration_seconds=time.time() - start_time,
                                error=stderr.decode() if stderr else "Unknown error",
                            )

                        return RepoResult(
                            repo=repo,
                            operation=OperationType.SYNC,
                            success=True,
                            message="Pulled latest changes",
                            duration_seconds=time.time() - start_time,
                        )

                    elif repo.url:
                        # Clone
                        path.parent.mkdir(parents=True, exist_ok=True)
                        process = await asyncio.create_subprocess_exec(
                            "git",
                            "clone",
                            repo.url,
                            str(path),
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        _stdout, stderr = await process.communicate()

                        if process.returncode != 0:
                            return RepoResult(
                                repo=repo,
                                operation=OperationType.SYNC,
                                success=False,
                                message="Clone failed",
                                duration_seconds=time.time() - start_time,
                                error=stderr.decode() if stderr else "Unknown error",
                            )

                        return RepoResult(
                            repo=repo,
                            operation=OperationType.SYNC,
                            success=True,
                            message="Cloned repository",
                            duration_seconds=time.time() - start_time,
                        )

                    else:
                        return RepoResult(
                            repo=repo,
                            operation=OperationType.SYNC,
                            success=False,
                            message="No URL provided for cloning",
                            duration_seconds=time.time() - start_time,
                            error="Repository path does not exist and no URL provided",
                        )

                else:
                    return RepoResult(
                        repo=repo,
                        operation=OperationType.SYNC,
                        success=False,
                        message="No path specified",
                        duration_seconds=time.time() - start_time,
                        error="Repository must have a path for sync operations",
                    )

            except Exception as e:
                return RepoResult(
                    repo=repo,
                    operation=OperationType.SYNC,
                    success=False,
                    message="Sync failed",
                    duration_seconds=time.time() - start_time,
                    error=str(e),
                )

    def get_build_order(self) -> list[RepoConfig]:
        """Get the build order respecting dependencies.

        Returns:
            Ordered list of repositories
        """
        repos = self.config.get_enabled_repos()
        return self._resolve_order(repos)
