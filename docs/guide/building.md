# Building Wheels

This guide covers all aspects of building Python wheels with Headless Wheel Builder.

## Basic Building

### Build from Current Directory

```bash
hwb build
```

This builds a wheel from the current directory and outputs to `dist/`.

### Specify Output Directory

```bash
hwb build --output ./my-wheels
# or short form
hwb build -o ./my-wheels
```

### Build Wheel and Source Distribution

```bash
hwb build --sdist
```

This creates both a `.whl` file and a `.tar.gz` source distribution.

## Python Version

By default, builds use Python 3.12. To specify a different version:

```bash
hwb build --python 3.11
```

!!! note
    The specified Python version must be available on your system or in Docker (for Docker isolation).

## Build Isolation

Build isolation ensures reproducible builds by creating a clean environment.

### Venv Isolation (Default)

Creates a temporary virtual environment for each build:

```bash
hwb build --isolation venv
```

Benefits:
- Fast environment creation
- Uses system Python
- Works everywhere

### Docker Isolation

Builds in a Docker container for manylinux/musllinux compatibility:

```bash
hwb build --isolation docker
```

Benefits:
- Produces portable Linux wheels
- Consistent build environment
- Required for C extensions on Linux

See [Build Isolation](isolation.md) for details.

### No Isolation

Use the current Python environment (fastest but least reproducible):

```bash
hwb build --isolation none
```

!!! warning
    Building without isolation may produce different results depending on installed packages.

## Config Settings

Pass configuration to the build backend:

```bash
# Single setting
hwb build -C key=value

# Multiple settings
hwb build -C wheel.py-api=cp312 -C build.verbose=true
```

Common settings vary by build backend:

### Setuptools

```bash
hwb build -C --global-option=--quiet
```

### Hatchling

```bash
hwb build -C targets.wheel.versions=["py3"]
```

### Maturin (Rust)

```bash
hwb build -C build-args=--release
```

## Building from Different Sources

### Local Directory

```bash
hwb build /path/to/project
hwb build ./my-package
hwb build .
```

### Git Repository

```bash
# Default branch
hwb build https://github.com/user/repo

# Specific tag
hwb build https://github.com/user/repo@v1.0.0

# Specific branch
hwb build https://github.com/user/repo@develop

# Specific commit
hwb build https://github.com/user/repo@abc123def
```

### Monorepo (Subdirectory)

```bash
hwb build https://github.com/org/monorepo#subdirectory=packages/my-lib
```

### Archive URL

```bash
hwb build https://example.com/releases/package-1.0.0.tar.gz
```

See [Source Types](sources.md) for complete details.

## Build Output

### Successful Build

```
Building wheel for /path/to/project
  Python: 3.12
  Output: /path/to/dist

+----------------------------- Build Successful ------------------------------+
|   Package     my-package                                                    |
|   Version     1.0.0                                                         |
|   Wheel       /path/to/dist/my_package-1.0.0-py3-none-any.whl               |
|   Size        42.5 KB                                                       |
|   Tags        py3-none-any                                                  |
|   Duration    5.2s                                                          |
+-----------------------------------------------------------------------------+
```

### Failed Build

```
Building wheel for /path/to/project
  Python: 3.12
  Output: /path/to/dist

+------------------------------- Build Failed --------------------------------+
| Error: Missing required dependency 'some-package'                           |
|                                                                             |
| Build log saved to: /tmp/hwb_build_xyz123.log                               |
+-----------------------------------------------------------------------------+
```

## Wheel Naming

Wheels follow the [PEP 427](https://peps.python.org/pep-0427/) naming convention:

```
{distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
```

Examples:

| Wheel Name | Description |
|------------|-------------|
| `click-8.1.7-py3-none-any.whl` | Pure Python, any platform |
| `numpy-1.26.0-cp312-cp312-manylinux_2_17_x86_64.whl` | CPython 3.12, Linux x86_64 |
| `cryptography-41.0.0-cp312-abi3-musllinux_1_1_x86_64.whl` | CPython 3.12+, Alpine Linux |

## Cleaning Output

To clean the output directory before building:

```bash
hwb build --clean
```

This removes all existing files in the output directory.

## Verbose Output

For detailed build output:

```bash
hwb build -v
# or
hwb build --verbose
```

For even more detail:

```bash
hwb build -vv
```

## JSON Output

For machine-readable output:

```bash
hwb build --json
```

```json
{
  "success": true,
  "package": "my-package",
  "version": "1.0.0",
  "wheel_path": "/path/to/dist/my_package-1.0.0-py3-none-any.whl",
  "size_bytes": 43520,
  "tags": "py3-none-any",
  "duration_seconds": 5.2
}
```

## Examples

### Build Click from GitHub

```bash
hwb build https://github.com/pallets/click@8.1.7 -o dist/
```

### Build Rich with Source Distribution

```bash
hwb build https://github.com/Textualize/rich@v13.9.4 --sdist -o dist/
```

### Build Pydantic in Docker

```bash
hwb build https://github.com/pydantic/pydantic@v2.10.0 --isolation docker
```

### Build Local Package for Multiple Platforms

```bash
# Pure Python
hwb build ./my-package -o dist/

# Linux manylinux
hwb build ./my-package --isolation docker --platform manylinux -o dist/

# Linux musllinux (Alpine)
hwb build ./my-package --isolation docker --platform musllinux -o dist/
```
