# Headless Wheel Builder

[![PyPI version](https://badge.fury.io/py/headless-wheel-builder.svg)](https://badge.fury.io/py/headless-wheel-builder)
[![Python versions](https://img.shields.io/pypi/pyversions/headless-wheel-builder.svg)](https://pypi.org/project/headless-wheel-builder/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A universal, headless Python wheel builder supporting local paths, git repos, and CI/CD pipelines with flexible isolation (venv/Docker), multi-registry publishing, and automated versioning.

## Features

- **Build from anywhere**: Local paths, git URLs (with branch/tag), tarballs
- **Build isolation**: venv (uv-powered, 10-100x faster) or Docker (manylinux/musllinux)
- **Multi-platform**: Build matrix for Python 3.9-3.14, Linux/macOS/Windows
- **Publishing**: PyPI Trusted Publishers (OIDC), DevPi, Artifactory, S3
- **Versioning**: Auto-bump from Conventional Commits, changelog generation
- **Windows-first**: Full Windows support including RTX 5080 compatibility

## Installation

```bash
# With pip
pip install headless-wheel-builder

# With uv (recommended - faster)
uv pip install headless-wheel-builder
```

## Quick Start

```bash
# Build wheel from current directory
hwb build

# Build from git repository
hwb build https://github.com/user/repo

# Build specific version
hwb build https://github.com/user/repo@v2.0.0

# Build with specific Python version
hwb build --python 3.11

# Build wheel and sdist
hwb build --sdist
```

## Usage

### CLI

```bash
# Basic build
hwb build [SOURCE]

# Build with options
hwb build --python 3.12 --output dist --sdist

# Inspect project
hwb inspect .

# JSON output (for scripting)
hwb build --json
```

### Python API

```python
import asyncio
from headless_wheel_builder import build_wheel

async def main():
    result = await build_wheel(
        source=".",
        output_dir="dist",
        python="3.12"
    )

    if result.success:
        print(f"Built: {result.wheel_path}")
        print(f"SHA256: {result.sha256}")

asyncio.run(main())
```

## Build Isolation

### Virtual Environment (Default)

Uses uv for 10-100x faster dependency installation:

```bash
hwb build --isolation venv
```

### Docker (for manylinux)

Build portable Linux wheels:

```bash
hwb build --isolation docker --manylinux 2_28
```

## Configuration

Configure in `pyproject.toml`:

```toml
[tool.hwb]
output-dir = "dist"
python = "3.12"

[tool.hwb.build]
sdist = true
checksum = true
```

## Documentation

See the [docs/](docs/) directory for comprehensive documentation:

- [ROADMAP.md](docs/ROADMAP.md) - Development phases and milestones
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design and components
- [API.md](docs/API.md) - CLI and Python API reference
- [SECURITY.md](docs/SECURITY.md) - Security model and best practices
- [PUBLISHING.md](docs/PUBLISHING.md) - Registry publishing workflows
- [ISOLATION.md](docs/ISOLATION.md) - Build isolation strategies
- [VERSIONING.md](docs/VERSIONING.md) - Semantic versioning and changelog
- [CONTRIBUTING.md](docs/CONTRIBUTING.md) - Development guidelines

## Requirements

- Python 3.10+
- Git (for git source support)
- Docker (optional, for manylinux builds)
- uv (optional, for faster builds)

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.
