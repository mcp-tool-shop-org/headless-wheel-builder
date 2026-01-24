"""Dependency resolver for finding compatible versions."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field

from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

from headless_wheel_builder.depgraph.models import (
    ConflictInfo,
    DependencyGraph,
)


@dataclass
class VersionConstraint:
    """A version constraint from a dependency.

    Attributes:
        source: Package requiring this constraint
        specifier: Version specifier (e.g., ">=2.0,<3.0")
        extras: Requested extras
        markers: Environment markers
    """

    source: str
    specifier: str = ""
    extras: list[str] = field(default_factory=lambda: [])
    markers: str = ""


@dataclass
class ResolvedPackage:
    """A resolved package with version.

    Attributes:
        name: Package name
        version: Resolved version
        constraints: All constraints that were satisfied
        available_versions: All available versions
    """

    name: str
    version: str
    constraints: list[VersionConstraint] = field(default_factory=lambda: [])
    available_versions: list[str] = field(default_factory=lambda: [])


class DependencyResolver:
    """Resolves dependency versions to find compatible combinations.

    Uses a constraint satisfaction approach to find versions that
    satisfy all requirements.
    """

    def __init__(self) -> None:
        """Initialize resolver."""
        self.constraints: dict[str, list[VersionConstraint]] = {}
        self.available: dict[str, list[str]] = {}
        self.resolved: dict[str, str] = {}

    def add_constraint(
        self,
        package: str,
        specifier: str,
        source: str,
        extras: list[str] | None = None,
        markers: str = "",
    ) -> None:
        """Add a version constraint.

        Args:
            package: Package name
            specifier: Version specifier
            source: Package requiring this constraint
            extras: Requested extras
            markers: Environment markers
        """
        if package not in self.constraints:
            self.constraints[package] = []

        self.constraints[package].append(
            VersionConstraint(
                source=source,
                specifier=specifier,
                extras=extras or [],
                markers=markers,
            )
        )

    def set_available_versions(
        self,
        package: str,
        versions: list[str],
    ) -> None:
        """Set available versions for a package.

        Args:
            package: Package name
            versions: List of available versions
        """
        self.available[package] = versions

    def _parse_versions(self, versions: list[str]) -> list[Version]:
        """Parse version strings to Version objects.

        Args:
            versions: Version strings

        Returns:
            Sorted list of Version objects (newest first)
        """
        parsed: list[Version] = []
        for v in versions:
            try:
                parsed.append(Version(v))
            except InvalidVersion:
                continue

        return sorted(parsed, reverse=True)

    def _version_satisfies(
        self,
        version: Version,
        constraints: list[VersionConstraint],
    ) -> bool:
        """Check if a version satisfies all constraints.

        Args:
            version: Version to check
            constraints: Constraints to satisfy

        Returns:
            True if all constraints are satisfied
        """
        for constraint in constraints:
            if not constraint.specifier:
                continue

            try:
                spec = SpecifierSet(constraint.specifier)
                if version not in spec:
                    return False
            except Exception:
                # If we can't parse the specifier, skip it
                continue

        return True

    def resolve(self, package: str) -> ResolvedPackage | None:
        """Resolve a single package.

        Args:
            package: Package name

        Returns:
            Resolved package or None if no resolution found
        """
        if package in self.resolved:
            return ResolvedPackage(
                name=package,
                version=self.resolved[package],
                constraints=self.constraints.get(package, []),
            )

        constraints = self.constraints.get(package, [])
        available = self.available.get(package, [])

        if not available:
            return None

        # Parse and sort versions
        versions = self._parse_versions(available)

        # Find first version that satisfies all constraints
        for version in versions:
            if self._version_satisfies(version, constraints):
                self.resolved[package] = str(version)
                return ResolvedPackage(
                    name=package,
                    version=str(version),
                    constraints=constraints,
                    available_versions=available,
                )

        return None

    def resolve_all(self) -> tuple[dict[str, str], list[ConflictInfo]]:
        """Resolve all packages.

        Returns:
            Tuple of (resolved versions, conflicts)
        """
        resolved: dict[str, str] = {}
        conflicts: list[ConflictInfo] = []

        for package in self.constraints:
            result = self.resolve(package)
            if result:
                resolved[package] = result.version
            else:
                # Collect conflict info
                constraints = self.constraints.get(package, [])
                required_versions = {c.source: c.specifier for c in constraints}
                conflicts.append(
                    ConflictInfo(
                        package=package,
                        required_versions=required_versions,
                        is_resolvable=False,
                        message="No version satisfies all constraints",
                    )
                )

        return resolved, conflicts

    def find_conflicts(self) -> list[ConflictInfo]:
        """Find version conflicts without resolving.

        Returns:
            List of conflicts
        """
        conflicts: list[ConflictInfo] = []

        for package, constraints in self.constraints.items():
            if len(constraints) < 2:
                continue

            # Check if constraints are compatible
            specs: list[SpecifierSet] = []
            for c in constraints:
                if c.specifier:
                    with contextlib.suppress(Exception):
                        specs.append(SpecifierSet(c.specifier))

            if len(specs) < 2:
                continue

            # Try to find a version that satisfies all
            available = self.available.get(package, [])
            versions = self._parse_versions(available)

            found = False
            for version in versions:
                if all(version in spec for spec in specs):
                    found = True
                    break

            if not found and available:
                required_versions = {c.source: c.specifier for c in constraints}
                conflicts.append(
                    ConflictInfo(
                        package=package,
                        required_versions=required_versions,
                        is_resolvable=False,
                        message="Conflicting version requirements",
                    )
                )

        return conflicts

    @classmethod
    def from_graph(cls, graph: DependencyGraph) -> DependencyResolver:
        """Create resolver from a dependency graph.

        Args:
            graph: Dependency graph

        Returns:
            Configured resolver
        """
        resolver = cls()

        # Extract constraints from graph
        for source, targets in graph.edges.items():
            _source_node = graph.nodes.get(source)
            for target in targets:
                target_node = graph.nodes.get(target)
                if target_node:
                    # Add constraint
                    resolver.add_constraint(
                        package=target,
                        specifier=f"=={target_node.version}" if target_node.version else "",
                        source=source,
                        extras=target_node.extras,
                    )

                    # Add available version (just the one we know about)
                    if target_node.version:
                        resolver.set_available_versions(
                            target,
                            [target_node.version],
                        )

        return resolver


def find_minimal_upgrade(
    current: dict[str, str],
    target: dict[str, str],
) -> dict[str, tuple[str, str]]:
    """Find minimal version changes to satisfy target.

    Args:
        current: Current package versions
        target: Target package versions

    Returns:
        Dict of package -> (old_version, new_version)
    """
    changes: dict[str, tuple[str, str]] = {}

    for package, new_version in target.items():
        old_version = current.get(package, "")
        if old_version != new_version:
            changes[package] = (old_version, new_version)

    return changes
