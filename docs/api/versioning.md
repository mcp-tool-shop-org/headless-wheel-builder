# Versioning API

The version module provides semantic versioning, conventional commits parsing, git operations, and changelog generation.

## Overview

Components:

- **Version** - Semantic version representation
- **Commit** - Conventional commit parsing
- **Git Operations** - Tag management
- **Changelog** - Markdown changelog generation

## Quick Start

```python
from headless_wheel_builder.version import (
    # SemVer
    parse_version,
    bump_version,
    Version,
    BumpType,
    # Conventional Commits
    parse_commit,
    determine_bump_from_commits,
    Commit,
    CommitType,
    # Git
    get_latest_tag,
    get_commits_since_tag,
    create_tag,
    # Changelog
    generate_changelog,
)

# Parse and bump version
v = parse_version("1.2.3")
next_v = v.bump("minor")  # 1.3.0

# Parse commits
commit = parse_commit("feat(api): add new endpoint")
print(commit.type)   # CommitType.FEAT
print(commit.scope)  # "api"

# Get commits since last tag
tag = await get_latest_tag(".")
commits = await get_commits_since_tag(".", tag.name)

# Determine version bump
parsed = [parse_commit(msg) for _, msg in commits]
bump = determine_bump_from_commits(parsed)

# Generate changelog
changelog = generate_changelog(parsed, version="1.3.0")
```

---

## Semantic Versioning

### Version

