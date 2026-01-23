# Source Types

Headless Wheel Builder can build from multiple source types.

## Local Paths

### Directory

Build from any directory containing a Python project:

```bash
hwb build /path/to/project
hwb build ./relative/path
hwb build .
```

Requirements:
- Must contain `pyproject.toml` or `setup.py`
- Directory must exist and be readable

### Local Archive

Build from a local source distribution:

```bash
hwb build ./downloads/package-1.0.0.tar.gz
hwb build /path/to/package-1.0.0.zip
```

Supported formats:
- `.tar.gz` / `.tgz`
- `.tar.bz2`
- `.zip`

## Git Repositories

### GitHub

```bash
# HTTPS (most common)
hwb build https://github.com/user/repo

# With specific ref
hwb build https://github.com/user/repo@v1.0.0
hwb build https://github.com/user/repo@main
hwb build https://github.com/user/repo@abc123def
```

### GitLab

```bash
hwb build https://gitlab.com/user/repo
hwb build https://gitlab.com/user/repo@v2.0.0
```

### Bitbucket

```bash
hwb build https://bitbucket.org/user/repo
hwb build https://bitbucket.org/user/repo@release-1.0
```

### SSH URLs

For private repositories:

```bash
hwb build git@github.com:user/private-repo.git
hwb build git@github.com:user/private-repo.git@v1.0.0
```

!!! note
    SSH URLs require SSH keys configured for the git host.

### Git Refs

You can specify any git ref after the `@` symbol:

| Ref Type | Example |
|----------|---------|
| Tag | `@v1.0.0`, `@1.0.0`, `@release-2023` |
| Branch | `@main`, `@develop`, `@feature/new-api` |
| Commit | `@abc123def`, `@a1b2c3d4e5f6` |

### Private Repositories

For private repos, ensure authentication is configured:

**SSH (recommended):**
```bash
# Ensure SSH key is added
ssh-add ~/.ssh/id_ed25519

# Build
hwb build git@github.com:org/private-repo.git@v1.0.0
```

**HTTPS with token:**
```bash
# Set credential helper or use URL with token
hwb build https://oauth2:${GITHUB_TOKEN}@github.com/org/private-repo.git
```

## Monorepos

For repositories with multiple packages, use the `#subdirectory=` fragment:

```bash
# Package in packages/core
hwb build https://github.com/org/monorepo#subdirectory=packages/core

# Package in src/mylib
hwb build https://github.com/org/monorepo@v1.0.0#subdirectory=src/mylib
```

## Remote Archives

Build directly from archive URLs:

```bash
# GitHub releases
hwb build https://github.com/user/repo/archive/refs/tags/v1.0.0.tar.gz

# PyPI sdists
hwb build https://files.pythonhosted.org/packages/.../package-1.0.0.tar.gz

# Custom URLs
hwb build https://example.com/releases/mypackage-2.0.0.tar.gz
```

Supported archive formats:
- `.tar.gz` / `.tgz`
- `.tar.bz2`
- `.zip`

## Source Caching

Git clones are cached in `~/.cache/hwb/sources/` to speed up repeated builds.

### Cache Location

| OS | Default Cache Path |
|----|--------------------|
| Linux | `~/.cache/hwb/sources/` |
| macOS | `~/Library/Caches/hwb/sources/` |
| Windows | `%LOCALAPPDATA%\hwb\sources\` |

### Clear Cache

To clear the source cache:

```bash
rm -rf ~/.cache/hwb/sources/
```

## Source Resolution Order

When resolving a source string, the following order is used:

1. **Git SSH** - Strings starting with `git@`
2. **Git HTTPS** - URLs containing `github.com`, `gitlab.com`, or `bitbucket.org`
3. **Remote Archive** - HTTP(S) URLs ending in `.tar.gz`, `.tgz`, `.zip`, `.tar.bz2`
4. **Local Archive** - Local paths ending in archive extensions
5. **Local Directory** - Any existing directory path

## Programmatic Usage

```python
from headless_wheel_builder.core.source import SourceResolver, SourceType

resolver = SourceResolver()

# Parse source string
spec = resolver.parse_source("https://github.com/user/repo@v1.0.0")
print(spec.type)        # SourceType.GIT_HTTPS
print(spec.location)    # https://github.com/user/repo
print(spec.ref)         # v1.0.0

# Resolve to local path
source = await resolver.resolve(spec)
print(source.local_path)   # /path/to/cloned/repo
print(source.is_temporary) # True (will be cleaned up)
print(source.commit_hash)  # abc123def...

# Use as context manager for automatic cleanup
async with resolver.resolve(spec) as source:
    # Build from source.local_path
    pass
# Temporary files cleaned up
```

## Error Handling

### Common Errors

**Source not found:**
```
SourceError: Path does not exist: /nonexistent/path
```

**Invalid git URL:**
```
SourceError: Cannot determine source type for: not-a-valid-source
```

**Clone failed:**
```
GitError: Failed to clone: repository not found
```

**No project files:**
```
SourceError: No pyproject.toml or setup.py found in: /path/to/dir
```
