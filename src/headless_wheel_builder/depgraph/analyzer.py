"""Dependency graph analyzer."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import httpx

from headless_wheel_builder.depgraph.models import (
    ConflictInfo,
    DependencyGraph,
    DependencyNode,
    DependencyType,
    LicenseCategory,
    LicenseInfo,
    categorize_license,
)

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class DependencyAnalyzer:
    """Analyzes package dependencies.

    Attributes:
        pypi_url: PyPI JSON API URL
        cache: Cached package metadata
        max_depth: Maximum dependency depth to traverse
    """

    pypi_url: str = "https://pypi.org/pypi"
    cache: dict[str, dict[str, Any]] = field(default_factory=lambda: {})
    max_depth: int = 10
    _client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def fetch_package_info(
        self,
        package: str,
        version: str | None = None,
    ) -> dict[str, Any] | None:
        """Fetch package info from PyPI.

        Args:
            package: Package name
            version: Specific version (or latest if None)

        Returns:
            Package metadata or None
        """
        cache_key = f"{package}=={version}" if version else package
        if cache_key in self.cache:
            return self.cache[cache_key]

        client = await self._get_client()

        try:
            if version:
                url = f"{self.pypi_url}/{package}/{version}/json"
            else:
                url = f"{self.pypi_url}/{package}/json"

            response = await client.get(url)
            if response.status_code == 404:
                return None

            response.raise_for_status()
            data = response.json()
            self.cache[cache_key] = data
            return data

        except httpx.HTTPError:
            return None

    def parse_requirement(self, req: str) -> tuple[str, str, list[str]]:
        """Parse a requirement string.

        Args:
            req: Requirement string (e.g., "requests>=2.0,<3.0")

        Returns:
            Tuple of (name, version_spec, extras)
        """
        # Handle extras: package[extra1,extra2]
        extras: list[str] = []
        if "[" in req:
            match = re.match(r"([^[]+)\[([^\]]+)\](.*)", req)
            if match:
                name_part = match.group(1)
                extras = [e.strip() for e in match.group(2).split(",")]
                version_part = match.group(3)
                req = name_part + version_part

        # Split on version specifiers
        match = re.match(r"([a-zA-Z0-9_-]+)(.*)", req.strip())
        if match:
            name = match.group(1)
            version_spec = match.group(2).strip()
            # Remove markers
            if ";" in version_spec:
                version_spec = version_spec.split(";")[0].strip()
            return (name.lower().replace("_", "-"), version_spec, extras)

        return (req.strip().lower().replace("_", "-"), "", extras)

    async def build_graph(
        self,
        package: str,
        version: str | None = None,
        include_dev: bool = False,
    ) -> DependencyGraph:
        """Build dependency graph for a package.

        Args:
            package: Root package name
            version: Specific version (or latest)
            include_dev: Include development dependencies

        Returns:
            Complete dependency graph
        """
        graph = DependencyGraph(root=package)

        # Fetch root package info
        info = await self.fetch_package_info(package, version)
        if not info:
            # Create minimal node for unknown package
            graph.add_node(
                DependencyNode(
                    name=package,
                    version=version or "unknown",
                    dep_type=DependencyType.DIRECT,
                )
            )
            return graph

        pkg_info = info.get("info", {})
        root_version = pkg_info.get("version", version or "unknown")

        # Create root node
        license_name = pkg_info.get("license") or ""
        root_node = DependencyNode(
            name=package,
            version=root_version,
            dep_type=DependencyType.DIRECT,
            license_info=LicenseInfo(
                name=license_name,
                category=categorize_license(license_name),
            )
            if license_name
            else None,
            source=pkg_info.get("home_page", ""),
        )
        graph.add_node(root_node)

        # Build dependency tree
        await self._resolve_dependencies(
            graph=graph,
            package=package,
            version=root_version,
            depth=0,
            visited=set(),
        )

        # Analyze for issues
        self._detect_cycles(graph)
        self._detect_conflicts(graph)
        self._check_licenses(graph)
        self._compute_build_order(graph)

        return graph

    async def _resolve_dependencies(
        self,
        graph: DependencyGraph,
        package: str,
        version: str,
        depth: int,
        visited: set[str],
    ) -> None:
        """Recursively resolve dependencies.

        Args:
            graph: Graph to populate
            package: Current package
            version: Current version
            depth: Current depth
            visited: Already visited packages
        """
        if depth >= self.max_depth:
            return

        cache_key = f"{package}=={version}"
        if cache_key in visited:
            return
        visited.add(cache_key)

        info = await self.fetch_package_info(package, version)
        if not info:
            return

        pkg_info = info.get("info", {})
        requires_dist: list[str] = pkg_info.get("requires_dist") or []

        for req in requires_dist:
            # Skip extras and markers we don't want
            if "extra ==" in req:
                continue

            name, _version_spec, extras = self.parse_requirement(req)

            # Skip if already in graph with this version
            if name in graph.nodes:
                # Just add edge
                graph.add_edge(package, name)
                continue

            # Fetch dependency info
            dep_info = await self.fetch_package_info(name)
            if not dep_info:
                # Add placeholder node
                dep_node = DependencyNode(
                    name=name,
                    version="unknown",
                    dep_type=DependencyType.TRANSITIVE,
                )
                graph.add_node(dep_node)
                graph.add_edge(package, name)
                continue

            dep_pkg_info = dep_info.get("info", {})
            dep_version = dep_pkg_info.get("version", "unknown")
            dep_license = dep_pkg_info.get("license") or ""

            dep_node = DependencyNode(
                name=name,
                version=dep_version,
                dep_type=DependencyType.TRANSITIVE,
                license_info=LicenseInfo(
                    name=dep_license,
                    category=categorize_license(dep_license),
                )
                if dep_license
                else None,
                extras=extras,
                source=dep_pkg_info.get("home_page", ""),
            )
            graph.add_node(dep_node)
            graph.add_edge(package, name)

            # Recurse
            await self._resolve_dependencies(
                graph=graph,
                package=name,
                version=dep_version,
                depth=depth + 1,
                visited=visited,
            )

    def _detect_cycles(self, graph: DependencyGraph) -> None:
        """Detect circular dependencies.

        Args:
            graph: Graph to analyze
        """
        visited: set[str] = set()
        rec_stack: set[str] = set()
        cycles: list[list[str]] = []

        def dfs(node: str, path: list[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.edges.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path.copy())
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = [*path[cycle_start:], neighbor]
                    cycles.append(cycle)

            rec_stack.remove(node)

        for node in graph.nodes:
            if node not in visited:
                dfs(node, [])

        graph.cycles = cycles

    def _detect_conflicts(self, graph: DependencyGraph) -> None:
        """Detect version conflicts.

        Args:
            graph: Graph to analyze
        """
        # Group requirements by package
        requirements: dict[str, dict[str, str]] = {}

        for source, targets in graph.edges.items():
            for target in targets:
                target_node = graph.nodes.get(target)
                if target_node:
                    if target not in requirements:
                        requirements[target] = {}
                    requirements[target][source] = target_node.version

        # Check for conflicts (different versions required)
        for package, versions in requirements.items():
            unique_versions = set(versions.values())
            if len(unique_versions) > 1:
                graph.conflicts.append(
                    ConflictInfo(
                        package=package,
                        required_versions=versions,
                        message=f"Multiple versions required: {unique_versions}",
                    )
                )

    def _check_licenses(self, graph: DependencyGraph) -> None:
        """Check for license compatibility issues.

        Args:
            graph: Graph to analyze
        """
        issues: list[str] = []

        root_node = graph.nodes.get(graph.root)
        root_license = root_node.license_info if root_node else None

        for name, node in graph.nodes.items():
            if name == graph.root:
                continue

            if not node.license_info:
                issues.append(f"{name}: Unknown license")
                continue

            # Check for copyleft in permissive projects
            if root_license and root_license.category == LicenseCategory.PERMISSIVE:
                if node.license_info.category == LicenseCategory.COPYLEFT:
                    issues.append(f"{name}: GPL-licensed dependency in permissive project")

        graph.license_issues = issues

    def _compute_build_order(self, graph: DependencyGraph) -> None:
        """Compute topological build order.

        Args:
            graph: Graph to populate build order
        """
        # Kahn's algorithm for topological sort
        in_degree: dict[str, int] = dict.fromkeys(graph.nodes, 0)

        for targets in graph.edges.values():
            for target in targets:
                if target in in_degree:
                    in_degree[target] += 1

        # Start with nodes that have no incoming edges
        queue = [node for node, degree in in_degree.items() if degree == 0]
        order: list[str] = []

        while queue:
            node = queue.pop(0)
            order.append(node)

            for neighbor in graph.edges.get(node, []):
                if neighbor in in_degree:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

        # Reverse to get build order (dependencies first)
        graph.build_order = list(reversed(order))

    async def analyze_local(self, project_path: Path) -> DependencyGraph:
        """Analyze dependencies of a local project.

        Args:
            project_path: Path to project directory

        Returns:
            Dependency graph
        """
        # Try to read pyproject.toml
        pyproject = project_path / "pyproject.toml"
        if pyproject.exists():
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib  # type: ignore

            content = pyproject.read_text(encoding="utf-8")
            data = tomllib.loads(content)

            project_name = data.get("project", {}).get("name", project_path.name)
            project_version = data.get("project", {}).get("version", "0.0.0")
            dependencies = data.get("project", {}).get("dependencies", [])

            graph = DependencyGraph(root=project_name)

            # Create root node
            graph.add_node(
                DependencyNode(
                    name=project_name,
                    version=project_version,
                    dep_type=DependencyType.DIRECT,
                    source=str(project_path),
                )
            )

            # Process dependencies
            for dep in dependencies:
                name, _version_spec, extras = self.parse_requirement(dep)

                # Fetch from PyPI
                info = await self.fetch_package_info(name)
                dep_version = "unknown"
                if info:
                    pkg_info = info.get("info", {})
                    dep_version = pkg_info.get("version", "unknown")
                    dep_license = pkg_info.get("license") or ""

                    graph.add_node(
                        DependencyNode(
                            name=name,
                            version=dep_version,
                            dep_type=DependencyType.DIRECT,
                            license_info=LicenseInfo(
                                name=dep_license,
                                category=categorize_license(dep_license),
                            )
                            if dep_license
                            else None,
                            extras=extras,
                        )
                    )

                    graph.add_edge(project_name, name)

                    # Resolve transitive dependencies
                    await self._resolve_dependencies(
                        graph=graph,
                        package=name,
                        version=dep_version,
                        depth=1,
                        visited={f"{project_name}=={project_version}"},
                    )
                else:
                    graph.add_node(
                        DependencyNode(
                            name=name,
                            dep_type=DependencyType.DIRECT,
                        )
                    )
                    graph.add_edge(project_name, name)

            # Analyze
            self._detect_cycles(graph)
            self._detect_conflicts(graph)
            self._check_licenses(graph)
            self._compute_build_order(graph)

            return graph

        # Fall back to requirements.txt
        requirements = project_path / "requirements.txt"
        if requirements.exists():
            return await self._analyze_requirements(project_path, requirements)

        raise ValueError(f"No pyproject.toml or requirements.txt found in {project_path}")

    async def _analyze_requirements(
        self,
        project_path: Path,
        requirements_file: Path,
    ) -> DependencyGraph:
        """Analyze a requirements.txt file.

        Args:
            project_path: Project path
            requirements_file: Path to requirements.txt

        Returns:
            Dependency graph
        """
        graph = DependencyGraph(root=project_path.name)

        # Create root node
        graph.add_node(
            DependencyNode(
                name=project_path.name,
                dep_type=DependencyType.DIRECT,
                source=str(project_path),
            )
        )

        # Parse requirements
        content = requirements_file.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue

            name, _version_spec, extras = self.parse_requirement(line)

            info = await self.fetch_package_info(name)
            if info:
                pkg_info = info.get("info", {})
                version = pkg_info.get("version", "unknown")
                license_name = pkg_info.get("license") or ""

                graph.add_node(
                    DependencyNode(
                        name=name,
                        version=version,
                        dep_type=DependencyType.DIRECT,
                        license_info=LicenseInfo(
                            name=license_name,
                            category=categorize_license(license_name),
                        )
                        if license_name
                        else None,
                        extras=extras,
                    )
                )
            else:
                graph.add_node(
                    DependencyNode(
                        name=name,
                        dep_type=DependencyType.DIRECT,
                    )
                )

            graph.add_edge(project_path.name, name)

        # Analyze
        self._detect_cycles(graph)
        self._detect_conflicts(graph)
        self._check_licenses(graph)
        self._compute_build_order(graph)

        return graph
