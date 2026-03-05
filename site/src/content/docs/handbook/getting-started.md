---
title: Getting Started
description: Install Headless Wheel Builder and build your first Python wheel in minutes.
sidebar:
  order: 1
---

## Installation

Install with pip or uv (recommended for speed):

```bash
pip install headless-wheel-builder

# or with uv
uv pip install headless-wheel-builder

# include all extras (notifications, security scanning, metrics)
pip install headless-wheel-builder[all]
```

## Build your first wheel

### From the current directory

```bash
hwb build .
```

### From a git URL

Pin to a tag, branch, or commit:

```bash
hwb build https://github.com/user/repo@v2.0.0
hwb build https://github.com/user/repo@main
```

### From a tarball

```bash
hwb build ./my-package-1.0.0.tar.gz
```

## Multi-platform builds

Target multiple Python versions in a single invocation:

```bash
hwb build . --python 3.11 --python 3.12
```

Each version gets its own isolated environment. The resulting wheels land in `dist/` by default.

## Build isolation

### Virtual environment (default)

Uses uv under the hood for fast dependency resolution:

```bash
hwb build . --isolation venv
```

### Docker

Build inside a manylinux or musllinux container for maximum compatibility:

```bash
hwb build . --isolation docker --image manylinux2014_x86_64
```

Docker isolation ensures your wheels work on any Linux distribution without surprises.

## Configuration

Add a `[tool.hwb]` section to your `pyproject.toml`:

```toml
[tool.hwb]
default-python = ["3.11", "3.12"]
isolation = "venv"
output-dir = "dist"
```

Command-line flags always override configuration file values.

## Next steps

- [Release Management](../release-management/) — draft and approve releases
- [CLI Reference](../cli-reference/) — all 14 commands
- [DevOps](../devops/) — pipelines, CI generation, multi-repo operations
