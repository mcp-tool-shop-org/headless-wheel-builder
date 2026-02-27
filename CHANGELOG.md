# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- SECURITY.md with vulnerability reporting policy and supported versions
- Threat model section in README (data touched, data NOT touched, permissions)
- Structured error shape on all exceptions: `error_code`, `hint`, `retryable`, `exit_code`
- `scripts/verify.sh` — one-command lint + format + typecheck + test + build
- `pip-audit` dependency scanning job in CI
- SHIP_GATE.md and SCORECARD.md for product standards tracking

### Changed
- CLI error output now shows error code and hint for HWBError exceptions
- Exit codes follow Shipcheck contract: 0 ok, 1 user error, 2 runtime error

## [0.3.0] - 2026-01-24

### Added
- **Release Management**: Draft releases with multi-stage approval workflows
  - Simple, two-stage, and enterprise workflow templates
  - Approval tracking with comments and audit trail
  - Auto-publish on approval option
  - Rollback support for published releases
- **Dependency Analysis**: Full dependency graph with license compliance
  - Dependency tree visualization
  - Cycle and conflict detection
  - License compliance checking (GPL in permissive projects)
  - Build order calculation
- **CI/CD Pipeline Orchestration**: Build-to-release automation
  - YAML-based pipeline definitions
  - Stage dependencies and parallel execution
  - Conditional execution with expressions
  - Artifact passing between stages
- **GitHub Actions Generator**: Create optimized CI workflows
  - Multi-platform matrix generation
  - Caching configuration
  - Trusted publisher support
- **Multi-Repository Operations**: Coordinate builds across repos
  - Bulk builds from repository list
  - Version synchronization
  - Coordinated releases
- **Notification System**: Slack, Discord, and webhook integrations
  - Configurable notification triggers
  - Rich message formatting
  - Webhook testing
- **Security Scanning**: SBOM generation, license audits, vulnerability checks
  - CycloneDX and SPDX SBOM formats
  - pip-audit integration
  - License policy enforcement
- **Metrics & Analytics**: Build performance tracking
  - Build time tracking
  - Success/failure rates
  - Prometheus export format
- **Artifact Caching**: LRU cache with registry integration
  - Content-addressable storage
  - Size limits and pruning
  - Cache statistics
- **Changelog Generation**: Auto-generate from Conventional Commits
  - Parse commit history
  - Group by change type
  - Markdown output

### Changed
- Comprehensive README rewrite with all new features documented
- Enhanced publish.yml workflow with security scanning and attestations
- Improved CLI structure with modular command groups

### Fixed
- Windows multiprocessing compatibility in build isolation

## [0.2.0] - 2026-01-23

### Added
- Docker isolation support (manylinux/musllinux)
- PyPI publishing with Trusted Publishers (OIDC)
- DevPi and Artifactory registry support
- S3 artifact storage
- Build matrix for multiple Python versions

## [0.1.0] - 2026-01-23

### Added
- Initial release
- Core build engine with PEP 517 support
- Source resolution for local paths, git URLs, and archives
- Project analyzer for pyproject.toml and setup.py
- Virtual environment isolation with uv support
- CLI with `build` and `inspect` commands
- Comprehensive documentation suite
- Unit tests for core functionality
