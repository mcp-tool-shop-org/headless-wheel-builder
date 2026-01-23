# CLI Reference

Headless Wheel Builder provides a comprehensive command-line interface through the `hwb` command.

## Installation

After installing the package, the `hwb` command is available:

```bash
hwb --help
```

Or run as a Python module:

```bash
python -m headless_wheel_builder --help
```

## Global Options

These options apply to all commands:

| Option | Description |
|--------|-------------|
| `--version` | Show version and exit |
| `-v, --verbose` | Increase verbosity (can be repeated) |
| `-q, --quiet` | Suppress non-error output |
| `--json` | Output in JSON format |
| `--no-color` | Disable colored output |
| `--help` | Show help message |

## Commands Overview

| Command | Description |
|---------|-------------|
| [`build`](build.md) | Build wheels from source |
| [`inspect`](inspect.md) | Analyze project configuration |
| [`publish`](publish.md) | Publish wheels to PyPI or S3 |
| [`version-next`](version.md) | Calculate next version |
| `images` | List available Docker images |
| `version` | Show version information |

## Quick Examples

```bash
# Build from current directory
hwb build

# Build from git repository
hwb build https://github.com/psf/requests@v2.31.0

# Build manylinux wheel
hwb build --isolation docker

# Inspect project metadata
hwb inspect /path/to/project

# Publish to PyPI
hwb publish dist/*.whl

# Calculate next version
hwb version-next
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 3 | Build or publish failure |
| 10 | Interrupted (Ctrl+C) |

## JSON Output

All commands support `--json` for machine-readable output:

```bash
hwb build --json | jq '.wheel.path'
hwb inspect --format json | jq '.name'
hwb version-next --json | jq '.next'
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `PYPI_TOKEN` | PyPI API token for publishing |
| `TESTPYPI_TOKEN` | TestPyPI API token |
| `AWS_ACCESS_KEY_ID` | AWS credentials for S3 publishing |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials for S3 publishing |
| `DOCKER_HOST` | Docker daemon address |

## Shell Completion

### Bash

```bash
# Add to ~/.bashrc
eval "$(_HWB_COMPLETE=bash_source hwb)"
```

### Zsh

```bash
# Add to ~/.zshrc
eval "$(_HWB_COMPLETE=zsh_source hwb)"
```

### Fish

```bash
# Add to ~/.config/fish/completions/hwb.fish
_HWB_COMPLETE=fish_source hwb | source
```
