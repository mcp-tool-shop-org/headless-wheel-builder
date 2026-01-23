# Build Command

Build Python wheels from various sources.

## Synopsis

```bash
hwb build [OPTIONS] [SOURCE]
```

## Description

The `build` command creates wheel distributions from Python packages. It supports local paths, git repositories, and archive URLs as sources.

## Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `SOURCE` | `.` | Source to build from (path, git URL, or archive URL) |

## Options

### Output Options

| Option | Default | Description |
|--------|---------|-------------|
| `-o, --output DIR` | `dist` | Output directory for built wheels |
| `--wheel/--no-wheel` | `--wheel` | Build wheel distribution |
| `--sdist/--no-sdist` | `--no-sdist` | Build source distribution |
| `--clean` | Off | Clean output directory before building |

### Python Options

| Option | Default | Description |
|--------|---------|-------------|
| `--python VERSION` | `3.12` | Python version to use |

### Isolation Options

| Option | Default | Description |
|--------|---------|-------------|
| `--isolation TYPE` | `auto` | Build isolation strategy |

Isolation types:

- `auto` - Automatically select (venv for pure Python, docker for extensions)
- `venv` - Use virtual environment isolation
- `docker` - Use Docker container isolation
- `none` - No isolation (use current environment)

### Docker Options

Only applicable when `--isolation docker`:

| Option | Default | Description |
|--------|---------|-------------|
| `--platform TYPE` | `auto` | Docker platform (manylinux, musllinux) |
| `--docker-image IMAGE` | Auto | Specific Docker image to use |
| `--arch ARCH` | `x86_64` | Target architecture |

Supported architectures:

- `x86_64` - Intel/AMD 64-bit (most common)
- `aarch64` - ARM 64-bit (Apple Silicon, AWS Graviton)
- `i686` - Intel/AMD 32-bit

### Build Backend Options

| Option | Description |
|--------|-------------|
| `-C, --config-setting KEY=VALUE` | Pass config setting to build backend |

## Examples

### Basic Build

```bash
# Build from current directory
hwb build

# Build from specific path
hwb build /path/to/project

# Build with source distribution
hwb build --sdist
```

### Git Sources

```bash
# Latest commit on default branch
hwb build https://github.com/psf/requests

# Specific tag
hwb build https://github.com/psf/requests@v2.31.0

# Specific branch
hwb build https://github.com/user/repo@develop

# Specific commit
hwb build https://github.com/user/repo@abc123def
```

### Docker Isolation

```bash
# Auto-detect best manylinux image
hwb build --isolation docker

# Specific platform
hwb build --isolation docker --platform manylinux

# musllinux for Alpine
hwb build --isolation docker --platform musllinux

# Custom Docker image
hwb build --isolation docker --docker-image quay.io/pypa/manylinux_2_28_x86_64

# ARM64 build
hwb build --isolation docker --arch aarch64
```

### Python Versions

```bash
# Build for Python 3.11
hwb build --python 3.11

# Build for Python 3.10
hwb build --python 3.10
```

### Config Settings

```bash
# Pass settings to build backend
hwb build -C--global-option=--no-user-cfg
hwb build -C cmake.define.CMAKE_BUILD_TYPE=Release
```

### Output Control

```bash
# Custom output directory
hwb build --output ./packages

# Clean before building
hwb build --clean --output ./dist

# JSON output
hwb build --json
```

## Output

### Text Output (default)

```
Building wheel for .
  Python: 3.12
  Output: dist

╭─────────────── Build Successful ───────────────╮
│   Package   my-package                         │
│   Version   1.0.0                              │
│   Wheel     dist/my_package-1.0.0-py3-none-any.whl │
│   Size      15.2 KB                            │
│   Tags      py3-none-any                       │
│   Duration  2.3s                               │
╰────────────────────────────────────────────────╯
```

### JSON Output

```json
{
  "success": true,
  "wheel": {
    "path": "dist/my_package-1.0.0-py3-none-any.whl",
    "name": "my_package",
    "version": "1.0.0",
    "python_tag": "py3",
    "abi_tag": "none",
    "platform_tag": "any",
    "sha256": "abc123...",
    "size_bytes": 15565
  },
  "sdist": null,
  "duration_seconds": 2.3,
  "error": null
}
```

With `--verbose`, the JSON includes `build_log`.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Build successful |
| 3 | Build failed |
| 10 | Interrupted |

## See Also

- [Building Wheels](../guide/building.md) - Detailed building guide
- [Source Types](../guide/sources.md) - All supported source formats
- [Build Isolation](../guide/isolation.md) - Isolation strategies
