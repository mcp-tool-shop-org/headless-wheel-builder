# Quick Start

This guide will get you building Python wheels in minutes.

## Your First Build

### Build from Current Directory

If you're in a Python project directory with a `pyproject.toml`:

```bash
hwb build
```

This creates a wheel in the `dist/` directory.

### Build from a Local Path

```bash
hwb build /path/to/your/project
```

### Build from a Git Repository

```bash
# Latest commit on default branch
hwb build https://github.com/psf/requests

# Specific tag
hwb build https://github.com/psf/requests@v2.31.0

# Specific branch
hwb build https://github.com/user/repo@develop
```

## Inspecting Projects

Before building, you can inspect a project to see its metadata:

```bash
hwb inspect /path/to/project
```

Output:
```
Project: my-package
Version: 1.0.0
Build Backend: setuptools.build_meta

Dependencies:
  - click>=8.0
  - rich>=13.0

Build Requirements:
  - setuptools>=61.0
  - wheel
```

For JSON output:
```bash
hwb inspect /path/to/project --format json
```

## Build Options

### Specify Output Directory

```bash
hwb build --output ./my-dist
```

### Build Source Distribution Too

```bash
hwb build --sdist
```

### Build with Specific Python Version

```bash
hwb build --python 3.11
```

### Build Isolation

By default, builds use virtual environment isolation:

```bash
# Explicit venv isolation
hwb build --isolation venv

# No isolation (use current environment)
hwb build --isolation none

# Docker isolation (for manylinux wheels)
hwb build --isolation docker
```

## Building Manylinux Wheels

For cross-platform compatibility, build manylinux wheels using Docker:

```bash
# Auto-detect best manylinux image
hwb build --isolation docker

# Specific platform
hwb build --isolation docker --platform manylinux

# musllinux for Alpine
hwb build --isolation docker --platform musllinux
```

## Publishing Wheels

### Publish to PyPI

```bash
# Publish all wheels in dist/
hwb publish dist/*.whl

# Dry run (validate without uploading)
hwb publish dist/*.whl --dry-run
```

### Publish to TestPyPI

```bash
hwb publish dist/*.whl --repository testpypi
```

### Publish to Private Registry

```bash
hwb publish dist/*.whl --repository-url https://my-registry.example.com/simple/
```

## Automated Versioning

If your project uses [Conventional Commits](https://www.conventionalcommits.org/):

### Check Next Version

```bash
hwb version-next
```

Output:
```
Current version: 1.2.3
Commits since v1.2.3:
  - feat: add new feature
  - fix: resolve bug

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

## Complete Workflow Example

Here's a typical CI/CD workflow:

```bash
# 1. Clone and build
hwb build https://github.com/user/repo@v1.0.0 --output dist/

# 2. Inspect the result
hwb inspect dist/*.whl

# 3. Test publish to TestPyPI
hwb publish dist/*.whl --repository testpypi --dry-run

# 4. Publish to PyPI
hwb publish dist/*.whl
```

## Python API

You can also use the library programmatically:

```python
import asyncio
from headless_wheel_builder.core.builder import BuildEngine
from headless_wheel_builder.core.source import SourceResolver

async def build_wheel():
    # Resolve source
    resolver = SourceResolver()
    spec = resolver.parse_source("https://github.com/psf/requests@v2.31.0")
    source = await resolver.resolve(spec)

    # Build wheel
    builder = BuildEngine()
    result = await builder.build(source, output_dir="dist/")

    if result.success:
        print(f"Built: {result.wheel_path}")
    else:
        print(f"Failed: {result.error}")

asyncio.run(build_wheel())
```

## Next Steps

- [Building Wheels](../guide/building.md) - Detailed build options
- [Source Types](../guide/sources.md) - All supported source formats
- [Build Isolation](../guide/isolation.md) - Venv vs Docker isolation
- [Publishing](../guide/publishing.md) - Registry configuration
- [CLI Reference](../cli/index.md) - Complete command reference
