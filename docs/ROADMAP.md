# Headless Wheel Builder - Development Roadmap

> **Project Vision**: A universal, headless Python wheel builder supporting local paths, git repos, and CI/CD pipelines with flexible isolation (venv/Docker), multi-registry publishing, and automated versioning.

---

## 2026 Best Practices Applied

> **Sources**: [Python Packaging User Guide 2026](https://packaging.python.org/en/latest/), [Hatchling PEP 517 Guide](https://johal.in/hatchling-build-backend-pep-517-compliant-python-packaging-2026-2/), [cibuildwheel Documentation](https://cibuildwheel.pypa.io/), [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/), [uv Package Manager](https://docs.astral.sh/uv/), [Conventional Commits](https://www.conventionalcommits.org/), [Python Packaging Best Practices 2026](https://dasroot.net/posts/2026/01/python-packaging-best-practices-setuptools-poetry-hatch/)

This roadmap follows 2026 Python packaging and agile best practices:

1. **PEP 517/518/621/660 First**: All builds use `pyproject.toml`-based configuration. Support legacy `setup.py`/`setup.cfg` as fallback with migration guidance.

2. **uv for Speed**: Leverage uv (10-100x faster than pip) for dependency resolution and build environment creation where available.

3. **Trusted Publishers for Security**: OIDC-based publishing eliminates long-lived API tokens. Support GitHub Actions, GitLab CI/CD, and Google Cloud as identity providers.

4. **Build Isolation by Default**: Every build runs in an isolated environment (venv or Docker) with only declared build dependencies. No host contamination.

5. **Hatchling as Default Backend**: Recommend hatchling for 5-10x faster builds. Support all PEP 517-compliant backends (setuptools, flit, pdm, maturin).

6. **Conventional Commits for Automation**: Standardized commit messages enable automatic version bumping and changelog generation.

7. **Cross-Platform from Day One**: Windows/macOS/Linux support with manylinux/musllinux Docker images for portable Linux wheels.

8. **Outcome-Based Milestones**: Each phase defines clear exit criteria rather than just task completion.

---

## Phase 0: Foundation
**Duration**: Documentation & Design
**Status**: 🟡 In Progress

### Objectives
- [x] Research 2026 Python packaging standards
- [x] Research build isolation strategies
- [x] Research publishing workflows (PyPI, private registries)
- [x] Research versioning and changelog automation
- [ ] Complete documentation suite
- [ ] Set up project structure
- [ ] Define CLI interface

### Deliverables
| Document | Purpose | Status |
|----------|---------|--------|
| `ROADMAP.md` | Development phases and milestones | 🟡 In Progress |
| `ARCHITECTURE.md` | System design and component interactions | ⬜ Pending |
| `API.md` | CLI and programmatic interface specifications | ⬜ Pending |
| `SECURITY.md` | Security model and threat mitigations | ⬜ Pending |
| `PUBLISHING.md` | Registry publishing workflows | ⬜ Pending |
| `ISOLATION.md` | Build isolation strategies (venv/Docker) | ⬜ Pending |
| `VERSIONING.md` | Semantic versioning and changelog automation | ⬜ Pending |
| `CONTRIBUTING.md` | Development guidelines | ⬜ Pending |

### Exit Criteria
- All documentation complete and reviewed
- Project structure scaffolded
- CLI interface designed and documented

---

## Phase 1: Core Build Engine
**Duration**: ~2 weeks
**Status**: ⬜ Not Started

### Objectives
Build the foundational wheel building capability without isolation.

### 1.1 Source Discovery
```
src/headless_wheel_builder/core/source.py
```
- [ ] Local path detection (directory, tarball, zip)
- [ ] Git URL parsing (https, ssh, branch/tag/commit)
- [ ] Git clone with sparse checkout support
- [ ] Editable source detection

### 1.2 Project Analysis
```
src/headless_wheel_builder/core/analyzer.py
```
- [ ] `pyproject.toml` parser (PEP 621 metadata)
- [ ] `setup.py`/`setup.cfg` fallback detection
- [ ] Build backend detection (hatchling, setuptools, flit, etc.)
- [ ] Build dependency extraction
- [ ] Project metadata extraction (name, version, etc.)

### 1.3 Build Execution
```
src/headless_wheel_builder/core/builder.py
```
- [ ] PEP 517 build frontend implementation
- [ ] Build backend invocation
- [ ] Wheel file generation
- [ ] Source distribution (sdist) generation
- [ ] Build log capture and streaming

### 1.4 Output Management
```
src/headless_wheel_builder/core/output.py
```
- [ ] Output directory management
- [ ] Wheel file validation (wheel-inspect)
- [ ] Artifact metadata generation
- [ ] Cleanup and error handling

### Exit Criteria
- Can build wheel from local `pyproject.toml` project
- Supports all major build backends
- Produces valid wheel files
- >80% test coverage

---

## Phase 2: Build Isolation
**Duration**: ~2 weeks
**Status**: ⬜ Not Started

### Objectives
Implement isolated build environments using venv and Docker.

### 2.1 Virtual Environment Isolation
```
src/headless_wheel_builder/isolation/venv.py
```
- [ ] Ephemeral venv creation
- [ ] uv integration for fast installs (with pip fallback)
- [ ] Build dependency installation
- [ ] Environment cleanup
- [ ] Python version selection (pyenv/uv integration)

### 2.2 Docker Isolation
```
src/headless_wheel_builder/isolation/docker.py
```
- [ ] manylinux image support (2014, 2_28, 2_34, 2_35)
- [ ] musllinux image support (1_2)
- [ ] Custom Dockerfile support
- [ ] Volume mounting for source/output
- [ ] Build execution in container
- [ ] GPU passthrough for CUDA wheels (optional)

### 2.3 Isolation Strategy Selection
```
src/headless_wheel_builder/isolation/strategy.py
```
- [ ] Auto-detection of best isolation method
- [ ] Platform-specific defaults
- [ ] User override support
- [ ] Hybrid strategies (venv for pure Python, Docker for extensions)

### Exit Criteria
- Can build in isolated venv with any Python version
- Can build manylinux wheels using Docker
- Isolation is configurable per build
- No host system contamination

---

## Phase 3: Multi-Platform Support
**Duration**: ~2 weeks
**Status**: ⬜ Not Started

### Objectives
Support building wheels for multiple platforms and Python versions.

### 3.1 Build Matrix
```
src/headless_wheel_builder/matrix/builder.py
```
- [ ] Python version matrix (3.9, 3.10, 3.11, 3.12, 3.13, 3.14)
- [ ] Platform matrix (linux, macos, windows)
- [ ] Architecture matrix (x86_64, aarch64, arm64)
- [ ] Parallel build execution
- [ ] Build matrix configuration (YAML/TOML)

### 3.2 Platform-Specific Handling
```
src/headless_wheel_builder/matrix/platform.py
```
- [ ] manylinux tag selection and validation
- [ ] macOS SDK version handling
- [ ] Windows Visual C++ detection
- [ ] auditwheel integration (Linux)
- [ ] delocate integration (macOS)

### 3.3 Build Artifacts
```
src/headless_wheel_builder/matrix/artifacts.py
```
- [ ] Multi-wheel output organization
- [ ] Artifact manifest generation
- [ ] Checksum generation (SHA256)
- [ ] Platform tag validation

### Exit Criteria
- Can build wheels for multiple Python versions in parallel
- Produces valid manylinux wheels
- Produces valid macOS wheels (universal2 support)
- Windows wheels build correctly

---

## Phase 4: Publishing & Registry Integration
**Duration**: ~2 weeks
**Status**: ⬜ Not Started

### Objectives
Implement publishing to PyPI and private registries.

### 4.1 PyPI Publishing
```
src/headless_wheel_builder/publish/pypi.py
```
- [ ] Trusted Publishers (OIDC) authentication
- [ ] API token authentication (fallback)
- [ ] TestPyPI support
- [ ] Upload with twine
- [ ] Pre-upload validation

### 4.2 Private Registry Support
```
src/headless_wheel_builder/publish/registry.py
```
- [ ] DevPi integration
- [ ] Artifactory integration
- [ ] AWS CodeArtifact support
- [ ] Google Artifact Registry support
- [ ] Azure Artifacts support
- [ ] Cloudsmith support

### 4.3 S3/Object Storage
```
src/headless_wheel_builder/publish/s3.py
```
- [ ] S3-compatible storage upload
- [ ] MinIO support
- [ ] Index generation (PEP 503 simple API)
- [ ] CDN-friendly output

### Exit Criteria
- Can publish to PyPI using Trusted Publishers
- Can publish to major private registries
- Can create pip-installable S3 index
- Secure credential handling

---

## Phase 5: Versioning & Changelog
**Duration**: ~1.5 weeks
**Status**: ⬜ Not Started

### Objectives
Implement automated versioning and changelog generation.

### 5.1 Version Management
```
src/headless_wheel_builder/version/manager.py
```
- [ ] Semantic versioning (SemVer) support
- [ ] Calendar versioning (CalVer) support
- [ ] PEP 440 validation
- [ ] Version file updates (pyproject.toml, __init__.py, etc.)
- [ ] Git tag creation

### 5.2 Conventional Commits
```
src/headless_wheel_builder/version/commits.py
```
- [ ] Commit message parsing
- [ ] Version bump detection (major/minor/patch)
- [ ] Breaking change detection
- [ ] Scope extraction

### 5.3 Changelog Generation
```
src/headless_wheel_builder/version/changelog.py
```
- [ ] Keep a Changelog format
- [ ] Conventional Changelog format
- [ ] Custom template support (Jinja2)
- [ ] GitHub/GitLab release notes format
- [ ] Unreleased section management

### Exit Criteria
- Can auto-bump version from commits
- Generates proper changelog
- Creates git tags
- Supports multiple versioning schemes

---

## Phase 6: CLI & Configuration
**Duration**: ~1.5 weeks
**Status**: ⬜ Not Started

### Objectives
Build the command-line interface and configuration system.

### 6.1 CLI Implementation
```
src/headless_wheel_builder/cli/main.py
```
- [ ] `hwb build` - Build wheels
- [ ] `hwb publish` - Publish to registry
- [ ] `hwb version` - Manage versions
- [ ] `hwb matrix` - Show/run build matrix
- [ ] `hwb inspect` - Analyze project
- [ ] `hwb init` - Initialize pyproject.toml
- [ ] Rich terminal output (progress bars, colors)

### 6.2 Configuration System
```
src/headless_wheel_builder/config/
```
- [ ] `pyproject.toml` [tool.hwb] section
- [ ] `hwb.toml` standalone config
- [ ] Environment variable support
- [ ] CLI flag overrides
- [ ] Configuration validation
- [ ] Config file discovery (walk up directories)

### 6.3 CI/CD Integration
```
src/headless_wheel_builder/ci/
```
- [ ] GitHub Actions workflow generation
- [ ] GitLab CI template generation
- [ ] Pre-built action/template
- [ ] CI environment detection
- [ ] Trusted Publisher setup helpers

### Exit Criteria
- Full CLI with all commands working
- Configuration system complete
- CI templates for major platforms
- Comprehensive help and documentation

---

## Phase 7: Caching & Performance
**Duration**: ~1 week
**Status**: ⬜ Not Started

### Objectives
Optimize build performance through caching.

### 7.1 Build Caching
```
src/headless_wheel_builder/cache/
```
- [ ] Wheel cache (avoid rebuilds)
- [ ] Build environment cache (venv reuse)
- [ ] Docker layer caching hints
- [ ] Dependency resolution cache
- [ ] Cache invalidation strategies

### 7.2 Incremental Builds
- [ ] Source hash tracking
- [ ] Dependency change detection
- [ ] Partial rebuild support
- [ ] Lock file integration

### Exit Criteria
- Repeated builds are significantly faster
- Cache hits/misses are reported
- Cache can be cleared/managed

---

## Phase 8: Production Hardening
**Duration**: ~1.5 weeks
**Status**: ⬜ Not Started

### Objectives
Make the system production-ready.

### 8.1 Error Handling
- [ ] Comprehensive error taxonomy
- [ ] User-friendly error messages
- [ ] Recovery suggestions
- [ ] Verbose/debug modes

### 8.2 Monitoring & Observability
- [ ] Structured logging (JSON option)
- [ ] Build metrics collection
- [ ] Timing breakdowns
- [ ] CI-friendly output modes

### 8.3 Testing & Quality
- [ ] >90% test coverage
- [ ] Integration tests with real packages
- [ ] Cross-platform CI testing
- [ ] Fuzzing for config parsing
- [ ] Performance benchmarks

### 8.4 Documentation
- [ ] User guide
- [ ] API reference (auto-generated)
- [ ] Troubleshooting guide
- [ ] Migration guide (from setuptools, poetry, etc.)
- [ ] Video tutorials

### Exit Criteria
- Production-quality error handling
- Comprehensive test suite
- Full documentation
- Performance benchmarks published

---

## Phase 9: Ecosystem Integration
**Duration**: ~1 week
**Status**: ⬜ Not Started

### Objectives
Integrate with the Python packaging ecosystem.

### 9.1 Tool Integrations
- [ ] pre-commit hook support
- [ ] pytest plugin for testing wheels
- [ ] tox integration
- [ ] nox integration

### 9.2 IDE/Editor Support
- [ ] VS Code extension (build task)
- [ ] PyCharm plugin (run configuration)
- [ ] Cursor/Claude Code MCP tool

### 9.3 Release & Distribution
- [ ] v1.0.0 release
- [ ] PyPI publishing
- [ ] Homebrew formula
- [ ] Conda package
- [ ] Docker image
- [ ] GitHub Release automation

### Exit Criteria
- Integrations with major tools
- Multiple distribution channels
- v1.0.0 released

---

## Risk Register

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Python packaging standard changes | Medium | Low | Follow PEP discussions, modular design |
| Docker unavailable on some systems | Medium | Medium | venv fallback always available |
| uv API changes | Low | Medium | Abstract behind interface, pip fallback |
| Complex C extensions fail in isolation | High | Medium | Extensive testing, escape hatches |
| Windows-specific path issues | Medium | High | Early Windows testing, pathlib everywhere |
| Registry authentication complexity | Medium | Medium | Clear docs, Trusted Publishers first |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Build time (pure Python) | <10s | Benchmark suite |
| Build time (C extension) | <60s | Benchmark suite |
| manylinux compliance | 100% | auditwheel check |
| Test coverage | >90% | pytest-cov |
| PyPI upload success | 100% | Integration tests |
| Documentation coverage | 100% public APIs | Doc coverage tool |

---

## Timeline Summary

```
Week 1-2:   Phase 0 - Foundation (Documentation)
Week 3-4:   Phase 1 - Core Build Engine
Week 5-6:   Phase 2 - Build Isolation
Week 7-8:   Phase 3 - Multi-Platform Support
Week 9-10:  Phase 4 - Publishing & Registry Integration
Week 11:    Phase 5 - Versioning & Changelog
Week 12:    Phase 6 - CLI & Configuration
Week 13:    Phase 7 - Caching & Performance
Week 14-15: Phase 8 - Production Hardening
Week 16:    Phase 9 - Ecosystem Integration
```

**Estimated Total Duration**: 14-16 weeks for full implementation

---

## Feature Comparison

| Feature | hwb | cibuildwheel | build | hatch |
|---------|-----|--------------|-------|-------|
| Headless CLI | ✅ | ✅ | ✅ | ✅ |
| Build isolation (venv) | ✅ | ✅ | ✅ | ✅ |
| Build isolation (Docker) | ✅ | ✅ | ❌ | ❌ |
| manylinux wheels | ✅ | ✅ | ❌ | ❌ |
| Git source support | ✅ | ❌ | ❌ | ❌ |
| Multi-registry publish | ✅ | ❌ | ❌ | ✅ |
| Trusted Publishers | ✅ | ❌ | ❌ | ❌ |
| Version bumping | ✅ | ❌ | ❌ | ✅ |
| Changelog generation | ✅ | ❌ | ❌ | ❌ |
| CI template generation | ✅ | ❌ | ❌ | ❌ |
| Windows native | ✅ | ✅ | ✅ | ✅ |

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-23 | 0.1.0 | Initial roadmap created |
