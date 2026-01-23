# Build Isolation

Build isolation creates a clean environment for each build, ensuring reproducibility.

## Why Isolation?

Without isolation, builds can be affected by:

- Packages installed in your environment
- Different versions of build tools
- Environment variables
- Platform-specific differences

Isolation solves these issues by creating a pristine build environment.

## Isolation Strategies

### Virtual Environment (venv)

**Default strategy.** Creates a temporary virtual environment for each build.

```bash
hwb build --isolation venv
```

**How it works:**

1. Creates a fresh venv in a temporary directory
2. Installs build requirements from `pyproject.toml`
3. Runs the build backend
4. Cleans up the venv

**Pros:**
- Fast (~2-5 seconds overhead)
- No external dependencies
- Works on all platforms
- Uses local Python version

**Cons:**
- Can't produce manylinux wheels
- Platform-dependent output

**When to use:**
- Development builds
- Pure Python packages
- Quick testing

### Docker

Builds in a Docker container using official manylinux or musllinux images.

```bash
hwb build --isolation docker
```

**How it works:**

1. Pulls the appropriate Docker image
2. Mounts source code into container
3. Runs build inside container
4. Copies wheel back to host
5. Runs `auditwheel repair` for compatibility

**Pros:**
- Produces portable Linux wheels
- Consistent build environment
- Required for C extensions
- Supports multiple architectures

**Cons:**
- Requires Docker
- Slower (~30-60 seconds overhead)
- Linux output only

**When to use:**
- Release builds
- Packages with C extensions
- CI/CD pipelines
- Cross-platform distribution

### No Isolation

Uses your current Python environment directly.

```bash
hwb build --isolation none
```

**Pros:**
- Fastest option
- No environment setup

**Cons:**
- Results depend on installed packages
- Not reproducible
- May conflict with local packages

**When to use:**
- Debugging build issues
- When you control the environment completely

## Docker Platforms

### Manylinux

For broad Linux compatibility:

```bash
# Auto-select best manylinux image
hwb build --isolation docker --platform manylinux
```

Available manylinux images:

| Platform | Base | GLIBC | Use Case |
|----------|------|-------|----------|
| `manylinux2014` | CentOS 7 | 2.17 | Legacy compatibility |
| `manylinux_2_28` | AlmaLinux 8 | 2.28 | Modern systems |
| `manylinux_2_34` | AlmaLinux 9 | 2.34 | Newest systems |

### Musllinux

For Alpine Linux and musl-based systems:

```bash
hwb build --isolation docker --platform musllinux
```

Available musllinux images:

| Platform | Base | Use Case |
|----------|------|----------|
| `musllinux_1_1` | Alpine 3.12 | Broad musl compatibility |
| `musllinux_1_2` | Alpine 3.17 | Modern musl systems |

### Custom Docker Image

Use a specific Docker image:

```bash
hwb build --isolation docker --docker-image quay.io/pypa/manylinux_2_28_x86_64
```

### Target Architecture

Build for different CPU architectures:

```bash
# x86_64 (default)
hwb build --isolation docker --arch x86_64

# ARM64/aarch64
hwb build --isolation docker --arch aarch64

# 32-bit x86
hwb build --isolation docker --arch i686
```

!!! note
    Cross-architecture builds require Docker with QEMU emulation configured.

## Available Images

List available Docker images:

```bash
hwb images
```

Output:
```
Manylinux Images:
  manylinux2014_x86_64     - quay.io/pypa/manylinux2014_x86_64
  manylinux2014_aarch64    - quay.io/pypa/manylinux2014_aarch64
  manylinux_2_28_x86_64    - quay.io/pypa/manylinux_2_28_x86_64
  manylinux_2_28_aarch64   - quay.io/pypa/manylinux_2_28_aarch64

Musllinux Images:
  musllinux_1_1_x86_64     - quay.io/pypa/musllinux_1_1_x86_64
  musllinux_1_1_aarch64    - quay.io/pypa/musllinux_1_1_aarch64
  musllinux_1_2_x86_64     - quay.io/pypa/musllinux_1_2_x86_64
```

## Auditwheel Repair

When using Docker isolation, `auditwheel repair` is automatically run to:

1. Check wheel compatibility
2. Bundle required shared libraries
3. Update wheel tags for manylinux compliance

This ensures your wheel works on any compatible Linux system.

## Environment Variables

### Venv Isolation

You can pass environment variables to the build:

```python
from headless_wheel_builder.isolation.venv import VenvIsolation, VenvConfig

config = VenvConfig(
    extra_env={
        "MY_VAR": "value",
        "DEBUG": "1",
    }
)
isolation = VenvIsolation(config)
```

### Docker Isolation

```python
from headless_wheel_builder.isolation.docker import DockerIsolation, DockerConfig

config = DockerConfig(
    environment={
        "MY_VAR": "value",
    }
)
isolation = DockerIsolation(config)
```

## Performance Comparison

| Strategy | Setup Time | Build Time | Total |
|----------|------------|------------|-------|
| none | 0s | ~5s | ~5s |
| venv | ~3s | ~5s | ~8s |
| docker | ~20s | ~10s | ~30s |

*Times are approximate for a typical pure Python package.*

## Programmatic Usage

```python
from headless_wheel_builder.isolation.venv import VenvIsolation
from headless_wheel_builder.isolation.docker import DockerIsolation

# Venv isolation
venv = VenvIsolation()
env = await venv.create_environment(
    python_version="3.12",
    build_requirements=["setuptools>=61.0", "wheel"],
)

async with env:
    # Use env.python_path for build commands
    print(env.python_path)
    print(env.site_packages)

# Docker isolation
docker = DockerIsolation()
if await docker.check_available():
    result = await docker.build_wheel(
        source_path="/path/to/project",
        output_dir="/path/to/dist",
        platform="manylinux",
    )
```

## Troubleshooting

### Docker not found

```
Error: Docker is not available
```

**Solution:** Install Docker and ensure it's running.

### Permission denied

```
Error: Permission denied connecting to Docker socket
```

**Solution:** Add your user to the docker group:
```bash
sudo usermod -aG docker $USER
# Log out and back in
```

### Image pull failed

```
Error: Failed to pull image
```

**Solution:** Check internet connection and Docker Hub access.

### venv creation failed

```
Error: Failed to create venv
```

**Solution:** Ensure Python's venv module is installed:
```bash
# Debian/Ubuntu
sudo apt-get install python3-venv
```
