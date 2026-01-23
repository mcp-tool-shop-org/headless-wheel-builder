# Headless Wheel Builder - Versioning Documentation

> **Purpose**: Guide to semantic versioning, automated version bumping, and changelog generation.
> **Last Updated**: 2026-01-23

---

## 2026 Best Practices Applied

> **Sources**: [Semantic Versioning 2.0.0](https://semver.org/), [PEP 440 Version Identification](https://peps.python.org/pep-0440/), [Conventional Commits](https://www.conventionalcommits.org/), [Keep a Changelog](https://keepachangelog.com/), [Commitizen](https://commitizen-tools.github.io/commitizen/), [Python Semantic Release](https://python-semantic-release.readthedocs.io/), [git-cliff](https://git-cliff.org/)

This versioning guide follows 2026 best practices:

1. **Semantic Versioning (SemVer)**: MAJOR.MINOR.PATCH versioning with clear meaning for each component.

2. **PEP 440 Compliance**: All versions follow Python's version specification standard.

3. **Conventional Commits**: Standardized commit messages enable automatic version detection.

4. **Single Source of Truth**: Version defined in one place (`pyproject.toml`), synced to others.

5. **Automated Changelog**: Generate changelogs from commit history.

6. **Git Tag Integration**: Versions linked to immutable git tags.

7. **Pre-release Support**: Alpha, beta, and release candidate versions for testing.

8. **CalVer Option**: Calendar versioning for projects preferring date-based versions.

---

## Versioning Schemes

### Semantic Versioning (SemVer) - Default

Format: `MAJOR.MINOR.PATCH`

```
1.0.0    Initial release
1.0.1    Patch: bug fix
1.1.0    Minor: new feature (backwards compatible)
2.0.0    Major: breaking change

Pre-releases:
1.0.0a1    Alpha 1
1.0.0b1    Beta 1
1.0.0rc1   Release Candidate 1
```

**When to Increment**:

| Change Type | Version Part | Example |
|-------------|--------------|---------|
| Breaking API change | MAJOR | `1.x.x` → `2.0.0` |
| New feature (compatible) | MINOR | `1.0.x` → `1.1.0` |
| Bug fix | PATCH | `1.0.0` → `1.0.1` |
| Pre-release | SUFFIX | `1.0.0` → `1.0.1a1` |

### Calendar Versioning (CalVer)

Format: `YYYY.MM.MICRO` or `YY.MM.MICRO`

```
2026.01.0    January 2026, first release
2026.01.1    January 2026, patch
2026.02.0    February 2026, first release
```

**Configuration**:
```toml
[tool.hwb.version]
scheme = "calver"
format = "YYYY.0M.MICRO"  # 2026.01.0
```

### PEP 440 Compliance

All versions must comply with [PEP 440](https://peps.python.org/pep-0440/):

```
# Valid PEP 440 versions
1.0.0
1.0.0a1
1.0.0b2
1.0.0rc1
1.0.0.post1
1.0.0.dev1
1.0.0+local.version

# Invalid (will be rejected)
1.0.0-beta    # Use 1.0.0b1
1.0           # Use 1.0.0
v1.0.0        # No 'v' prefix in version
```

---

## Version Management

### Show Current Version

```bash
# Display current version
hwb version show

# Output:
# Current version: 1.2.3
# Source: pyproject.toml
```

### Bump Version

```bash
# Bump patch: 1.0.0 → 1.0.1
hwb version bump patch

# Bump minor: 1.0.0 → 1.1.0
hwb version bump minor

# Bump major: 1.0.0 → 2.0.0
hwb version bump major
```

### Pre-release Versions

```bash
# Create alpha: 1.0.0 → 1.0.1a1
hwb version bump patch --pre alpha

# Create beta: 1.0.1a1 → 1.0.1b1
hwb version bump --pre beta

# Create release candidate: 1.0.1b1 → 1.0.1rc1
hwb version bump --pre rc

# Release final: 1.0.1rc1 → 1.0.1
hwb version bump release
```

### Set Version Explicitly

```bash
# Set specific version
hwb version set 2.0.0

# Set pre-release
hwb version set 2.0.0rc1
```

### Git Integration

```bash
# Bump and create commit
hwb version bump patch --commit

# Bump, commit, and tag
hwb version bump patch --commit --tag

# Bump, commit, tag, and push
hwb version bump patch --commit --tag --push

# Custom commit message
hwb version bump patch --commit --message "Release v{new_version}"
```

---

## Configuration

### pyproject.toml

```toml
[tool.hwb.version]
# Versioning scheme: semver (default) or calver
scheme = "semver"

# Files to update on version bump
files = [
    "pyproject.toml",                           # project.version
    "src/mypackage/__init__.py:__version__",    # __version__ = "..."
    "src/mypackage/version.py:VERSION",         # VERSION = "..."
    "docs/conf.py:release",                     # release = "..."
]

# Commit settings
commit-message = "chore: bump version to {new_version}"
commit-author = "Release Bot <release@example.com>"

# Tag settings
tag-format = "v{version}"           # v1.0.0
tag-message = "Release {version}"   # Tag annotation

# Pre-release tag format
pre-tag-format = "v{version}"       # Same as release by default

# Sign commits and tags
sign-commits = false
sign-tags = false
```

### Version File Formats

HWB supports multiple file formats for version storage:

**pyproject.toml** (PEP 621):
```toml
[project]
version = "1.0.0"
```

**Python file with __version__**:
```python
# src/mypackage/__init__.py
__version__ = "1.0.0"
```

**Dedicated version module**:
```python
# src/mypackage/version.py
VERSION = "1.0.0"
MAJOR = 1
MINOR = 0
PATCH = 0
```

**VERSION file**:
```
1.0.0
```

---

## Conventional Commits

Conventional Commits enable automatic version detection from commit messages.

### Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types and Version Impact

| Type | Description | Version Bump |
|------|-------------|--------------|
| `feat` | New feature | MINOR |
| `fix` | Bug fix | PATCH |
| `docs` | Documentation | None |
| `style` | Formatting | None |
| `refactor` | Code restructure | None |
| `perf` | Performance | PATCH |
| `test` | Tests | None |
| `build` | Build system | None |
| `ci` | CI configuration | None |
| `chore` | Maintenance | None |

**Breaking Change** (MAJOR bump):
```
feat!: remove deprecated API
```
or
```
feat: new authentication system

BREAKING CHANGE: old auth tokens no longer valid
```

### Examples

```bash
# Feature (MINOR bump)
git commit -m "feat: add dark mode support"

# Bug fix (PATCH bump)
git commit -m "fix: resolve login timeout issue"

# Breaking change (MAJOR bump)
git commit -m "feat!: redesign API endpoints"

# With scope
git commit -m "feat(auth): add OAuth2 support"

# With body
git commit -m "fix: resolve memory leak

The connection pool was not properly releasing resources.
This commit adds proper cleanup in the destructor."
```

### Auto Version Bump

```bash
# Determine version from commits
hwb version bump auto

# What happens:
# 1. Scans commits since last tag
# 2. Detects highest impact change
# 3. Bumps appropriate version part

# Example:
# Last tag: v1.0.0
# Commits:
#   - fix: resolve bug
#   - feat: add feature
#   - docs: update README
# Result: 1.1.0 (feat triggers MINOR bump)
```

---

## Changelog Generation

### Automatic Changelog

```bash
# Generate changelog for all versions
hwb version changelog

# Generate for specific version
hwb version changelog --version 1.0.0

# Generate since last tag
hwb version changelog --unreleased

# Output formats
hwb version changelog --format markdown    # Default
hwb version changelog --format github      # GitHub release notes
hwb version changelog --format json        # Machine-readable
```

### Changelog Format

**Keep a Changelog** (default):
```markdown
# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- New feature X

### Fixed
- Bug in Y

## [1.0.0] - 2026-01-23

### Added
- Initial release with core functionality

### Changed
- Updated dependencies

### Deprecated
- Old API (use new API instead)

### Removed
- Legacy support

### Fixed
- Various bug fixes

### Security
- Fixed XSS vulnerability
```

### Configuration

```toml
# pyproject.toml
[tool.hwb.changelog]
# Output file
file = "CHANGELOG.md"

# Template (built-in or custom)
template = "keepachangelog"  # or "conventional", "angular"

# Custom template (Jinja2)
# template-file = "changelog.jinja2"

# Categories mapping
[tool.hwb.changelog.categories]
feat = "Added"
fix = "Fixed"
perf = "Performance"
refactor = "Changed"
docs = "Documentation"
deprecate = "Deprecated"
remove = "Removed"
security = "Security"

# Exclude types from changelog
exclude = ["chore", "ci", "test", "style"]

# Include commit links
links = true

# Include authors
authors = true
```

### GitHub Release Notes

```bash
# Generate GitHub-flavored release notes
hwb version changelog --format github > RELEASE.md

# Output:
## What's Changed

### Features
* Add dark mode support by @user in #123
* New authentication system by @user in #124

### Bug Fixes
* Fix memory leak by @user in #125

### Full Changelog
https://github.com/user/repo/compare/v0.9.0...v1.0.0
```

---

## Release Workflow

### Manual Release

```bash
# 1. Ensure clean working directory
git status

# 2. Bump version
hwb version bump minor

# 3. Update changelog
hwb version changelog --unreleased >> CHANGELOG.md

# 4. Commit changes
git add pyproject.toml CHANGELOG.md src/mypackage/__init__.py
git commit -m "chore: release v1.1.0"

# 5. Tag release
git tag -a v1.1.0 -m "Release v1.1.0"

# 6. Push
git push origin main --tags

# 7. Build and publish
hwb build
hwb publish --trusted-publisher
```

### Automated Release (Recommended)

```bash
# Single command: bump, commit, tag, push
hwb version bump minor --commit --tag --push

# Then build and publish in CI
```

### CI/CD Release

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  id-token: write
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for changelog

      - name: Install hwb
        run: pip install headless-wheel-builder

      - name: Generate release notes
        run: hwb version changelog --format github > RELEASE.md

      - name: Build
        run: hwb build --sdist

      - name: Publish to PyPI
        run: hwb publish --trusted-publisher

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          body_path: RELEASE.md
          files: dist/*
```

---

## Dynamic Versioning

### From Git Tags

Use git tags as the single source of truth.

```toml
# pyproject.toml
[project]
dynamic = ["version"]

[tool.hatch.version]
source = "vcs"

# For setuptools
[tool.setuptools_scm]
```

**How it works**:
```bash
git tag v1.0.0
python -m build
# Version: 1.0.0

git commit -m "fix: something"
python -m build
# Version: 1.0.1.dev1+g1234567
```

### From Environment

```toml
[project]
dynamic = ["version"]

[tool.hatch.version]
source = "env"
variable = "PACKAGE_VERSION"
```

```bash
export PACKAGE_VERSION=1.0.0
hwb build
```

---

## Version Validation

### Check Version

```bash
# Validate version format
hwb version check

# Checks:
# ✓ PEP 440 compliant
# ✓ Version files in sync
# ✓ Version not already published
```

### Pre-publish Validation

```bash
# Check if version exists on PyPI
hwb version check --pypi

# Output:
# Version 1.0.0 status:
#   PyPI: not published ✓
#   TestPyPI: not published ✓
```

---

## Version History

### View History

```bash
# Show version history from git tags
hwb version history

# Output:
# v1.2.0  2026-01-20  feat: add feature X
# v1.1.0  2026-01-15  feat: add feature Y
# v1.0.0  2026-01-01  Initial release
```

### Compare Versions

```bash
# Changes between versions
hwb version diff v1.0.0 v1.1.0

# Commits since last release
hwb version diff --unreleased
```

---

## Troubleshooting

### "Version files out of sync"

```bash
# Sync all version files
hwb version sync

# Or manually check
hwb version check --verbose
```

### "Invalid PEP 440 version"

```bash
# Check version format
python -c "from packaging.version import Version; Version('1.0.0-beta')"
# Error: Invalid version

# Use correct format
python -c "from packaging.version import Version; Version('1.0.0b1')"
# OK
```

### "Tag already exists"

```bash
# Delete local tag
git tag -d v1.0.0

# Delete remote tag
git push origin :refs/tags/v1.0.0

# Re-create
hwb version bump patch --tag
```

---

## Changelog

| Date | Changes |
|------|---------|
| 2026-01-23 | Initial versioning documentation |
