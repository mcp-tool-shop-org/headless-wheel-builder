"""Tests for dependency graph analysis module."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from headless_wheel_builder.depgraph.analyzer import DependencyAnalyzer
from headless_wheel_builder.depgraph.cli import deps
from headless_wheel_builder.depgraph.models import (
    ConflictInfo,
    DependencyGraph,
    DependencyNode,
    DependencyType,
    LicenseCategory,
    LicenseInfo,
    categorize_license,
)
from headless_wheel_builder.depgraph.resolver import (
    DependencyResolver,
    find_minimal_upgrade,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestLicenseInfo:
    """Tests for LicenseInfo model."""

    def test_create(self) -> None:
        """Test creating license info."""
        info = LicenseInfo(name="MIT", category=LicenseCategory.PERMISSIVE)
        assert info.name == "MIT"
        assert info.category == LicenseCategory.PERMISSIVE

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        info = LicenseInfo(
            name="Apache-2.0",
            category=LicenseCategory.PERMISSIVE,
            url="https://example.com/license",
        )
        d = info.to_dict()
        assert d["name"] == "Apache-2.0"
        assert d["category"] == "permissive"

    def test_from_dict(self) -> None:
        """Test creating from dictionary."""
        data = {
            "name": "GPL-3.0",
            "category": "copyleft",
            "url": "",
        }
        info = LicenseInfo.from_dict(data)
        assert info.name == "GPL-3.0"
        assert info.category == LicenseCategory.COPYLEFT


class TestCategorizeLicense:
    """Tests for license categorization."""

    def test_mit(self) -> None:
        """Test MIT license categorization."""
        assert categorize_license("MIT") == LicenseCategory.PERMISSIVE
        assert categorize_license("MIT License") == LicenseCategory.PERMISSIVE

    def test_bsd(self) -> None:
        """Test BSD license categorization."""
        assert categorize_license("BSD-3-Clause") == LicenseCategory.PERMISSIVE
        assert categorize_license("BSD") == LicenseCategory.PERMISSIVE

    def test_apache(self) -> None:
        """Test Apache license categorization."""
        assert categorize_license("Apache-2.0") == LicenseCategory.PERMISSIVE
        assert categorize_license("Apache License 2.0") == LicenseCategory.PERMISSIVE

    def test_gpl(self) -> None:
        """Test GPL license categorization."""
        assert categorize_license("GPL-3.0") == LicenseCategory.COPYLEFT
        assert categorize_license("GPLv3") == LicenseCategory.COPYLEFT

    def test_lgpl(self) -> None:
        """Test LGPL license categorization."""
        assert categorize_license("LGPL-2.1") == LicenseCategory.WEAK_COPYLEFT
        assert categorize_license("LGPL") == LicenseCategory.WEAK_COPYLEFT

    def test_mpl(self) -> None:
        """Test MPL license categorization."""
        assert categorize_license("MPL-2.0") == LicenseCategory.WEAK_COPYLEFT

    def test_unknown(self) -> None:
        """Test unknown license."""
        assert categorize_license("Custom License") == LicenseCategory.UNKNOWN


class TestDependencyNode:
    """Tests for DependencyNode model."""

    def test_create(self) -> None:
        """Test creating node."""
        node = DependencyNode(
            name="requests",
            version="2.28.0",
            dep_type=DependencyType.DIRECT,
        )
        assert node.name == "requests"
        assert node.version == "2.28.0"
        assert node.dep_type == DependencyType.DIRECT

    def test_key(self) -> None:
        """Test node key generation."""
        node = DependencyNode(name="pkg", version="1.0.0")
        assert node.key == "pkg==1.0.0"

        node_no_version = DependencyNode(name="pkg")
        assert node_no_version.key == "pkg"

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        node = DependencyNode(
            name="test",
            version="1.0.0",
            license_info=LicenseInfo(name="MIT"),
        )
        d = node.to_dict()
        assert d["name"] == "test"
        assert d["license_info"]["name"] == "MIT"

    def test_from_dict(self) -> None:
        """Test creating from dictionary."""
        data = {
            "name": "restored",
            "version": "2.0.0",
            "dep_type": "transitive",
            "dependencies": ["dep1", "dep2"],
        }
        node = DependencyNode.from_dict(data)
        assert node.name == "restored"
        assert node.dep_type == DependencyType.TRANSITIVE
        assert len(node.dependencies) == 2


class TestConflictInfo:
    """Tests for ConflictInfo model."""

    def test_create(self) -> None:
        """Test creating conflict info."""
        conflict = ConflictInfo(
            package="requests",
            required_versions={"a": ">=2.0", "b": "<=1.9"},
            message="Incompatible versions",
        )
        assert conflict.package == "requests"
        assert conflict.is_resolvable is False

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        conflict = ConflictInfo(
            package="pkg",
            required_versions={"x": ">=1.0"},
        )
        d = conflict.to_dict()
        assert d["package"] == "pkg"


class TestDependencyGraph:
    """Tests for DependencyGraph model."""

    def test_add_node(self) -> None:
        """Test adding nodes."""
        graph = DependencyGraph(root="root")
        node = DependencyNode(name="dep1", version="1.0.0")
        graph.add_node(node)

        assert "dep1" in graph.nodes
        assert graph.nodes["dep1"].version == "1.0.0"

    def test_add_edge(self) -> None:
        """Test adding edges."""
        graph = DependencyGraph(root="root")
        graph.add_node(DependencyNode(name="root"))
        graph.add_node(DependencyNode(name="dep1"))
        graph.add_edge("root", "dep1")

        assert "dep1" in graph.edges["root"]

    def test_get_node(self) -> None:
        """Test getting nodes."""
        graph = DependencyGraph(root="root")
        graph.add_node(DependencyNode(name="test", version="1.0.0"))

        node = graph.get_node("test")
        assert node is not None
        assert node.version == "1.0.0"

        assert graph.get_node("nonexistent") is None

    def test_get_dependencies(self) -> None:
        """Test getting dependencies."""
        graph = DependencyGraph(root="root")
        graph.add_node(DependencyNode(name="root"))
        graph.add_node(DependencyNode(name="dep1"))
        graph.add_node(DependencyNode(name="dep2"))
        graph.add_edge("root", "dep1")
        graph.add_edge("root", "dep2")

        deps = graph.get_dependencies("root")
        assert set(deps) == {"dep1", "dep2"}

    def test_get_dependents(self) -> None:
        """Test getting dependents."""
        graph = DependencyGraph(root="root")
        graph.add_node(DependencyNode(name="root"))
        graph.add_node(DependencyNode(name="dep"))
        graph.add_edge("root", "dep")

        dependents = graph.get_dependents("dep")
        assert dependents == ["root"]

    def test_depth_first_traverse(self) -> None:
        """Test DFS traversal."""
        graph = DependencyGraph(root="root")
        graph.add_node(DependencyNode(name="root"))
        graph.add_node(DependencyNode(name="a"))
        graph.add_node(DependencyNode(name="b"))
        graph.add_edge("root", "a")
        graph.add_edge("a", "b")

        order = graph.depth_first_traverse()
        assert order == ["root", "a", "b"]

    def test_to_tree_string(self) -> None:
        """Test tree string generation."""
        graph = DependencyGraph(root="root")
        graph.add_node(DependencyNode(name="root", version="1.0.0"))
        graph.add_node(DependencyNode(name="dep", version="2.0.0"))
        graph.add_edge("root", "dep")

        tree_str = graph.to_tree_string()
        assert "root" in tree_str
        assert "dep" in tree_str

    def test_to_dict_from_dict(self) -> None:
        """Test serialization round-trip."""
        graph = DependencyGraph(root="root")
        graph.add_node(DependencyNode(name="root", version="1.0.0"))
        graph.add_node(DependencyNode(name="dep", version="2.0.0"))
        graph.add_edge("root", "dep")

        data = graph.to_dict()
        restored = DependencyGraph.from_dict(data)

        assert restored.root == "root"
        assert "dep" in restored.nodes


class TestDependencyAnalyzer:
    """Tests for DependencyAnalyzer."""

    def test_parse_requirement_simple(self) -> None:
        """Test parsing simple requirement."""
        analyzer = DependencyAnalyzer()
        name, spec, extras = analyzer.parse_requirement("requests")
        assert name == "requests"
        assert spec == ""
        assert extras == []

    def test_parse_requirement_version(self) -> None:
        """Test parsing requirement with version."""
        analyzer = DependencyAnalyzer()
        name, spec, _extras = analyzer.parse_requirement("requests>=2.0,<3.0")
        assert name == "requests"
        assert spec == ">=2.0,<3.0"

    def test_parse_requirement_extras(self) -> None:
        """Test parsing requirement with extras."""
        analyzer = DependencyAnalyzer()
        name, _spec, extras = analyzer.parse_requirement("requests[security,socks]>=2.0")
        assert name == "requests"
        assert extras == ["security", "socks"]

    def test_parse_requirement_underscore(self) -> None:
        """Test parsing requirement with underscore."""
        analyzer = DependencyAnalyzer()
        name, _spec, _extras = analyzer.parse_requirement("my_package>=1.0")
        assert name == "my-package"  # Normalized

    @pytest.mark.asyncio
    async def test_build_graph_mock(self) -> None:
        """Test building graph with mocked PyPI."""
        analyzer = DependencyAnalyzer()

        mock_info = {
            "info": {
                "name": "test",
                "version": "1.0.0",
                "license": "MIT",
                "home_page": "https://example.com",
            }
        }

        with patch.object(analyzer, "fetch_package_info", return_value=mock_info):
            graph = await analyzer.build_graph("test")

        assert graph.root == "test"
        assert "test" in graph.nodes

        await analyzer.close()

    @pytest.mark.asyncio
    async def test_analyze_local(self, tmp_path: Path) -> None:
        """Test analyzing local project."""
        # Create pyproject.toml
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[project]
name = "testproject"
version = "1.0.0"
dependencies = ["requests>=2.0"]
""",
            encoding="utf-8",
        )

        analyzer = DependencyAnalyzer()

        mock_info = {
            "info": {
                "name": "requests",
                "version": "2.28.0",
                "license": "Apache-2.0",
                "requires_dist": None,
            }
        }

        with patch.object(analyzer, "fetch_package_info", return_value=mock_info):
            graph = await analyzer.analyze_local(tmp_path)

        assert graph.root == "testproject"
        assert "requests" in graph.nodes

        await analyzer.close()


