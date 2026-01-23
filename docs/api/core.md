# Core API

The core module provides the main building blocks for wheel building.

## Quick Start

```python
import asyncio
from headless_wheel_builder.core import (
    BuildEngine,
    BuildConfig,
    BuildResult,
    SourceResolver,
)

async def build_example():
    # Simple build
    engine = BuildEngine()
    result = await engine.build(".")

    if result.success:
        print(f"Built: {result.wheel_path}")
    else:
        print(f"Failed: {result.error}")

asyncio.run(build_example())
```

## BuildEngine

The main build engine that orchestrates the entire build process.

### Constructor

```python
BuildEngine(config: BuildConfig | None = None)
```

### Methods

#### build()

```python
async def build(
    source: str | Path | SourceSpec | ResolvedSource,
    output_dir: Path | None = None,
    python_version: str | None = None,
    wheel: bool = True,
    sdist: bool = False,
) -> BuildResult
```

Build wheel (and optionally sdist) from source.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `source` | `str \| Path \| SourceSpec \| ResolvedSource` | - | Source to build from |
| `output_dir` | `Path \| None` | From config | Output directory |
| `python_version` | `str \| None` | From config | Python version |
| `wheel` | `bool` | `True` | Build wheel |
| `sdist` | `bool` | `False` | Build source distribution |

**Returns:** `BuildResult`

**Example:**

```python
from pathlib import Path
from headless_wheel_builder.core import BuildEngine, BuildConfig

config = BuildConfig(
    output_dir=Path("dist"),
    python_version="3.12",
)

engine = BuildEngine(config)

# Build from local path
result = await engine.build(".")

# Build from git
result = await engine.build("https://github.com/psf/requests@v2.31.0")

# Build with sdist
result = await engine.build(".", sdist=True)
```

---

## BuildConfig

Configuration for the build engine.

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `output_dir` | `Path` | `Path("dist")` | Output directory |
| `python_version` | `str` | `"3.12"` | Python version |
| `build_wheel` | `bool` | `True` | Build wheel |
| `build_sdist` | `bool` | `False` | Build sdist |
| `clean_output` | `bool` | `False` | Clean output before build |
| `config_settings` | `dict[str, str] \| None` | `None` | Backend config settings |
| `isolation` | `IsolationStrategy \| None` | `None` | Custom isolation strategy |
| `use_docker` | `bool` | `False` | Use Docker isolation |
| `docker_platform` | `str` | `"auto"` | Docker platform |
| `docker_image` | `str \| None` | `None` | Custom Docker image |
| `docker_architecture` | `str` | `"x86_64"` | Target architecture |

### Example

```python
from pathlib import Path
from headless_wheel_builder.core import BuildConfig, BuildEngine

# Basic config
config = BuildConfig(
    output_dir=Path("dist"),
    python_version="3.11",
)

# Docker build config
docker_config = BuildConfig(
    output_dir=Path("dist"),
    use_docker=True,
    docker_platform="manylinux",
    docker_architecture="x86_64",
)

# With config settings
config_with_settings = BuildConfig(
    config_settings={
        "--global-option": "--no-user-cfg",
    }
)
```

---

## BuildResult

Result of a wheel build operation.

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `success` | `bool` | Whether build succeeded |
| `wheel_path` | `Path \| None` | Path to built wheel |
| `sdist_path` | `Path \| None` | Path to built sdist |
| `build_log` | `str` | Full build log |
| `duration_seconds` | `float` | Build duration |
| `error` | `str \| None` | Error message if failed |
| `name` | `str \| None` | Package name |
| `version` | `str \| None` | Package version |
| `python_tag` | `str \| None` | Python compatibility tag |
| `abi_tag` | `str \| None` | ABI tag |
| `platform_tag` | `str \| None` | Platform tag |
| `sha256` | `str \| None` | SHA256 hash of wheel |
| `size_bytes` | `int \| None` | Wheel file size |

### Methods

#### failure()

```python
@classmethod
def failure(
    cls,
    error: str,
    build_log: str = "",
    duration: float = 0.0
) -> BuildResult
```

Create a failure result.

### Example

```python
result = await engine.build(".")

if result.success:
    print(f"Package: {result.name}")
    print(f"Version: {result.version}")
    print(f"Wheel: {result.wheel_path}")
    print(f"Size: {result.size_bytes / 1024:.1f} KB")
    print(f"SHA256: {result.sha256}")
    print(f"Tags: {result.python_tag}-{result.abi_tag}-{result.platform_tag}")
else:
    print(f"Build failed: {result.error}")
    print(result.build_log)
```

---

## SourceResolver

Resolves source specifications to local paths.

### Constructor

