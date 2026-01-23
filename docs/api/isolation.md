# Isolation API

The isolation module provides build environment isolation strategies.

## Overview

Build isolation ensures clean, reproducible builds by:

- Creating isolated environments with specific Python versions
- Installing only required build dependencies
- Preventing contamination from system packages

Two strategies are available:

- **VenvIsolation** - Virtual environments (default)
- **DockerIsolation** - Docker containers (for manylinux wheels)

## Quick Start

```python
from headless_wheel_builder.isolation import (
    VenvIsolation,
    VenvConfig,
    BuildEnvironment,
)

# Create venv isolation
isolation = VenvIsolation()

# Create environment with build requirements
env = await isolation.create_environment(
    python_version="3.12",
    build_requirements=["setuptools>=61.0", "wheel"],
)

# Use the environment
async with env:
    print(f"Python: {env.python_path}")
    print(f"Site-packages: {env.site_packages}")
```

---

## IsolationStrategy Protocol

All isolation strategies implement this protocol:

```python
class IsolationStrategy(Protocol):
    async def create_environment(
        self,
        python_version: str,
        build_requirements: list[str],
    ) -> BuildEnvironment: ...

    async def check_available(self) -> bool: ...
```

---

## BuildEnvironment

Represents an isolated build environment.

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `python_path` | `Path` | Path to Python interpreter |
| `site_packages` | `Path` | Path to site-packages directory |
| `env_vars` | `dict[str, str]` | Environment variables to use |

### Methods

#### cleanup()

```python
async def cleanup() -> None
```

Clean up the environment resources.

### Context Manager

BuildEnvironment supports async context manager:

```python
async with await isolation.create_environment(...) as env:
    # Use environment
    pass
# Automatic cleanup
```

---

## VenvIsolation

Virtual environment isolation strategy.

### Constructor

```python
VenvIsolation(config: VenvConfig | None = None)
```

### VenvConfig

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `use_uv` | `bool` | `True` | Use uv for fast installs |
| `python_path` | `Path \| None` | `None` | Specific Python to use |
| `cache_envs` | `bool` | `False` | Cache environments |
| `extra_env` | `dict[str, str] \| None` | `None` | Extra env vars |

### Methods

#### create_environment()

```python
async def create_environment(
    python_version: str,
    build_requirements: list[str],
) -> BuildEnvironment
```

Create an isolated virtual environment.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `python_version` | `str` | Python version (e.g., "3.12") |
| `build_requirements` | `list[str]` | Packages to install |

**Returns:** `BuildEnvironment`

**Raises:**
- `IsolationError` - Environment creation failed
- `DependencyError` - Package installation failed

#### check_available()

```python
async def check_available() -> bool
```

Check if venv isolation is available (always True on supported Python).

### Python Discovery

VenvIsolation searches for Python interpreters in this order:

1. Config-specified path (`VenvConfig.python_path`)
2. uv-managed Python (`uv python find`)
3. pyenv Python (`~/.pyenv/versions/`)
4. System Python (`python3.12`, `python312`, etc.)

### Example

```python
from headless_wheel_builder.isolation import VenvIsolation, VenvConfig

# With uv (fast)
config = VenvConfig(use_uv=True)
isolation = VenvIsolation(config)

# Without uv
config = VenvConfig(use_uv=False)
isolation = VenvIsolation(config)

# With specific Python
config = VenvConfig(
    python_path=Path("/opt/python/3.12/bin/python"),
)
isolation = VenvIsolation(config)

# Create environment
env = await isolation.create_environment(
    python_version="3.12",
    build_requirements=[
        "setuptools>=61.0",
        "wheel",
        "hatchling",
    ],
)

async with env:
    # Run build in environment
    import asyncio
    process = await asyncio.create_subprocess_exec(
        str(env.python_path),
        "-c", "import setuptools; print(setuptools.__version__)",
        env=env.env_vars,
    )
    await process.communicate()
```

---

## DockerIsolation

Docker-based isolation for manylinux/musllinux wheels.

### Constructor

```python
DockerIsolation(config: DockerConfig | None = None)
```