class TestDependencyResolver:
    """Tests for DependencyResolver."""

    def test_add_constraint(self) -> None:
        """Test adding constraints."""
        resolver = DependencyResolver()
        resolver.add_constraint("pkg", ">=1.0", "root")

        assert "pkg" in resolver.constraints
        assert len(resolver.constraints["pkg"]) == 1

    def test_set_available_versions(self) -> None:
        """Test setting available versions."""
        resolver = DependencyResolver()
        resolver.set_available_versions("pkg", ["1.0.0", "1.1.0", "2.0.0"])

        assert resolver.available["pkg"] == ["1.0.0", "1.1.0", "2.0.0"]

    def test_resolve_simple(self) -> None:
        """Test simple resolution."""
        resolver = DependencyResolver()
        resolver.add_constraint("pkg", ">=1.0", "root")
        resolver.set_available_versions("pkg", ["0.9.0", "1.0.0", "1.1.0"])

        result = resolver.resolve("pkg")
        assert result is not None
        assert result.version == "1.1.0"  # Latest satisfying

    def test_resolve_multiple_constraints(self) -> None:
        """Test resolution with multiple constraints."""
        resolver = DependencyResolver()
        resolver.add_constraint("pkg", ">=1.0", "root")
        resolver.add_constraint("pkg", "<2.0", "other")
        resolver.set_available_versions("pkg", ["0.9.0", "1.0.0", "1.5.0", "2.0.0"])

        result = resolver.resolve("pkg")
        assert result is not None
        assert result.version == "1.5.0"

    def test_resolve_no_solution(self) -> None:
        """Test resolution with no solution."""
        resolver = DependencyResolver()
        resolver.add_constraint("pkg", ">=2.0", "root")
        resolver.add_constraint("pkg", "<1.0", "other")
        resolver.set_available_versions("pkg", ["1.0.0", "1.5.0", "2.0.0"])

        result = resolver.resolve("pkg")
        assert result is None

    def test_resolve_all(self) -> None:
        """Test resolving all packages."""
        resolver = DependencyResolver()
        resolver.add_constraint("a", ">=1.0", "root")
        resolver.add_constraint("b", ">=2.0", "root")
        resolver.set_available_versions("a", ["1.0.0", "1.1.0"])
        resolver.set_available_versions("b", ["2.0.0", "2.1.0"])

        resolved, conflicts = resolver.resolve_all()
        assert "a" in resolved
        assert "b" in resolved
        assert len(conflicts) == 0

    def test_find_conflicts(self) -> None:
        """Test finding conflicts."""
        resolver = DependencyResolver()
        resolver.add_constraint("pkg", ">=2.0", "a")
        resolver.add_constraint("pkg", "<=1.0", "b")
        resolver.set_available_versions("pkg", ["0.5.0", "1.0.0", "2.0.0"])

        conflicts = resolver.find_conflicts()
        assert len(conflicts) == 1
        assert conflicts[0].package == "pkg"

    def test_from_graph(self) -> None:
        """Test creating resolver from graph."""
        graph = DependencyGraph(root="root")
        graph.add_node(DependencyNode(name="root", version="1.0.0"))
        graph.add_node(DependencyNode(name="dep", version="2.0.0"))
        graph.add_edge("root", "dep")

        resolver = DependencyResolver.from_graph(graph)
        assert "dep" in resolver.constraints


