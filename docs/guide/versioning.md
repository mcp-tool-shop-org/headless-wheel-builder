# Versioning

Headless Wheel Builder provides automated versioning based on [Semantic Versioning](https://semver.org/) and [Conventional Commits](https://www.conventionalcommits.org/).

## Quick Start

### Check Next Version

From a git repository:

```bash
hwb version-next
```

Output:
```
Current version: 1.2.3 (from tag v1.2.3)

Commits since v1.2.3:
  feat: add new feature
  fix: resolve bug
  docs: update readme

Recommended bump: minor
Next version: 1.3.0
```

### Create and Push Tag

```bash
hwb version-next --tag --push
```

### Generate Changelog

```bash
hwb version-next --changelog
```

## Semantic Versioning

SemVer uses three numbers: `MAJOR.MINOR.PATCH`

| Version Part | When to Increment |
|--------------|-------------------|
| MAJOR | Breaking changes (incompatible API changes) |
| MINOR | New features (backwards compatible) |
| PATCH | Bug fixes (backwards compatible) |

### Prerelease Versions

For development releases:

```
1.0.0-alpha.1    # Alpha release
1.0.0-beta.1     # Beta release
1.0.0-rc.1       # Release candidate
```

### Build Metadata

Additional information:

```
1.0.0+build.123      # With build number
1.0.0-rc.1+sha.abc   # Prerelease with commit
```

## Conventional Commits

Conventional Commits provide a structured format for commit messages:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Commit Types

| Type | Description | Version Bump |
|------|-------------|--------------|
| `feat` | New feature | Minor |
| `fix` | Bug fix | Patch |
| `docs` | Documentation only | None |
| `style` | Code style (formatting) | None |
| `refactor` | Code refactoring | None |
| `perf` | Performance improvement | Patch |
| `test` | Adding tests | None |
| `build` | Build system changes | None |
| `ci` | CI configuration | None |
| `chore` | Maintenance tasks | None |

### Breaking Changes

Breaking changes trigger a MAJOR version bump:

```
feat!: remove deprecated API

# or with footer
feat: change response format

BREAKING CHANGE: Response now returns data directly instead of wrapped.
```

### Scoped Commits

Add scope for more context:

```
feat(auth): add OAuth2 support
fix(api): handle null responses
docs(readme): add installation section
```

## Command Usage

### Basic Usage

```bash
# Show next version
hwb version-next

# From specific directory
hwb version-next --path /path/to/repo
```

### Create Git Tag

```bash
# Create tag
hwb version-next --tag

# Create and push tag
hwb version-next --tag --push
```

### Dry Run

Preview without making changes:

```bash
hwb version-next --dry-run
```

### Custom Tag Prefix

Default prefix is `v`:

```bash
# Use different prefix
hwb version-next --tag-prefix release-

# No prefix
hwb version-next --tag-prefix ""
```

### Generate Changelog

```bash
# Print to stdout
hwb version-next --changelog

# Save to file
hwb version-next --changelog > CHANGELOG.md
```

## Changelog Format

Generated changelogs follow [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
## [1.3.0] - 2024-01-15

### Features

- Add OAuth2 authentication support ([abc123](https://github.com/...))
- Implement user preferences API ([def456](https://github.com/...))

### Bug Fixes

- Fix login timeout issue ([789abc](https://github.com/...))

### Breaking Changes

- Remove deprecated v1 API endpoints ([xyz789](https://github.com/...))

[1.3.0]: https://github.com/user/repo/compare/v1.2.3...v1.3.0
```

## Workflow Examples

### Feature Release

```bash
# 1. Make commits
git commit -m "feat: add user profiles"
git commit -m "feat: add settings page"
git commit -m "fix: profile image upload"

# 2. Check version
hwb version-next
# Output: 1.2.3 → 1.3.0 (minor bump)

# 3. Create release
hwb version-next --tag --push --changelog
```

### Breaking Change Release

```bash
# 1. Make breaking change
git commit -m "feat!: redesign API response format"

# 2. Check version
hwb version-next
# Output: 1.2.3 → 2.0.0 (major bump)

# 3. Create release
hwb version-next --tag --push
```

### Prerelease Workflow

```python
from headless_wheel_builder.version.semver import parse_version

# Start with current stable
current = parse_version("1.0.0")

# Create alpha
alpha1 = current.bump("minor").with_prerelease("alpha.1")
print(alpha1)  # 1.1.0-alpha.1

# Bump alpha
alpha2 = alpha1.bump("prerelease")
print(alpha2)  # 1.1.0-alpha.2

# Move to beta
beta1 = alpha2.base_version.with_prerelease("beta.1")
print(beta1)  # 1.1.0-beta.1

# Release stable
stable = beta1.base_version
print(stable)  # 1.1.0
```

## Programmatic Usage

### Parse Versions

```python
from headless_wheel_builder.version.semver import (
    parse_version,
    bump_version,
    compare_versions,
    Version,
)

# Parse version string
v = parse_version("1.2.3")
print(v.major, v.minor, v.patch)  # 1 2 3

# With prerelease
v2 = parse_version("2.0.0-beta.1")
print(v2.prerelease)  # beta.1
print(v2.is_prerelease)  # True

# Bump version
v3 = v.bump("minor")
print(v3)  # 1.3.0

# Compare versions
result = compare_versions("1.0.0", "2.0.0")
print(result)  # -1 (first is less)
```

### Parse Commits

```python
from headless_wheel_builder.version.conventional import (
    parse_commit,
    determine_bump_from_commits,
)

# Parse single commit
commit = parse_commit("feat(api): add new endpoint")
print(commit.type)        # CommitType.FEAT
print(commit.scope)       # api
print(commit.description) # add new endpoint
print(commit.breaking)    # False

# Parse breaking change
breaking = parse_commit("feat!: remove deprecated API")
print(breaking.breaking)  # True

# Determine bump from commits
commits = [
    parse_commit("feat: new feature"),
    parse_commit("fix: bug fix"),
]
bump = determine_bump_from_commits(commits)
print(bump)  # BumpType.MINOR
```

### Git Operations

```python
from headless_wheel_builder.version.git import (
    get_latest_tag,
    get_commits_since_tag,
    create_tag,
)

# Get latest version tag
tag = await get_latest_tag("/path/to/repo")
print(tag.name)     # v1.2.3
print(tag.version)  # Version(1, 2, 3)

# Get commits since tag
commits = await get_commits_since_tag("/path/to/repo", tag="v1.2.3")
for hash, message in commits:
    print(f"{hash[:7]}: {message}")

# Create new tag
new_tag = await create_tag(
    "/path/to/repo",
    tag_name="v1.3.0",
    message="Release 1.3.0",
)
```

### Generate Changelog

```python
from headless_wheel_builder.version.changelog import (
    generate_changelog,
    create_changelog_entry,
)
from datetime import date

# Generate markdown changelog
changelog = generate_changelog(
    commits=[...],
    version="1.3.0",
    previous_version="1.2.3",
    release_date=date.today(),
    repo_url="https://github.com/user/repo",
)
print(changelog)
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Release

on:
  push:
    branches: [main]

jobs:
  version:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.version }}
      should_release: ${{ steps.version.outputs.should_release }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Calculate version
        id: version
        run: |
          VERSION=$(hwb version-next --json | jq -r '.next_version')
          SHOULD_RELEASE=$(hwb version-next --json | jq -r '.has_changes')
          echo "version=$VERSION" >> $GITHUB_OUTPUT
          echo "should_release=$SHOULD_RELEASE" >> $GITHUB_OUTPUT

  release:
    needs: version
    if: needs.version.outputs.should_release == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Create release
        run: hwb version-next --tag --push
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Best Practices

1. **Use Conventional Commits** consistently for automatic versioning
2. **Tag releases** to mark version points clearly
3. **Generate changelogs** for users to understand changes
4. **Test on TestPyPI** before releasing to PyPI
5. **Use prereleases** for testing before stable releases
6. **Automate in CI/CD** for consistent releases
