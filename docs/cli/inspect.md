# Inspect Command

Analyze Python project configuration and metadata.

## Synopsis

```bash
hwb inspect [OPTIONS] [SOURCE]
```

## Description

The `inspect` command analyzes a Python project and displays its metadata, build system configuration, dependencies, and potential issues. Useful for understanding a project before building.

## Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `SOURCE` | `.` | Source to inspect (path or git URL) |

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--format TYPE` | `text` | Output format (`text` or `json`) |
| `--check` | Off | Exit with error if issues found |

## Examples

### Basic Inspection

```bash
# Inspect current directory
hwb inspect

# Inspect specific path
hwb inspect /path/to/project

# Inspect git repository
hwb inspect https://github.com/psf/requests
```

### Output Formats

```bash
# Human-readable (default)
hwb inspect

# JSON output
hwb inspect --format json

# Pipe to jq for specific fields
hwb inspect --format json | jq '.dependencies'
```

### Validation

```bash
# Exit with error if issues found
hwb inspect --check

# Use in CI/CD
hwb inspect --check && hwb build
```

## Output

### Text Output (default)

```
Project: my-package
Version: 1.0.0
Path: /path/to/project

Build System
  Backend: setuptools (setuptools.build_meta)
  Requirements: setuptools>=61.0, wheel

Requires Python: >=3.8

Dependencies (5)
  - click>=8.0
  - rich>=13.0
  - httpx>=0.24
  - pydantic>=2.0
  - tomli>=2.0 ; python_version < "3.11"

Optional Dependencies
  dev: 10 packages
  docs: 5 packages
  test: 3 packages

Pure Python package (no extensions)

Configuration Files
  Y pyproject.toml
  - setup.py
  - setup.cfg
```

### JSON Output

```json
{
  "name": "my-package",
  "version": "1.0.0",
  "path": "/path/to/project",
  "requires_python": ">=3.8",
  "backend": {
    "name": "setuptools",
    "module": "setuptools.build_meta",
    "requirements": ["setuptools>=61.0", "wheel"]
  },
  "dependencies": [
    "click>=8.0",
    "rich>=13.0",
    "httpx>=0.24",
    "pydantic>=2.0",
    "tomli>=2.0 ; python_version < \"3.11\""
  ],
  "optional_dependencies": {
    "dev": ["pytest>=7.0", "mypy>=1.0", "..."],
    "docs": ["mkdocs>=1.5", "..."],
    "test": ["pytest>=7.0", "coverage>=7.0", "..."]
  },
  "has_extensions": false,
  "extension_languages": [],
  "files": {
    "pyproject.toml": true,
    "setup.py": false,
    "setup.cfg": false
  }
}
```

## Information Displayed

### Project Metadata

- **Name** - Package name
- **Version** - Package version (or "dynamic" if determined at build time)
- **Path** - Resolved source path
- **Requires Python** - Python version constraints

### Build System

- **Backend** - Build backend name and module
- **Requirements** - Build system requirements

### Dependencies

- **Runtime Dependencies** - Packages required at runtime
- **Optional Dependencies** - Extra dependency groups (e.g., `dev`, `test`, `docs`)

### Extension Modules

- Whether the package contains compiled extensions
- Languages used (C, C++, Cython, Rust, etc.)

### Configuration Files

- `pyproject.toml` - Modern Python packaging
- `setup.py` - Legacy setup script
- `setup.cfg` - Legacy configuration

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (or success with issues in non-check mode) |
| 1 | Error or issues found (with `--check`) |

## See Also

- [Build Command](build.md) - Build wheels
- [Source Types](../guide/sources.md) - Supported source formats
