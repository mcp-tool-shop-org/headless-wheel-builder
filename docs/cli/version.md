# Version Commands

Version management and changelog generation.

## Commands

- `hwb version` - Show hwb version
- `hwb version-next` - Calculate next semantic version

---

## version

Show the installed hwb version.

### Synopsis

```bash
hwb version
```

### Output

```
hwb version 0.1.0
```

---

## version-next

Calculate the next semantic version based on Conventional Commits.

### Synopsis

```bash
hwb version-next [OPTIONS]
```

### Description

Analyzes git commits since the last tag using Conventional Commits format to determine the appropriate version bump (major, minor, or patch). Can optionally create and push git tags.

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `-p, --path PATH` | `.` | Path to git repository |
| `--tag-prefix PREFIX` | `v` | Tag prefix (e.g., `v` for `v1.0.0`) |
| `--dry-run` | Off | Show what would happen without making changes |
| `--tag` | Off | Create git tag |
| `--push` | Off | Push tag to remote |
| `--changelog` | Off | Generate changelog |

### Examples

#### Check Next Version

```bash
# Show next version
hwb version-next

# From specific directory
hwb version-next --path /path/to/repo
```

Output:
```
Current version: 1.2.3
Next version: 1.3.0
Bump type: minor
Commits: 5
```

#### Create Tags

```bash
# Create git tag
hwb version-next --tag

# Create and push tag
hwb version-next --tag --push

# Dry run (preview without creating)
hwb version-next --tag --dry-run
```

#### Custom Tag Prefix

```bash
# Use 'release-' prefix instead of 'v'
hwb version-next --tag-prefix release-
# Creates: release-1.3.0

# No prefix
hwb version-next --tag-prefix ""
# Creates: 1.3.0
```

#### Generate Changelog

```bash
# Print changelog to stdout
hwb version-next --changelog

# Save to file
hwb version-next --changelog > CHANGELOG.md
```

Output:
```markdown
## [1.3.0] - 2024-01-15

### Features

- Add OAuth2 authentication support (abc123)
- Implement user preferences API (def456)

### Bug Fixes

- Fix login timeout issue (789abc)
```

#### JSON Output

```bash
hwb version-next --json
```

```json
{
  "current": "1.2.3",
  "next": "1.3.0",
  "bump": "minor",
  "commits": 5,
  "tag": "v1.3.0"
}
```

With `--changelog`:

```json
{
  "current": "1.2.3",
  "next": "1.3.0",
  "bump": "minor",
  "commits": 5,
  "tag": "v1.3.0",
  "changelog": "## [1.3.0] - 2024-01-15\n\n..."
}
```

### Version Bump Rules

Based on Conventional Commits:

| Commit Type | Bump | Example |
|-------------|------|---------|
| `feat` | minor | `feat: add login feature` |
| `fix` | patch | `fix: resolve crash` |
| `feat!` or `BREAKING CHANGE:` | major | `feat!: redesign API` |
| `docs`, `style`, `refactor`, `test`, `ci`, `chore` | none | `docs: update readme` |

Priority order: major > minor > patch

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (not a git repo, no commits, etc.) |

### CI/CD Integration

#### GitHub Actions

```yaml
name: Release

on:
  push:
    branches: [main]

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for version calculation

      - name: Check for release
        id: version
        run: |
          VERSION=$(hwb version-next --json | jq -r '.next')
          HAS_CHANGES=$(hwb version-next --json | jq -r '.next != null')
          echo "version=$VERSION" >> $GITHUB_OUTPUT
          echo "has_changes=$HAS_CHANGES" >> $GITHUB_OUTPUT

      - name: Create release
        if: steps.version.outputs.has_changes == 'true'
        run: hwb version-next --tag --push
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

#### GitLab CI

```yaml
release:
  stage: release
  script:
    - |
      if hwb version-next --json | jq -e '.next != null'; then
        hwb version-next --tag --push
      fi
  only:
    - main
```

## See Also

- [Versioning Guide](../guide/versioning.md) - Detailed versioning guide
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
