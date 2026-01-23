# Headless Wheel Builder - API Documentation

> **Purpose**: Complete specification of CLI commands and Python API for programmatic usage.
> **Last Updated**: 2026-01-23

---

## 2026 Best Practices Applied

> **Sources**: [Click Documentation](https://click.palletsprojects.com/), [Typer Modern CLI](https://typer.tiangolo.com/), [Rich Terminal Output](https://rich.readthedocs.io/), [Python Packaging User Guide](https://packaging.python.org/), [12-Factor CLI Apps](https://medium.com/@jdxcode/12-factor-cli-apps-dd3c227a0e46)

This API follows 2026 CLI and Python library best practices:

1. **Explicit Over Implicit**: All options have sensible defaults but can be overridden. No hidden magic.

2. **Progressive Disclosure**: Simple use cases are simple. Advanced options available when needed.

3. **Machine-Readable Output**: JSON output mode for CI/CD integration. Human-friendly by default.

4. **Fail Fast, Fail Clearly**: Validation happens early. Error messages include remediation steps.

5. **Composable Commands**: Each command does one thing well. Commands can be combined in scripts.

6. **Async-First Python API**: All I/O-bound operations are async for maximum throughput.

7. **Type-Annotated**: Full type hints for IDE support and static analysis.

8. **Configuration Precedence**: CLI flags > Environment variables > Config file > Defaults.

---

## CLI Reference

### Installation

```bash
# From PyPI
pip install headless-wheel-builder

# Or with uv (recommended)
uv pip install headless-wheel-builder

# Verify installation
hwb --version
```

### Global Options

```
hwb [OPTIONS] COMMAND [ARGS]...

Options:
  --version              Show version and exit
  --verbose, -v          Increase verbosity (can be repeated: -vv, -vvv)
  --quiet, -q            Suppress non-error output
  --config FILE          Path to configuration file
  --no-config            Ignore configuration files
  --json                 Output in JSON format (for scripting)
  --no-color             Disable colored output
  --help                 Show this message and exit

Commands:
  build      Build wheels from source
  publish    Publish wheels to a registry
  version    Manage package versions
  matrix     Build for multiple Python versions/platforms
  inspect    Analyze project configuration
  init       Initialize a new pyproject.toml
  cache      Manage build cache
```

---

### `hwb build`

Build wheels from local path or git repository.

```
hwb build [OPTIONS] [SOURCE]

Arguments:
  SOURCE  Source to build from. Can be:
          - Local path: /path/to/project or .
          - Git URL: https://github.com/user/repo
          - Git URL with ref: https://github.com/user/repo@v1.0.0
          - Git URL with subdir: https://github.com/user/repo#subdirectory=pkg
          [default: .]

Options:
  --output, -o DIR       Output directory for wheels [default: dist]
  --wheel/--no-wheel     Build wheel [default: --wheel]
  --sdist/--no-sdist     Build source distribution [default: --no-sdist]

Isolation Options:
  --isolation TYPE       Isolation strategy: auto, venv, docker, none
                         [default: auto]
  --python VERSION       Python version to use [default: 3.12]
  --no-isolation         Build without isolation (use host environment)

Docker Options (when --isolation=docker):
  --manylinux VERSION    manylinux version: 2014, 2_28, 2_34, 2_35
                         [default: 2_28]
  --musllinux VERSION    musllinux version: 1_2 [default: none]
  --platform PLATFORM    Target platform (e.g., linux/amd64)
  --gpu                  Enable GPU support in container

Build Options:
  --config-setting, -C   Pass config setting to build backend
                         Can be repeated: -C--opt=value -C--flag
  --no-build-isolation   Disable PEP 517 build isolation
  --skip-deps            Skip installing build dependencies

Output Options:
  --clean                Clean output directory before building
  --checksum             Generate SHA256 checksums
  --manifest             Generate build manifest (JSON)

Examples:
  # Build wheel from current directory
  hwb build

  # Build from git repository
  hwb build https://github.com/user/repo

  # Build specific version
  hwb build https://github.com/user/repo@v2.0.0

  # Build manylinux wheel
  hwb build --isolation docker --manylinux 2_28

  # Build for specific Python version
  hwb build --python 3.11

  # Build wheel and sdist with checksums
  hwb build --sdist --checksum
```

**Output (default)**:
```
Building wheel for mypackage...
  Source: /path/to/project
  Backend: hatchling
  Python: 3.12
  Isolation: venv

Installing build dependencies...
  hatchling>=1.26

Building wheel...
  Built: mypackage-1.0.0-py3-none-any.whl

Success! Wheel saved to dist/mypackage-1.0.0-py3-none-any.whl
```

**Output (JSON)**:
```json
{
  "success": true,
  "wheel": {
    "path": "dist/mypackage-1.0.0-py3-none-any.whl",
    "name": "mypackage",
    "version": "1.0.0",
    "python_tag": "py3",
    "abi_tag": "none",
    "platform_tag": "any",
    "size_bytes": 12345,
    "sha256": "abc123..."
  },
  "duration_seconds": 5.2,
  "build_log": "..."
}
```

---

### `hwb publish`

Publish wheels to PyPI or other registries.

```
hwb publish [OPTIONS] [FILES]...

Arguments:
  FILES  Wheel or sdist files to publish. If not specified,
         publishes all files in dist/ directory.

Options:
  --repository, -r NAME  Repository to publish to [default: pypi]
                         Built-in: pypi, testpypi
                         Or custom URL
  --url URL              Repository URL (overrides --repository)

Authentication:
  --trusted-publisher    Use OIDC Trusted Publisher (CI only)
  --token TOKEN          PyPI API token
  --username USER        Username (legacy, not recommended)
  --password PASS        Password (legacy, not recommended)

Options:
  --skip-existing        Don't fail if version already exists
  --dry-run              Validate but don't upload
  --sign                 Sign packages with GPG
  --attestation          Generate SLSA attestation (PyPI)

Examples:
  # Publish to PyPI using Trusted Publisher (in CI)
  hwb publish --trusted-publisher

  # Publish to PyPI with API token
  hwb publish --token $PYPI_TOKEN

  # Publish to TestPyPI for testing
  hwb publish --repository testpypi --token $TEST_PYPI_TOKEN

  # Publish specific files
  hwb publish dist/mypackage-1.0.0-py3-none-any.whl

  # Dry run (validate only)
  hwb publish --dry-run
```

**Output**:
```
Publishing to PyPI...
  Files: mypackage-1.0.0-py3-none-any.whl
  Authentication: Trusted Publisher (GitHub Actions)

Uploading mypackage-1.0.0-py3-none-any.whl... done

Success! Published to:
  https://pypi.org/project/mypackage/1.0.0/
```

---

### `hwb version`

Manage package versions with semantic versioning.

```
hwb version [OPTIONS] COMMAND

Commands:
  show       Show current version
  bump       Bump version (major/minor/patch)
  set        Set version explicitly
  tag        Create git tag for current version

hwb version show [OPTIONS]
  Show current version from pyproject.toml

hwb version bump [OPTIONS] PART
  Bump version. PART is: major, minor, patch, pre, post

  Options:
    --pre TYPE           Add pre-release: alpha, beta, rc
    --commit             Create git commit
    --tag                Create git tag
    --push               Push commit and tag
    --message, -m MSG    Custom commit message

  Examples:
    # Bump patch version (1.0.0 -> 1.0.1)
    hwb version bump patch

    # Bump minor with commit and tag
    hwb version bump minor --commit --tag

    # Create release candidate
    hwb version bump patch --pre rc

hwb version set [OPTIONS] VERSION
  Set version explicitly

  Options:
    --commit             Create git commit
    --tag                Create git tag

  Examples:
    hwb version set 2.0.0
    hwb version set 2.0.0rc1 --commit --tag

hwb version tag [OPTIONS]
  Create git tag for current version

  Options:
    --push               Push tag to remote
    --sign               Sign tag with GPG
    --message, -m MSG    Tag message
```

**Output**:
```
Current version: 1.2.3
Bumping patch version...
New version: 1.2.4

Updated:
  pyproject.toml
  src/mypackage/__init__.py

Created commit: Bump version to 1.2.4
Created tag: v1.2.4
```

---

### `hwb matrix`

Build for multiple Python versions and platforms.

```
hwb matrix [OPTIONS] [SOURCE]

Options:
  --python VERSIONS      Python versions to build for
                         [default: 3.9,3.10,3.11,3.12,3.13]
  --platform PLATFORMS   Platforms to build for
                         [default: linux,macos,windows]
  --arch ARCHITECTURES   Architectures to build for
                         [default: x86_64,aarch64]

  --only SPEC            Only build specific combination
                         Format: python-platform-arch
                         Example: 3.12-linux-x86_64

  --exclude SPEC         Exclude specific combination
  --parallel, -j N       Number of parallel builds [default: 4]

  --output, -o DIR       Output directory [default: dist]
  --config FILE          Matrix configuration file (YAML)

Examples:
  # Build for all default combinations
  hwb matrix

  # Build for specific Python versions
  hwb matrix --python 3.11,3.12

  # Build for Linux only
  hwb matrix --platform linux

  # Build with custom parallelism
  hwb matrix --parallel 8

  # Use configuration file
  hwb matrix --config matrix.yaml
```

**Matrix Configuration File (`matrix.yaml`)**:
```yaml
python:
  - "3.10"
  - "3.11"
  - "3.12"
  - "3.13"

platforms:
  linux:
    architectures: [x86_64, aarch64]
    manylinux: "2_28"
  macos:
    architectures: [x86_64, arm64]
    deployment_target: "11.0"
  windows:
    architectures: [x86_64]

exclude:
  - python: "3.10"
    platform: windows
    arch: aarch64

include:
  - python: "3.13"
    platform: linux
    arch: x86_64
    env:
      CFLAGS: "-O3"
```

**Output**:
```
Building matrix: 12 combinations
  Python: 3.10, 3.11, 3.12, 3.13
  Platforms: linux, macos, windows
  Running 4 parallel builds...

[============================] 12/12 complete

Results:
  ✓ 3.10-linux-x86_64     mypackage-1.0.0-cp310-cp310-manylinux_2_28_x86_64.whl
  ✓ 3.10-linux-aarch64    mypackage-1.0.0-cp310-cp310-manylinux_2_28_aarch64.whl
  ✓ 3.10-macos-x86_64     mypackage-1.0.0-cp310-cp310-macosx_11_0_x86_64.whl
  ... (9 more)

Built 12 wheels in 45.2s
```

---

### `hwb inspect`

Analyze project configuration.

```
hwb inspect [OPTIONS] [SOURCE]

Options:
  --format FORMAT        Output format: text, json, yaml [default: text]
  --check                Exit with error if issues found

Checks:
  --check-metadata       Validate PEP 621 metadata
  --check-backend        Validate build backend configuration
  --check-deps           Check for dependency issues
  --check-all            Run all checks
```

**Output**:
```
Project: mypackage
Version: 1.0.0
Path: /path/to/project

Build System:
  Backend: hatchling (hatchling.build)
  Requirements: hatchling>=1.26

Metadata (PEP 621):
  Name: mypackage
  Version: 1.0.0
  Requires-Python: >=3.9
  License: MIT
  Authors: 1 author(s)

Dependencies:
  Runtime: 3 packages
    - requests>=2.28
    - click>=8.0
    - rich>=13.0
  Optional Groups:
    dev: 5 packages
    test: 3 packages

Files:
  pyproject.toml: ✓ valid
  README.md: ✓ found
  LICENSE: ✓ found
  src/mypackage/__init__.py: ✓ found

Issues:
  ⚠ No py.typed marker (consider adding for type checking support)
```

---

### `hwb init`

Initialize a new pyproject.toml.

```
hwb init [OPTIONS] [PATH]

Options:
  --name NAME            Package name
  --version VERSION      Initial version [default: 0.1.0]
  --description DESC     Package description
  --author AUTHOR        Author name
  --email EMAIL          Author email
  --license LICENSE      License (MIT, Apache-2.0, GPL-3.0, etc.)

  --backend BACKEND      Build backend: hatchling, setuptools, flit, pdm
                         [default: hatchling]
  --src-layout           Use src/ layout [default: true]

  --interactive, -i      Interactive mode (prompt for values)
  --force                Overwrite existing pyproject.toml

Examples:
  # Interactive initialization
  hwb init -i

  # Non-interactive with options
  hwb init --name mypackage --author "John Doe" --license MIT

  # Initialize in specific directory
  hwb init /path/to/project
```

---

### `hwb cache`

Manage the build cache.

```
hwb cache [OPTIONS] COMMAND

Commands:
  show       Show cache statistics
  clean      Remove cached items
  path       Show cache directory path

hwb cache show
  Show cache size and contents

hwb cache clean [OPTIONS]
  Options:
    --all                Remove all cached items
    --wheels             Remove cached wheels only
    --envs               Remove cached environments only
    --older-than DAYS    Remove items older than N days
```

---

## Python API

### Installation

```python
pip install headless-wheel-builder
```

### Basic Usage

```python
import asyncio
from headless_wheel_builder import build_wheel, publish

async def main():
    # Build a wheel
    result = await build_wheel(
        source=".",
        output_dir="dist",
        python="3.12"
    )

    if result.success:
        print(f"Built: {result.wheel_path}")

        # Publish to PyPI
        pub_result = await publish(
            result.wheel_path,
            repository="pypi",
            trusted_publisher=True
        )

asyncio.run(main())
```

### API Reference

#### `build_wheel()`

Build a wheel from source.

```python
async def build_wheel(
    source: str | Path = ".",
    *,
    output_dir: str | Path = "dist",
    python: str = "3.12",
    isolation: Literal["auto", "venv", "docker", "none"] = "auto",
    wheel: bool = True,
    sdist: bool = False,
    manylinux: str | None = None,
    musllinux: str | None = None,
    config_settings: dict[str, str] | None = None,
    clean: bool = False,
) -> BuildResult:
    """
    Build a wheel from source.

    Args:
        source: Path to project or git URL
        output_dir: Directory for output files
        python: Python version to use
        isolation: Isolation strategy
        wheel: Build wheel
        sdist: Build source distribution
        manylinux: manylinux version (implies docker isolation)
        musllinux: musllinux version (implies docker isolation)
        config_settings: Settings to pass to build backend
        clean: Clean output directory first

    Returns:
        BuildResult with wheel path and metadata

    Raises:
        BuildError: If build fails
        SourceError: If source cannot be resolved
    """
```

#### `BuildResult`

```python
@dataclass
class BuildResult:
    """Result of a build operation."""
    success: bool
    wheel_path: Path | None = None
    sdist_path: Path | None = None
    build_log: str = ""
    duration_seconds: float = 0.0
    error: str | None = None

    # Wheel metadata (if successful)
    name: str | None = None
    version: str | None = None
    python_tag: str | None = None
    abi_tag: str | None = None
    platform_tag: str | None = None
    sha256: str | None = None
```

#### `publish()`

Publish wheel to a registry.

```python
async def publish(
    *files: str | Path,
    repository: str = "pypi",
    url: str | None = None,
    trusted_publisher: bool = False,
    token: str | None = None,
    skip_existing: bool = False,
    dry_run: bool = False,
) -> PublishResult:
    """
    Publish wheel(s) to a package registry.

    Args:
        files: Wheel or sdist files to publish
        repository: Repository name (pypi, testpypi) or URL
        url: Custom repository URL (overrides repository)
        trusted_publisher: Use OIDC authentication (CI only)
        token: API token for authentication
        skip_existing: Don't fail if version exists
        dry_run: Validate but don't upload

    Returns:
        PublishResult with upload status

    Raises:
        PublishError: If publish fails
        AuthenticationError: If authentication fails
    """
```

#### `PublishResult`

```python
@dataclass
class PublishResult:
    """Result of a publish operation."""
    success: bool
    repository_url: str
    package_url: str | None = None
    files_uploaded: list[str] = field(default_factory=list)
    output: str = ""
    error: str | None = None
```

#### `bump_version()`

Bump package version.

```python
async def bump_version(
    source: str | Path = ".",
    part: Literal["major", "minor", "patch", "pre", "post"] = "patch",
    *,
    pre: Literal["alpha", "beta", "rc"] | None = None,
    commit: bool = False,
    tag: bool = False,
    push: bool = False,
    message: str | None = None,
) -> VersionResult:
    """
    Bump package version.

    Args:
        source: Path to project
        part: Version part to bump
        pre: Pre-release type (alpha, beta, rc)
        commit: Create git commit
        tag: Create git tag
        push: Push commit and tag to remote
        message: Custom commit message

    Returns:
        VersionResult with old and new versions

    Raises:
        VersionError: If version bump fails
    """
```

#### `build_matrix()`

Build for multiple Python versions/platforms.

```python
async def build_matrix(
    source: str | Path = ".",
    *,
    output_dir: str | Path = "dist",
    python_versions: list[str] = ["3.9", "3.10", "3.11", "3.12", "3.13"],
    platforms: list[str] = ["linux", "macos", "windows"],
    architectures: list[str] = ["x86_64", "aarch64"],
    exclude: list[dict] | None = None,
    parallel: int = 4,
    on_build_complete: Callable[[BuildResult], None] | None = None,
) -> MatrixResult:
    """
    Build wheels for multiple Python versions and platforms.

    Args:
        source: Path to project
        output_dir: Directory for output files
        python_versions: Python versions to build for
        platforms: Platforms to build for
        architectures: Architectures to build for
        exclude: Combinations to exclude
        parallel: Number of parallel builds
        on_build_complete: Callback for each completed build

    Returns:
        MatrixResult with all build results
    """
```

#### `inspect_project()`

Analyze project configuration.

```python
async def inspect_project(
    source: str | Path = ".",
    *,
    check_metadata: bool = True,
    check_backend: bool = True,
    check_deps: bool = True,
) -> InspectResult:
    """
    Analyze project configuration.

    Args:
        source: Path to project
        check_metadata: Validate PEP 621 metadata
        check_backend: Validate build backend
        check_deps: Check dependencies

    Returns:
        InspectResult with project metadata and issues
    """
```

### Low-Level API

For advanced use cases, access the underlying components:

```python
from headless_wheel_builder.core import (
    SourceResolver,
    ProjectAnalyzer,
    BuildEngine,
)
from headless_wheel_builder.isolation import (
    VenvIsolation,
    DockerIsolation,
)
from headless_wheel_builder.publish import (
    PyPIPublisher,
    DevPiPublisher,
    S3Publisher,
)
from headless_wheel_builder.version import (
    VersionManager,
    ChangelogGenerator,
)

# Example: Custom build workflow
async def custom_build():
    # Resolve source
    resolver = SourceResolver()
    source = await resolver.resolve("https://github.com/user/repo@v1.0")

    # Analyze project
    analyzer = ProjectAnalyzer()
    metadata = await analyzer.analyze(source.local_path)

    # Build with custom isolation
    isolation = DockerIsolation(DockerConfig(
        manylinux_image="quay.io/pypa/manylinux_2_34_x86_64",
        enable_gpu=True
    ))

    engine = BuildEngine(isolation)
    result = await engine.build_wheel(
        source.local_path,
        metadata,
        python_version="3.12"
    )

    return result
```

---

## Configuration

### Configuration File

HWB reads configuration from `pyproject.toml` or `hwb.toml`.

**`pyproject.toml`**:
```toml
[tool.hwb]
# Default output directory
output-dir = "dist"

# Default isolation strategy
isolation = "auto"

# Default Python version
python = "3.12"

[tool.hwb.build]
# Always include sdist
sdist = true

# Generate checksums
checksum = true

[tool.hwb.publish]
# Default repository
repository = "pypi"

# Skip if version exists
skip-existing = true

[tool.hwb.matrix]
python = ["3.10", "3.11", "3.12", "3.13"]
platforms = ["linux", "macos", "windows"]

[tool.hwb.matrix.linux]
manylinux = "2_28"
architectures = ["x86_64", "aarch64"]

[tool.hwb.matrix.macos]
architectures = ["x86_64", "arm64"]
deployment-target = "11.0"

[tool.hwb.version]
# Files to update on version bump
files = [
    "pyproject.toml",
    "src/mypackage/__init__.py:__version__",
]

# Commit message template
commit-message = "chore: bump version to {new_version}"

# Tag format
tag-format = "v{version}"
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `HWB_OUTPUT_DIR` | Default output directory |
| `HWB_PYTHON` | Default Python version |
| `HWB_ISOLATION` | Default isolation strategy |
| `HWB_PARALLEL` | Default parallel build count |
| `HWB_CACHE_DIR` | Cache directory location |
| `PYPI_TOKEN` | PyPI API token |
| `TEST_PYPI_TOKEN` | TestPyPI API token |

### Precedence

1. CLI flags (highest)
2. Environment variables
3. `pyproject.toml` [tool.hwb]
4. `hwb.toml`
5. Built-in defaults (lowest)

---

## Error Codes

| Code | Name | Description |
|------|------|-------------|
| `HWB-001` | `SourceNotFound` | Source path or URL not found |
| `HWB-002` | `GitCloneFailed` | Failed to clone git repository |
| `HWB-003` | `InvalidProject` | No pyproject.toml or setup.py found |
| `HWB-004` | `BackendError` | Build backend raised an error |
| `HWB-005` | `IsolationError` | Failed to create isolated environment |
| `HWB-006` | `DependencyError` | Failed to install build dependencies |
| `HWB-007` | `WheelInvalid` | Built wheel failed validation |
| `HWB-008` | `PublishFailed` | Failed to upload to registry |
| `HWB-009` | `AuthError` | Authentication failed |
| `HWB-010` | `VersionError` | Version bump or tag failed |
| `HWB-011` | `DockerError` | Docker operation failed |
| `HWB-012` | `ConfigError` | Invalid configuration |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | Build failed |
| 4 | Publish failed |
| 5 | Authentication failed |
| 10 | Keyboard interrupt |

---

## Changelog

| Date | Changes |
|------|---------|
| 2026-01-23 | Initial API documentation |