### DockerConfig

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `platform` | `PlatformType` | `"auto"` | Platform type |
| `image` | `str \| None` | `None` | Custom image |
| `architecture` | `str` | `"x86_64"` | Target arch |
| `network` | `bool` | `True` | Enable network |
| `memory_limit` | `str \| None` | `None` | Memory limit |
| `cpu_limit` | `float \| None` | `None` | CPU limit |
| `repair_wheel` | `bool` | `True` | Run auditwheel |
| `strip_binaries` | `bool` | `True` | Strip debug |
| `extra_mounts` | `dict[str, str]` | `{}` | Extra volumes |
| `extra_env` | `dict[str, str]` | `{}` | Extra env vars |

### Platform Types

```python
PlatformType = Literal["manylinux", "musllinux", "auto"]
```

### Methods

#### create_environment()

```python
async def create_environment(
    python_version: str,
    build_requirements: list[str],
) -> BuildEnvironment
```

Prepare Docker build environment configuration.

#### build_in_container()

```python
async def build_in_container(
    source_dir: Path,
    output_dir: Path,
    env: BuildEnvironment,
    build_wheel: bool = True,
    build_sdist: bool = False,
    config_settings: dict[str, str] | None = None,
) -> tuple[Path | None, Path | None, str]
```

Build wheel inside Docker container.

**Returns:** `(wheel_path, sdist_path, build_log)`

#### check_available()

```python
async def check_available() -> bool
```

Check if Docker is available and running.

#### list_available_images()

```python
async def list_available_images() -> dict[str, str]
```

List available manylinux/musllinux images.

#### get_image_info()

```python
async def get_image_info(image: str) -> dict
```

Get information about a Docker image.

### Available Images

| Image | Description |
|-------|-------------|
| `manylinux2014_x86_64` | CentOS 7 (oldest, most compatible) |
| `manylinux_2_28_x86_64` | AlmaLinux 8 (recommended) |
| `manylinux_2_34_x86_64` | AlmaLinux 9 (newest glibc) |
| `musllinux_1_1_x86_64` | Alpine musl 1.1 |
| `musllinux_1_2_x86_64` | Alpine musl 1.2 |

ARM64 variants (`_aarch64`) are also available.

### Example

```python
from pathlib import Path
from headless_wheel_builder.isolation.docker import (
    DockerIsolation,
    DockerConfig,
    get_docker_isolation,
)

# Basic Docker build
config = DockerConfig(
    platform="manylinux",
    architecture="x86_64",
)
isolation = DockerIsolation(config)

# Check availability
if await isolation.check_available():
    env = await isolation.create_environment(
        python_version="3.12",
        build_requirements=["setuptools>=61.0", "wheel"],
    )

    wheel_path, sdist_path, log = await isolation.build_in_container(
        source_dir=Path("/path/to/project"),
        output_dir=Path("/path/to/dist"),
        env=env,
    )

    print(f"Built: {wheel_path}")

# Custom image
config = DockerConfig(
    image="quay.io/pypa/manylinux_2_28_x86_64",
    repair_wheel=True,
)

# With resource limits
config = DockerConfig(
    memory_limit="4g",
    cpu_limit=2.0,
)

# With extra mounts
config = DockerConfig(
    extra_mounts={
        "/host/cache": "/root/.cache",
    },
)
```

### Convenience Function

```python
async def get_docker_isolation(
    platform: PlatformType = "auto",
    architecture: str = "x86_64",
) -> DockerIsolation
```

Get a configured Docker isolation strategy.

```python
isolation = await get_docker_isolation(
    platform="manylinux",
    architecture="x86_64",
)
```

---

## Choosing Isolation Strategy

| Use Case | Strategy |
|----------|----------|
| Pure Python packages | VenvIsolation |
| C extensions (Linux) | DockerIsolation |
| Local development | VenvIsolation |
| CI/CD manylinux | DockerIsolation |
| Alpine deployment | DockerIsolation (musllinux) |
| Windows/macOS | VenvIsolation |

### Example: Auto-Select

```python
from headless_wheel_builder.core import ProjectAnalyzer
from headless_wheel_builder.isolation import VenvIsolation
from headless_wheel_builder.isolation.docker import DockerIsolation

async def get_best_isolation(project_path: Path):
    analyzer = ProjectAnalyzer()
    metadata = await analyzer.analyze(project_path)

    if metadata.has_extension_modules:
        # Use Docker for compiled extensions
        docker = DockerIsolation()
        if await docker.check_available():
            return docker

    # Default to venv
    return VenvIsolation()
```
