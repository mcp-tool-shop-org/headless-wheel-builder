# Headless Wheel Builder

A universal, headless Python wheel builder supporting local paths, git repos, and CI/CD pipelines.

## Features

- **Build from Anywhere**: Build wheels from local paths, git repositories, or archive URLs
- **PEP 517/518/621 Compliant**: Full support for modern Python packaging standards
- **Build Isolation**: Choose between venv or Docker isolation for reproducible builds
- **Docker Support**: Build manylinux and musllinux wheels for cross-platform compatibility
- **Multi-Registry Publishing**: Publish to PyPI, TestPyPI, private registries, or S3-compatible storage
- **Automated Versioning**: SemVer support with Conventional Commits integration
- **Changelog Generation**: Automatically generate changelogs from git history

## Quick Start

```bash
# Install
pip install headless-wheel-builder

# Build a wheel from current directory
hwb build

# Build from a git repository
hwb build https://github.com/user/repo

# Build with Docker isolation (manylinux)
hwb build --isolation docker

# Publish to PyPI
hwb publish dist/*.whl
```

## Installation

```bash
pip install headless-wheel-builder
```

Or with optional dependencies:

```bash
# For publishing support
pip install headless-wheel-builder[publish]

# For development
pip install headless-wheel-builder[dev,test]
```

## Documentation

- [Getting Started](getting-started/installation.md)
- [User Guide](guide/building.md)
- [CLI Reference](cli/index.md)
- [API Reference](api/core.md)

## License

MIT License - see [LICENSE](https://github.com/your-org/headless-wheel-builder/blob/main/LICENSE) for details.