```python
SourceResolver(cache_dir: Path | None = None)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cache_dir` | `Path \| None` | `~/.cache/hwb/sources` | Cache directory for cloned repos |

### Methods

#### parse_source()

```python
def parse_source(source: str) -> SourceSpec
```

Parse a source string into a SourceSpec.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `source` | `str` | Source string (path, git URL, etc.) |

**Returns:** `SourceSpec`

**Raises:** `SourceError` if source type cannot be determined

#### resolve()

```python
async def resolve(spec: SourceSpec) -> ResolvedSource
```

Resolve a source spec to a local path.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `spec` | `SourceSpec` | Source specification |

**Returns:** `ResolvedSource`

**Raises:** `SourceError` if source cannot be resolved

### Example

```python
from headless_wheel_builder.core import SourceResolver

resolver = SourceResolver()

# Parse different source types
local_spec = resolver.parse_source("/path/to/project")
git_spec = resolver.parse_source("https://github.com/psf/requests@v2.31.0")
archive_spec = resolver.parse_source("https://example.com/package.tar.gz")

# Resolve to local path
resolved = await resolver.resolve(git_spec)
print(f"Cloned to: {resolved.local_path}")
print(f"Commit: {resolved.commit_hash}")

# Cleanup when done
resolved.cleanup()
```

---

## SourceSpec

Specification for a source location.

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `type` | `SourceType` | Type of source |
| `location` | `str` | Location (path or URL) |
| `ref` | `str \| None` | Git ref (branch/tag/commit) |
| `subdirectory` | `str \| None` | Subdirectory for monorepos |
| `editable` | `bool` | Editable install |

---

## SourceType

Enum of supported source types.

| Value | Description |
|-------|-------------|
| `LOCAL_PATH` | Local directory |
| `GIT_HTTPS` | Git repository (HTTPS) |
| `GIT_SSH` | Git repository (SSH) |
| `TARBALL` | Remote archive |
| `SDIST` | Local source distribution |

---

## ResolvedSource

A source that has been resolved to a local path.

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `spec` | `SourceSpec` | Original specification |
| `local_path` | `Path` | Local path to source |
| `is_temporary` | `bool` | Whether path should be cleaned up |
| `commit_hash` | `str \| None` | Git commit hash (for git sources) |

### Methods

#### cleanup()

```python
def cleanup() -> None
```

Clean up temporary resources.

### Context Manager

ResolvedSource can be used as a context manager for automatic cleanup:

```python
resolver = SourceResolver()
spec = resolver.parse_source("https://github.com/psf/requests@v2.31.0")

with await resolver.resolve(spec) as resolved:
    # Use resolved.local_path
    print(resolved.local_path)
# Automatic cleanup
```

---

## Convenience Function

### build_wheel()

```python
async def build_wheel(
    source: str | Path = ".",
    output_dir: str | Path = "dist",
    python: str = "3.12",
    sdist: bool = False,
) -> BuildResult
```

Simple entry point for building wheels.

**Example:**

```python
from headless_wheel_builder.core.builder import build_wheel

result = await build_wheel(
    source="https://github.com/psf/requests@v2.31.0",
    output_dir="dist",
    python="3.12",
)

print(result.wheel_path)
```

---

## ProjectAnalyzer

Analyzes Python projects to extract metadata.

### Methods

#### analyze()

```python
async def analyze(path: Path) -> ProjectMetadata
```

Analyze a Python project.

**Returns:** `ProjectMetadata` with project information.

---

## ProjectMetadata

Metadata extracted from a project.

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str \| None` | Package name |
| `version` | `str \| None` | Package version |
| `requires_python` | `str \| None` | Python version constraint |
| `backend` | `BuildBackend \| None` | Build backend info |
| `dependencies` | `list[str]` | Runtime dependencies |
| `optional_dependencies` | `dict[str, list[str]]` | Optional dependency groups |
| `build_requirements` | `list[str]` | Build system requirements |
| `has_extension_modules` | `bool` | Has compiled extensions |
| `extension_languages` | `list[str]` | Languages used in extensions |
| `has_pyproject` | `bool` | Has pyproject.toml |
| `has_setup_py` | `bool` | Has setup.py |
| `has_setup_cfg` | `bool` | Has setup.cfg |

### Example

```python
from pathlib import Path
from headless_wheel_builder.core import ProjectAnalyzer

analyzer = ProjectAnalyzer()
metadata = await analyzer.analyze(Path("."))

print(f"Name: {metadata.name}")
print(f"Version: {metadata.version}")
print(f"Backend: {metadata.backend.name}")
print(f"Dependencies: {len(metadata.dependencies)}")
print(f"Has extensions: {metadata.has_extension_modules}")
```
