# Installation

## Requirements

- Python 3.10 or higher
- pip or uv package manager
- Git (for building from repositories)
- Docker (optional, for manylinux/musllinux builds)

## Quick Install

```bash
pip install headless-wheel-builder
```

Or with [uv](https://github.com/astral-sh/uv) (recommended for speed):

```bash
uv pip install headless-wheel-builder
```

## Optional Dependencies

### Publishing Support

For publishing to PyPI or other registries:

```bash
pip install headless-wheel-builder[publish]
```

This includes:
- `twine` - For uploading to PyPI
- `build` - For building packages

### Development

For development and testing:

```bash
pip install headless-wheel-builder[dev,test]
```

This includes:
- `ruff` - Linting and formatting
- `pyright` - Type checking
- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting

### Documentation

For building documentation:

```bash
pip install headless-wheel-builder[docs]
```

### All Dependencies

Install everything:

```bash
pip install headless-wheel-builder[all]
```

## Verify Installation

After installation, verify the CLI is available:

```bash
hwb --help
```

You should see:

```
Usage: hwb [OPTIONS] COMMAND [ARGS]...

  Headless Wheel Builder - Build Python wheels from anywhere.

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  build        Build wheels from source.
  inspect      Analyze project configuration.
  publish      Publish wheels to a registry.
  version-next Calculate and optionally create the next version.
```

## Docker Setup (Optional)

For building manylinux or musllinux wheels, you need Docker installed:

### Linux

```bash
# Ubuntu/Debian
sudo apt-get install docker.io
sudo usermod -aG docker $USER

# Fedora
sudo dnf install docker
sudo systemctl start docker
sudo usermod -aG docker $USER
```

### macOS

Install [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/).

### Windows

Install [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/) with WSL 2 backend.

### Verify Docker

```bash
docker run --rm hello-world
```

## Development Installation

To install from source for development:

```bash
git clone https://github.com/your-org/headless-wheel-builder.git
cd headless-wheel-builder
pip install -e ".[dev,test]"
```

Run tests to verify:

```bash
pytest tests/
```