Semantic version representation following [SemVer 2.0.0](https://semver.org/).

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `major` | `int` | Major version |
| `minor` | `int` | Minor version |
| `patch` | `int` | Patch version |
| `prerelease` | `str \| None` | Prerelease identifier |
| `build` | `str \| None` | Build metadata |

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `is_prerelease` | `bool` | Has prerelease |
| `is_stable` | `bool` | >= 1.0.0 and not prerelease |
| `base_version` | `Version` | Without prerelease/build |

#### Methods

##### bump()

```python
def bump(bump_type: BumpType | str) -> Version
```

Create new version with specified bump.

##### with_prerelease()

```python
def with_prerelease(prerelease: str) -> Version
```

Add prerelease identifier.

##### with_build()

```python
def with_build(build: str) -> Version
```

Add build metadata.

##### to_pep440()

```python
def to_pep440() -> str
```

Convert to PEP 440 format.

#### Example

```python
from headless_wheel_builder.version import Version, parse_version

# Create directly
v = Version(1, 2, 3)
print(str(v))  # "1.2.3"

# With prerelease
v = Version(2, 0, 0, prerelease="alpha.1")
print(str(v))  # "2.0.0-alpha.1"
print(v.is_prerelease)  # True

# Bump versions
v = Version(1, 2, 3)
print(v.bump("patch"))  # 1.2.4
print(v.bump("minor"))  # 1.3.0
print(v.bump("major"))  # 2.0.0

# Prerelease workflow
v = Version(1, 0, 0)
alpha = v.bump("minor").with_prerelease("alpha.1")  # 1.1.0-alpha.1
alpha2 = alpha.bump("prerelease")  # 1.1.0-alpha.2
beta = alpha2.base_version.with_prerelease("beta.1")  # 1.1.0-beta.1
stable = beta.base_version  # 1.1.0

# PEP 440
v = Version(1, 0, 0, prerelease="alpha.1")
print(v.to_pep440())  # "1.0.0a1"
```

---

### BumpType

Enum for version bump types.

| Value | Description |
|-------|-------------|
| `MAJOR` | Breaking changes |
| `MINOR` | New features |
| `PATCH` | Bug fixes |
| `PRERELEASE` | Prerelease increment |
| `BUILD` | Build metadata |

---

### parse_version()

```python
def parse_version(version_str: str, strict: bool = False) -> Version
```

Parse version string.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `version_str` | `str` | - | Version string |
| `strict` | `bool` | `False` | Require strict SemVer |

**Returns:** `Version`

**Example:**

```python
# Standard versions
parse_version("1.2.3")        # Version(1, 2, 3)
parse_version("v2.0.0")       # Version(2, 0, 0)

# With prerelease
parse_version("1.0.0-alpha.1")  # Version(1, 0, 0, prerelease="alpha.1")

# With build metadata
parse_version("1.0.0+build.123")  # Version(1, 0, 0, build="build.123")

# Relaxed parsing
parse_version("1.0")          # Version(1, 0, 0)
parse_version("2.0.0-beta1")  # Version(2, 0, 0, prerelease="beta1")
```

---

### bump_version()

```python
def bump_version(
    version: str | Version,
    bump_type: BumpType | str,
) -> Version
```

Bump a version.

**Example:**

```python
bump_version("1.2.3", "patch")  # Version(1, 2, 4)
bump_version("1.2.3", "minor")  # Version(1, 3, 0)
bump_version("1.2.3", BumpType.MAJOR)  # Version(2, 0, 0)
```

---

### compare_versions()

```python
def compare_versions(v1: str | Version, v2: str | Version) -> int
```

Compare two versions.

**Returns:** `-1` if v1 < v2, `0` if equal, `1` if v1 > v2

---

## Conventional Commits

### Commit

Parsed conventional commit.

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `type` | `CommitType \| str` | Commit type |
| `description` | `str` | Commit description |
| `scope` | `str \| None` | Commit scope |
| `body` | `str \| None` | Commit body |
| `footers` | `dict[str, str]` | Footer key-values |
| `breaking` | `bool` | Is breaking change |
| `breaking_description` | `str \| None` | Breaking change description |
| `raw_message` | `str` | Original message |
| `hash` | `str \| None` | Git commit hash |

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `is_conventional` | `bool` | Follows conventional format |
| `bump_type` | `BumpType \| None` | Version bump for this commit |

---

### CommitType

Enum for conventional commit types.

| Value | Description | Version Bump |
|-------|-------------|--------------|
| `FEAT` | New feature | Minor |
| `FIX` | Bug fix | Patch |
| `DOCS` | Documentation | None |
| `STYLE` | Formatting | None |
| `REFACTOR` | Code refactoring | Patch |
| `PERF` | Performance | Patch |
| `TEST` | Testing | None |
| `BUILD` | Build system | None |
| `CI` | CI configuration | None |
| `CHORE` | Maintenance | None |
| `REVERT` | Revert commit | Patch |

---

### parse_commit()

```python
def parse_commit(message: str, hash: str | None = None) -> Commit
```

Parse a commit message.

**Example:**

```python
# Basic commit
commit = parse_commit("feat: add login feature")
print(commit.type)        # CommitType.FEAT
print(commit.description) # "add login feature"

# With scope
commit = parse_commit("fix(api): handle null response")
print(commit.scope)  # "api"

# Breaking change
commit = parse_commit("feat!: redesign API")
print(commit.breaking)  # True

# With footer
commit = parse_commit("""feat: change response format

BREAKING CHANGE: Response now returns data directly.
""")
print(commit.breaking)  # True
print(commit.breaking_description)  # "Response now returns data directly."
```

---

### determine_bump_from_commits()

```python
def determine_bump_from_commits(commits: Sequence[Commit]) -> BumpType | None
```

Determine version bump from commits.

**Priority:** Major (breaking) > Minor (feat) > Patch (fix/perf)

**Example:**

```python
commits = [
    parse_commit("feat: new feature"),
    parse_commit("fix: bug fix"),
    parse_commit("docs: update readme"),
]
bump = determine_bump_from_commits(commits)
print(bump)  # BumpType.MINOR

# Breaking change takes precedence
commits = [
    parse_commit("feat!: breaking change"),
    parse_commit("feat: new feature"),
]
bump = determine_bump_from_commits(commits)
print(bump)  # BumpType.MAJOR
```

---

## Git Operations

### GitTag

Git tag information.

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Tag name |
| `version` | `Version \| None` | Parsed version |
| `commit_hash` | `str` | Commit hash |
| `message` | `str \| None` | Tag message |

---

### get_latest_tag()

```python
async def get_latest_tag(
    repo_path: Path | str = ".",
    pattern: str = "v*",
    include_prereleases: bool = True,
) -> GitTag | None
```

Get latest version tag.

**Example:**

```python
tag = await get_latest_tag(".", pattern="v*")
if tag:
    print(f"Latest: {tag.name} ({tag.version})")
    print(f"Commit: {tag.commit_hash}")
```

---

### get_commits_since_tag()

```python
async def get_commits_since_tag(
    repo_path: Path | str = ".",
    tag: str | None = None,
    include_hash: bool = True,
) -> list[tuple[str, str]]
```

Get commits since a tag.

**Returns:** List of `(hash, message)` tuples.

**Example:**

```python
commits = await get_commits_since_tag(".", tag="v1.0.0")
for hash, message in commits:
    print(f"{hash[:7]}: {message.split(chr(10))[0]}")
```

---

### create_tag()

```python
async def create_tag(
    repo_path: Path | str = ".",
    tag_name: str = "",
    message: str | None = None,
    commit: str = "HEAD",
    sign: bool = False,
    force: bool = False,
) -> GitTag
```

Create a git tag.

**Example:**

```python
tag = await create_tag(
    ".",
    tag_name="v1.2.0",
    message="Release 1.2.0",
)
print(f"Created: {tag.name}")
```

---

### push_tag()

```python
async def push_tag(
    repo_path: Path | str = ".",
    tag_name: str = "",
    remote: str = "origin",
    force: bool = False,
) -> None
```

Push tag to remote.

---

### Other Git Functions

```python
# Get current branch
branch = await get_current_branch(".")

# Get HEAD commit
head = await get_head_commit(".")

# Check for uncommitted changes
dirty = await is_dirty(".")
```

---

## Changelog

### generate_changelog()

```python
def generate_changelog(
    commits: Sequence[Commit],
    version: Version | str,
    previous_version: Version | str | None = None,
    release_date: date | None = None,
    repo_url: str | None = None,
    include_hash: bool = True,
    group_by_scope: bool = False,
) -> str
```

Generate markdown changelog.

**Example:**

```python
from datetime import date
from headless_wheel_builder.version import (
    parse_commit,
    generate_changelog,
)

commits = [
    parse_commit("feat(api): add user endpoint", "abc123"),
    parse_commit("fix(auth): token expiration", "def456"),
    parse_commit("docs: update readme", "789abc"),
]

changelog = generate_changelog(
    commits=commits,
    version="1.2.0",
    previous_version="1.1.0",
    release_date=date(2024, 1, 15),
    repo_url="https://github.com/user/repo",
)

print(changelog)
```

**Output:**

```markdown
## [1.2.0](https://github.com/user/repo/compare/v1.1.0...v1.2.0) (2024-01-15)

### Features

- **api:** add user endpoint ([abc123](https://github.com/user/repo/commit/abc123))

### Bug Fixes

- **auth:** token expiration ([def456](https://github.com/user/repo/commit/def456))

### Documentation

- update readme (789abc)
```

---

### ChangelogEntry

Changelog entry for a version.

| Attribute | Type | Description |
|-----------|------|-------------|
| `version` | `Version \| str` | Version |
| `date` | `date \| None` | Release date |
| `commits` | `list[Commit]` | Commits |
| `breaking_changes` | `list[Commit]` | Breaking changes |
| `compare_url` | `str \| None` | Compare URL |

---

### generate_full_changelog()

```python
def generate_full_changelog(
    entries: Sequence[ChangelogEntry],
    title: str = "Changelog",
    description: str | None = None,
    repo_url: str | None = None,
    include_hash: bool = True,
) -> str
```

Generate complete changelog from multiple entries.

---

### create_changelog_entry()

```python
def create_changelog_entry(
    version: Version | str,
    commits: Sequence[Commit],
    release_date: date | None = None,
) -> ChangelogEntry
```

Create changelog entry from commits.

---

## Complete Example

```python
import asyncio
from pathlib import Path
from headless_wheel_builder.version import (
    get_latest_tag,
    get_commits_since_tag,
    parse_commit,
    determine_bump_from_commits,
    generate_changelog,
    create_tag,
    push_tag,
)

async def release():
    repo = Path(".")

    # Get current version
    tag = await get_latest_tag(repo)
    current = tag.version if tag else parse_version("0.0.0")

    # Get and parse commits
    raw_commits = await get_commits_since_tag(repo, tag.name if tag else None)
    commits = [parse_commit(msg, hash) for hash, msg in raw_commits]

    if not commits:
        print("No new commits")
        return

    # Determine bump
    bump = determine_bump_from_commits(commits)
    if not bump:
        print("No version bump needed")
        return

    # Calculate next version
    next_version = current.bump(bump)
    print(f"Bumping {current} -> {next_version} ({bump.value})")

    # Generate changelog
    changelog = generate_changelog(
        commits=commits,
        version=next_version,
        previous_version=current,
    )
    print(changelog)

    # Create and push tag
    tag_name = f"v{next_version}"
    await create_tag(repo, tag_name, message=f"Release {next_version}")
    await push_tag(repo, tag_name)

    print(f"Created and pushed {tag_name}")

asyncio.run(release())
```