class TestFindMinimalUpgrade:
    """Tests for find_minimal_upgrade."""

    def test_no_changes(self) -> None:
        """Test when no changes needed."""
        current = {"a": "1.0.0", "b": "2.0.0"}
        target = {"a": "1.0.0", "b": "2.0.0"}

        changes = find_minimal_upgrade(current, target)
        assert len(changes) == 0

    def test_some_changes(self) -> None:
        """Test when some changes needed."""
        current = {"a": "1.0.0", "b": "2.0.0"}
        target = {"a": "1.0.0", "b": "2.1.0", "c": "1.0.0"}

        changes = find_minimal_upgrade(current, target)
        assert "b" in changes
        assert changes["b"] == ("2.0.0", "2.1.0")
        assert "c" in changes
        assert changes["c"] == ("", "1.0.0")


class TestDepsCLI:
    """Tests for deps CLI commands."""

    def test_tree_json(self) -> None:
        """Test tree command with JSON output."""
        runner = CliRunner()

        mock_graph = DependencyGraph(root="test")
        mock_graph.add_node(DependencyNode(name="test", version="1.0.0"))

        with patch("headless_wheel_builder.depgraph.cli.run_async", return_value=mock_graph):
            result = runner.invoke(deps, ["tree", "test", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["root"] == "test"

    def test_analyze_not_found(self, tmp_path: Path) -> None:
        """Test analyze with no config file."""
        runner = CliRunner()
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = runner.invoke(deps, ["analyze", str(empty_dir)])
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_licenses_json(self) -> None:
        """Test licenses command with JSON output."""
        runner = CliRunner()

        mock_graph = DependencyGraph(root="test")
        mock_graph.add_node(
            DependencyNode(
                name="test",
                version="1.0.0",
                license_info=LicenseInfo(name="MIT"),
            )
        )

        with patch("headless_wheel_builder.depgraph.cli.run_async", return_value=mock_graph):
            result = runner.invoke(deps, ["licenses", "test", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "licenses" in data

    def test_conflicts_none(self) -> None:
        """Test conflicts command with no conflicts."""
        runner = CliRunner()

        mock_graph = DependencyGraph(root="test")
        mock_graph.conflicts = []

        with patch("headless_wheel_builder.depgraph.cli.run_async", return_value=mock_graph):
            result = runner.invoke(deps, ["conflicts", "test"])
            assert result.exit_code == 0
            assert "No version conflicts" in result.output

    def test_conflicts_found(self) -> None:
        """Test conflicts command with conflicts."""
        runner = CliRunner()

        mock_graph = DependencyGraph(root="test")
        mock_graph.conflicts = [
            ConflictInfo(
                package="pkg",
                required_versions={"a": ">=2.0", "b": "<1.0"},
                message="Conflict",
            )
        ]

        with patch("headless_wheel_builder.depgraph.cli.run_async", return_value=mock_graph):
            result = runner.invoke(deps, ["conflicts", "test"])
            assert result.exit_code == 1
            assert "1 version conflict" in result.output

    def test_cycles_none(self) -> None:
        """Test cycles command with no cycles."""
        runner = CliRunner()

        mock_graph = DependencyGraph(root="test")
        mock_graph.cycles = []

        with patch("headless_wheel_builder.depgraph.cli.run_async", return_value=mock_graph):
            result = runner.invoke(deps, ["cycles", "test"])
            assert result.exit_code == 0
            assert "No circular dependencies" in result.output

    def test_cycles_found(self) -> None:
        """Test cycles command with cycles."""
        runner = CliRunner()

        mock_graph = DependencyGraph(root="test")
        mock_graph.cycles = [["a", "b", "c", "a"]]

        with patch("headless_wheel_builder.depgraph.cli.run_async", return_value=mock_graph):
            result = runner.invoke(deps, ["cycles", "test"])
            assert result.exit_code == 1
            assert "circular dependency" in result.output

    def test_order_json(self) -> None:
        """Test order command with JSON output."""
        runner = CliRunner()

        mock_graph = DependencyGraph(root="test")
        mock_graph.build_order = ["dep1", "dep2", "test"]

        with patch("headless_wheel_builder.depgraph.cli.run_async", return_value=mock_graph):
            result = runner.invoke(deps, ["order", "test", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["build_order"] == ["dep1", "dep2", "test"]
