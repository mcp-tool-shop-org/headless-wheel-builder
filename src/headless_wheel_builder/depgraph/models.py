"""Models for dependency graph analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DependencyType(Enum):
    """Type of dependency."""

    DIRECT = "direct"
    TRANSITIVE = "transitive"
    DEV = "dev"
    OPTIONAL = "optional"


class LicenseCategory(Enum):
    """License category for compliance checking."""

    PERMISSIVE = "permissive"  # MIT, BSD, Apache
    COPYLEFT = "copyleft"  # GPL, LGPL
    WEAK_COPYLEFT = "weak_copyleft"  # MPL, LGPL
    PROPRIETARY = "proprietary"
    UNKNOWN = "unknown"


@dataclass
class LicenseInfo:
    """License information for a package.

    Attributes:
        name: License name (e.g., "MIT", "Apache-2.0")
        category: License category
        url: URL to license text
        compatible_with: List of compatible licenses
    """

    name: str
    category: LicenseCategory = LicenseCategory.UNKNOWN
    url: str = ""
    compatible_with: list[str] = field(default_factory=lambda: [])

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "category": self.category.value,
            "url": self.url,
            "compatible_with": self.compatible_with,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LicenseInfo:
        """Create from dictionary."""
        return cls(
            name=data["name"],
            category=LicenseCategory(data.get("category", "unknown")),
            url=data.get("url", ""),
            compatible_with=data.get("compatible_with", []),
        )


# Common license mappings
LICENSE_CATEGORIES: dict[str, LicenseCategory] = {
    "MIT": LicenseCategory.PERMISSIVE,
    "MIT License": LicenseCategory.PERMISSIVE,
    "BSD": LicenseCategory.PERMISSIVE,
    "BSD-2-Clause": LicenseCategory.PERMISSIVE,
    "BSD-3-Clause": LicenseCategory.PERMISSIVE,
    "Apache-2.0": LicenseCategory.PERMISSIVE,
    "Apache License 2.0": LicenseCategory.PERMISSIVE,
    "Apache Software License": LicenseCategory.PERMISSIVE,
    "ISC": LicenseCategory.PERMISSIVE,
    "PSF": LicenseCategory.PERMISSIVE,
    "Python Software Foundation License": LicenseCategory.PERMISSIVE,
    "GPL": LicenseCategory.COPYLEFT,
    "GPL-2.0": LicenseCategory.COPYLEFT,
    "GPL-3.0": LicenseCategory.COPYLEFT,
    "GPLv2": LicenseCategory.COPYLEFT,
    "GPLv3": LicenseCategory.COPYLEFT,
    "LGPL": LicenseCategory.WEAK_COPYLEFT,
    "LGPL-2.1": LicenseCategory.WEAK_COPYLEFT,
    "LGPL-3.0": LicenseCategory.WEAK_COPYLEFT,
    "MPL": LicenseCategory.WEAK_COPYLEFT,
    "MPL-2.0": LicenseCategory.WEAK_COPYLEFT,
    "Mozilla Public License 2.0": LicenseCategory.WEAK_COPYLEFT,
    "Unlicense": LicenseCategory.PERMISSIVE,
    "Public Domain": LicenseCategory.PERMISSIVE,
    "WTFPL": LicenseCategory.PERMISSIVE,
}


def categorize_license(license_name: str) -> LicenseCategory:
    """Categorize a license by name.

    Args:
        license_name: License name

    Returns:
        License category
    """
    # Check exact match first
    if license_name in LICENSE_CATEGORIES:
        return LICENSE_CATEGORIES[license_name]

    # Check partial matches
    license_upper = license_name.upper()
    if "MIT" in license_upper:
        return LicenseCategory.PERMISSIVE
    if "BSD" in license_upper:
        return LicenseCategory.PERMISSIVE
    if "APACHE" in license_upper:
        return LicenseCategory.PERMISSIVE
    if "GPL" in license_upper and "LGPL" not in license_upper:
        return LicenseCategory.COPYLEFT
    if "LGPL" in license_upper:
        return LicenseCategory.WEAK_COPYLEFT
    if "MPL" in license_upper or "MOZILLA" in license_upper:
        return LicenseCategory.WEAK_COPYLEFT

    return LicenseCategory.UNKNOWN


@dataclass
class DependencyNode:
    """A node in the dependency graph.

    Attributes:
        name: Package name
        version: Package version
        dep_type: Dependency type (direct, transitive, etc.)
        license_info: License information
        dependencies: Direct dependencies
        dependents: Packages that depend on this
        extras: Requested extras
        markers: Environment markers
        source: Source URL or path
        metadata: Additional metadata
    """

    name: str
    version: str = ""
    dep_type: DependencyType = DependencyType.DIRECT
    license_info: LicenseInfo | None = None
    dependencies: list[str] = field(default_factory=lambda: [])
    dependents: list[str] = field(default_factory=lambda: [])
    extras: list[str] = field(default_factory=lambda: [])
    markers: str = ""
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=lambda: {})

    @property
    def key(self) -> str:
        """Get unique key for this node."""
        return f"{self.name}=={self.version}" if self.version else self.name

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "dep_type": self.dep_type.value,
            "license_info": self.license_info.to_dict() if self.license_info else None,
            "dependencies": self.dependencies,
            "dependents": self.dependents,
            "extras": self.extras,
            "markers": self.markers,
            "source": self.source,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DependencyNode:
        """Create from dictionary."""
        license_data = data.get("license_info")
        return cls(
            name=data["name"],
            version=data.get("version", ""),
            dep_type=DependencyType(data.get("dep_type", "direct")),
            license_info=LicenseInfo.from_dict(license_data) if license_data else None,
            dependencies=data.get("dependencies", []),
            dependents=data.get("dependents", []),
            extras=data.get("extras", []),
            markers=data.get("markers", ""),
            source=data.get("source", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ConflictInfo:
    """Information about a version conflict.

    Attributes:
        package: Package name with conflict
        required_versions: Map of requirer -> required version
        resolved_version: Resolved version (if any)
        is_resolvable: Whether conflict can be resolved
        message: Human-readable conflict description
    """

    package: str
    required_versions: dict[str, str] = field(default_factory=lambda: {})
    resolved_version: str = ""
    is_resolvable: bool = False
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "package": self.package,
            "required_versions": self.required_versions,
            "resolved_version": self.resolved_version,
            "is_resolvable": self.is_resolvable,
            "message": self.message,
        }


@dataclass
class DependencyGraph:
    """Complete dependency graph.

    Attributes:
        root: Root package name
        nodes: All dependency nodes
        edges: Dependency edges (source -> list of targets)
        cycles: Detected circular dependencies
        conflicts: Version conflicts
        license_issues: License compatibility issues
        build_order: Topological build order
    """

    root: str
    nodes: dict[str, DependencyNode] = field(default_factory=lambda: {})
    edges: dict[str, list[str]] = field(default_factory=lambda: {})
    cycles: list[list[str]] = field(default_factory=lambda: [])
    conflicts: list[ConflictInfo] = field(default_factory=lambda: [])
    license_issues: list[str] = field(default_factory=lambda: [])
    build_order: list[str] = field(default_factory=lambda: [])

    def add_node(self, node: DependencyNode) -> None:
        """Add a node to the graph.

        Args:
            node: Dependency node to add
        """
        self.nodes[node.name] = node
        if node.name not in self.edges:
            self.edges[node.name] = []

    def add_edge(self, source: str, target: str) -> None:
        """Add an edge between nodes.

        Args:
            source: Source node name
            target: Target node name
        """
        if source not in self.edges:
            self.edges[source] = []
        if target not in self.edges[source]:
            self.edges[source].append(target)

    def get_node(self, name: str) -> DependencyNode | None:
        """Get a node by name.

        Args:
            name: Package name

        Returns:
            Dependency node or None
        """
        return self.nodes.get(name)

    def get_dependencies(self, name: str) -> list[str]:
        """Get direct dependencies of a node.

        Args:
            name: Package name

        Returns:
            List of dependency names
        """
        return self.edges.get(name, [])

    def get_dependents(self, name: str) -> list[str]:
        """Get packages that depend on a node.

        Args:
            name: Package name

        Returns:
            List of dependent names
        """
        dependents: list[str] = []
        for source, targets in self.edges.items():
            if name in targets:
                dependents.append(source)
        return dependents

    def depth_first_traverse(
        self,
        start: str | None = None,
        visited: set[str] | None = None,
    ) -> list[str]:
        """Traverse the graph depth-first.

        Args:
            start: Starting node (default: root)
            visited: Already visited nodes

        Returns:
            List of node names in traversal order
        """
        if start is None:
            start = self.root
        if visited is None:
            visited = set()

        result: list[str] = []
        if start in visited:
            return result

        visited.add(start)
        result.append(start)

        for dep in self.edges.get(start, []):
            result.extend(self.depth_first_traverse(dep, visited))

        return result

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "root": self.root,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "edges": self.edges,
            "cycles": self.cycles,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "license_issues": self.license_issues,
            "build_order": self.build_order,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DependencyGraph:
        """Create from dictionary."""
        graph = cls(root=data["root"])
        for name, node_data in data.get("nodes", {}).items():
            graph.nodes[name] = DependencyNode.from_dict(node_data)
        graph.edges = data.get("edges", {})
        graph.cycles = data.get("cycles", [])
        graph.conflicts = [ConflictInfo(**c) for c in data.get("conflicts", [])]
        graph.license_issues = data.get("license_issues", [])
        graph.build_order = data.get("build_order", [])
        return graph

    def to_tree_string(
        self, node: str | None = None, prefix: str = "", is_last: bool = True
    ) -> str:
        """Generate ASCII tree representation.

        Args:
            node: Starting node (default: root)
            prefix: Line prefix for indentation
            is_last: Whether this is the last child

        Returns:
            ASCII tree string
        """
        if node is None:
            node = self.root

        node_obj = self.nodes.get(node)
        version = f"=={node_obj.version}" if node_obj and node_obj.version else ""

        connector = "└── " if is_last else "├── "
        lines = [f"{prefix}{connector}{node}{version}"]

        new_prefix = prefix + ("    " if is_last else "│   ")
        deps = self.edges.get(node, [])

        for i, dep in enumerate(deps):
            is_last_child = i == len(deps) - 1
            lines.append(self.to_tree_string(dep, new_prefix, is_last_child))

        return "\n".join(lines)
