---
title: CLI Reference
description: All 14 Headless Wheel Builder commands — what they do and when to use them.
sidebar:
  order: 3
---

Every command follows the pattern `hwb <command> [options]`. Run `hwb <command> --help` for full usage details.

## Commands

### `hwb build`

Build wheels from a local directory, git URL, or tarball. Supports multi-Python targets, venv or Docker isolation, and output directory selection.

### `hwb publish`

Publish built wheels to PyPI, TestPyPI, private registries, or S3-compatible storage. Handles authentication and retry logic.

### `hwb inspect`

Examine a built wheel: metadata, entry points, dependencies, file listing, and size breakdown.

### `hwb github`

Headless GitHub operations: create releases, open pull requests, file issues, and trigger workflow runs without leaving the terminal.

### `hwb release`

Draft, submit, approve, publish, and roll back releases using configurable approval workflows.

### `hwb pipeline`

Orchestrate multi-stage build-to-release pipelines from YAML definitions. Supports stage selection, conditional execution, and parallel steps.

### `hwb deps`

Dependency graph analysis: tree visualization, license compliance checking, cycle detection, and topological build ordering.

### `hwb actions`

Generate GitHub Actions workflow files from your project configuration. Produces ready-to-commit CI/CD YAML.

### `hwb multirepo`

Coordinate builds, syncs, and releases across multiple repositories in a single invocation.

### `hwb notify`

Send build and release notifications to Slack, Discord, Microsoft Teams, or arbitrary webhooks.

### `hwb security`

Run security scans: vulnerability auditing, SBOM generation (CycloneDX), and license compliance checks.

### `hwb metrics`

Track build performance over time: success rates, build durations, cache hit ratios, and failure analysis.

### `hwb cache`

Manage the local LRU artifact cache. List, inspect, prune, and configure size limits.

### `hwb changelog`

Generate changelogs from Conventional Commits between two tags or refs. Outputs grouped Markdown.
