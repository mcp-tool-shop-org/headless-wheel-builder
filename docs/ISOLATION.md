# Headless Wheel Builder - Build Isolation Documentation

> **Purpose**: Detailed guide for build isolation strategies using virtual environments and Docker containers.
> **Last Updated**: 2026-01-23

---

## 2026 Best Practices Applied

> **Sources**: [PEP 517 Build Isolation](https://peps.python.org/pep-0517/), [uv Documentation](https://docs.astral.sh/uv/), [manylinux Project](https://github.com/pypa/manylinux), [cibuildwheel](https://cibuildwheel.pypa.io/), [auditwheel](https://github.com/pypa/auditwheel), [delocate](https://github.com/matthew-brett/delocate)

This isolation guide follows 2026 Python packaging best practices:

1. **Isolation by Default**: Every build runs in an isolated environment with only declared dependencies.

2. **uv for Speed**: Use uv (10-100x faster) for dependency installation when available.

3. **manylinux for Portability**: Use official PyPA manylinux images for portable Linux wheels.

4. **musllinux for Alpine**: Separate musllinux wheels for musl-based systems.

5. **auditwheel/delocate**: Automatically bundle shared libraries for maximum portability.

6. **Python Version Management**: Seamless switching between Python versions via uv or pyenv.

7. **GPU Support**: Docker isolation supports NVIDIA GPU passthrough for CUDA builds.

8. **Windows Native**: First-class Windows support without Docker requirement.

---

## Isolation Strategies Overview

| Strategy | Speed | Portability | Use Case |
|----------|-------|-------------|----------|
| `venv` | Fast | Host only | Pure Python, development |
| `docker` | Slower | High | manylinux, CI/CD |
| `none` | Fastest | None | Testing, debugging |
| `auto` | Varies | Optimal | Default (chooses best) |

### Auto Selection Logic

```python
def select_isolation(project: ProjectMetadata) -> IsolationType:
    """Automatically select best isolation strategy."""

    # Pure Python packages: venv is sufficient
    if not project.has_extension_modules:
        return IsolationType.VENV

    # C/C++ extensions on Linux: use Docker for manylinux
    if sys.platform == "linux" and project.has_extension_modules:
        return IsolationType.DOCKER

    # Rust extensions: Docker recommended for manylinux
    if "rust" in project.extension_languages:
        return IsolationType.DOCKER

    # macOS/Windows: venv (Docker less common)
    return IsolationType.VENV
```

---

## Virtual Environment Isolation

### Overview

Virtual environment isolation creates an ephemeral venv for each build with only the declared build dependencies.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         HOST SYSTEM                                  │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    EPHEMERAL VENV                            │   │
│  │                                                              │   │
│  │  Python 3.12                                                 │   │
│  │  ├── hatchling>=1.26                                         │   │
│  │  ├── wheel                                                   │   │
│  │  └── [project build dependencies]                            │   │
│  │                                                              │   │
│  │  Isolated from:                                              │   │
│  │  • User site-packages                                        │   │
│  │  • System site-packages                                      │   │
│  │  • Other projects                                            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  Source: /path/to/project (read)                                    │
│  Output: /path/to/project/dist (write)                              │
└─────────────────────────────────────────────────────────────────────┘
```

### Basic Usage

```bash
# Build with venv isolation (default for pure Python)
hwb build --isolation venv

# Specify Python version
hwb build --isolation venv --python 3.11

# Build with uv (faster dependency installation)
hwb build --isolation venv  # Uses uv automatically if available
```

### Python Version Management

HWB supports multiple methods for Python version selection:

**1. uv Python Management (Recommended)**

```bash
# uv can install and manage Python versions
uv python install 3.12 3.13

# HWB uses uv's Python automatically
hwb build --python 3.12
```

**2. pyenv**

```bash
# Install Python version with pyenv
pyenv install 3.12.0

# HWB finds pyenv Pythons
hwb build --python 3.12
```

**3. System Python**

```bash
# Uses system Python if version matches
hwb build --python 3.12  # Finds /usr/bin/python3.12
```

**Search Order**:
1. uv-managed Python
2. pyenv Python
3. System Python (python3.X, python3, python)

### Configuration

```toml
# pyproject.toml
[tool.hwb.isolation.venv]
# Prefer uv for faster installs (default: true)
use-uv = true

# Cache venvs for repeated builds (default: false)
cache-envs = false

# Custom Python path (optional)
python-path = "/opt/python/3.12/bin/python"
```

### How It Works

```python
async def build_with_venv(source_path: Path, python: str) -> BuildResult:
    """Build wheel in isolated venv."""

    # 1. Create temporary venv
    venv_dir = Path(tempfile.mkdtemp(prefix="hwb_"))

    try:
        # Find Python interpreter
        python_path = await find_python(python)

        # 2. Create venv (uv is faster if available)
        if await uv_available():
            await run(["uv", "venv", str(venv_dir), "--python", str(python_path)])
        else:
            venv.create(venv_dir, with_pip=True)

        # 3. Install build dependencies
        build_deps = extract_build_deps(source_path / "pyproject.toml")

        if await uv_available():
            await run(["uv", "pip", "install", "--python", venv_python, *build_deps])
        else:
            await run([venv_python, "-m", "pip", "install", *build_deps])

        # 4. Run PEP 517 build
        wheel_path = await run_build_backend(source_path, venv_python)

        return BuildResult(success=True, wheel_path=wheel_path)

    finally:
        # 5. Cleanup
        shutil.rmtree(venv_dir, ignore_errors=True)
```

### Performance Tips

**Use uv**:
```bash
# Install uv
pip install uv

# HWB automatically uses uv when available
hwb build  # 10-100x faster dependency resolution
```

**Cache Build Dependencies**:
```toml
[tool.hwb.isolation.venv]
# Reuse venvs with same dependencies
cache-envs = true
```

**Pin Build Dependencies**:
```toml
# pyproject.toml
[build-system]
# Pinned versions = faster resolution
requires = ["hatchling==1.26.0", "wheel==0.42.0"]
```

---

## Docker Isolation

### Overview

Docker isolation builds wheels inside containers using official PyPA manylinux/musllinux images for maximum portability.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         HOST SYSTEM                                  │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │               DOCKER CONTAINER                               │   │
│  │               (manylinux_2_28_x86_64)                        │   │
│  │                                                              │   │
│  │  /opt/python/cp312-cp312/                                    │   │
│  │  ├── bin/python                                              │   │
│  │  └── lib/python3.12/site-packages/                           │   │
│  │      └── [build dependencies]                                │   │
│  │                                                              │   │
│  │  /src (read-only mount)                                      │   │
│  │  └── [project source]                                        │   │
│  │                                                              │   │
│  │  /output (writable mount)                                    │   │
│  │  └── [built wheels]                                          │   │
│  │                                                              │   │
│  │  Network: disabled                                           │   │
│  │  Capabilities: none                                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### manylinux Wheels

manylinux wheels are portable across Linux distributions by:
1. Building against old glibc (maximum compatibility)
2. Bundling shared library dependencies
3. Using relative RPATHs

**Available manylinux Versions**:

| Version | glibc | Status | Use Case |
|---------|-------|--------|----------|
| `manylinux2014` | 2.17 | Supported | Maximum compatibility |
| `manylinux_2_28` | 2.28 | **Default** | Modern systems |
| `manylinux_2_34` | 2.34 | Supported | Recent systems |
| `manylinux_2_35` | 2.35 | New | C++20 features |

**Basic Usage**:
```bash
# Build manylinux wheel (default: 2_28)
hwb build --isolation docker

# Specify manylinux version
hwb build --isolation docker --manylinux 2014

# Build for older systems
hwb build --isolation docker --manylinux 2014
```

### musllinux Wheels

For Alpine Linux and other musl-based systems.

```bash
# Build musllinux wheel
hwb build --isolation docker --musllinux 1_2
```

**When to Use**:
- Docker images based on Alpine
- IoT/embedded systems using musl
- Minimal container images

### Multi-Architecture Builds

Build for different CPU architectures.

```bash
# Build for ARM64 (on x86_64 host with QEMU)
hwb build --isolation docker --platform linux/arm64

# Build matrix for multiple architectures
hwb matrix --arch x86_64,aarch64
```

**Available Architectures**:
- `x86_64` (amd64) - Default
- `aarch64` (arm64) - ARM servers, Apple Silicon
- `armv7l` - Raspberry Pi
- `ppc64le` - IBM POWER
- `s390x` - IBM Z

### Configuration

```toml
# pyproject.toml
[tool.hwb.isolation.docker]
# Default manylinux version
manylinux = "2_28"

# Custom image (overrides manylinux)
# image = "my-registry.com/custom-build-image:latest"

# Resource limits
memory = "8g"
cpus = 4.0

# GPU support (for CUDA wheels)
gpu = false

# Network access (default: disabled for security)
network = false
```

### GPU Support (CUDA)

Build CUDA-enabled wheels with GPU access.

```bash
# Enable GPU in container
hwb build --isolation docker --gpu
```

**Configuration**:
```toml
[tool.hwb.isolation.docker]
gpu = true
gpu-runtime = "nvidia"  # Default

# Or specify GPU devices
gpu-devices = ["0", "1"]  # Use GPUs 0 and 1
```

**Requirements**:
- NVIDIA Container Toolkit installed
- `nvidia-docker2` or Docker with `--gpus` support
- Matching CUDA version in image

### Custom Dockerfiles

For complex build requirements.

**Project Structure**:
```
mypackage/
├── pyproject.toml
├── Dockerfile.build        # Custom build image
├── src/
│   └── mypackage/
└── ...
```

**Custom Dockerfile**:
```dockerfile
# Dockerfile.build
FROM quay.io/pypa/manylinux_2_28_x86_64

# Install additional system dependencies
RUN yum install -y libffi-devel

# Install custom compiler
RUN yum install -y devtoolset-11
ENV PATH="/opt/rh/devtoolset-11/root/usr/bin:$PATH"

# Pre-install large build dependencies
RUN /opt/python/cp312-cp312/bin/pip install numpy==2.0.0
```

**Usage**:
```bash
hwb build --isolation docker --dockerfile Dockerfile.build
```

### How auditwheel Works

auditwheel repairs wheels by bundling external shared libraries.

```
Before auditwheel:
  mypackage-1.0.0-cp312-cp312-linux_x86_64.whl
  └── mypackage/
      └── _extension.cpython-312-x86_64-linux-gnu.so
          └── NEEDED: libfoo.so.1  (external dependency!)

After auditwheel repair:
  mypackage-1.0.0-cp312-cp312-manylinux_2_28_x86_64.whl
  └── mypackage/
      ├── _extension.cpython-312-x86_64-linux-gnu.so
      │   └── NEEDED: libfoo.so.1 → $ORIGIN/.libs/libfoo.so.1
      └── .libs/
          └── libfoo-abc123.so.1  (bundled!)
```

**Automatic in HWB**:
```bash
# auditwheel runs automatically in Docker builds
hwb build --isolation docker
# Output: mypackage-1.0.0-cp312-cp312-manylinux_2_28_x86_64.whl
```

**Manual Policy**:
```toml
[tool.hwb.isolation.docker]
# auditwheel policy (default: auto-detect)
auditwheel-policy = "manylinux_2_28"

# Exclude libraries from bundling
auditwheel-exclude = ["libcuda.so"]  # CUDA driver is host-provided
```

---

## No Isolation Mode

Build using the host environment (not recommended for production).

```bash
# Use host Python and packages
hwb build --isolation none

# Or
hwb build --no-isolation
```

**Use Cases**:
- Debugging build issues
- Development iteration
- When isolation causes problems
- Performance testing

**Risks**:
- Non-reproducible builds
- May depend on host packages
- May contaminate host environment

---

## macOS Builds

### Universal2 Wheels

Build for both Intel and Apple Silicon.

```bash
# Build universal2 wheel (both architectures)
hwb build --platform macosx-11.0-universal2
```

**Configuration**:
```toml
[tool.hwb.matrix.macos]
# Deployment target (minimum macOS version)
deployment-target = "11.0"

# Architectures
architectures = ["x86_64", "arm64"]

# Build universal2 wheel
universal2 = true
```

### delocate for macOS

delocate bundles shared libraries for macOS (like auditwheel for Linux).

```bash
# Runs automatically for macOS builds
hwb build --platform macos

# Manual delocate
delocate-wheel -w wheelhouse -v dist/*.whl
```

---

## Windows Builds

### Native Windows Builds

Windows builds use venv isolation (Docker not typically used).

```bash
# Build on Windows
hwb build --isolation venv

# Specify Visual Studio version
hwb build --config-setting=--build-option=--compiler=msvc
```

### Visual Studio Detection

HWB automatically finds Visual Studio:

```python
def find_msvc() -> Path:
    """Find Visual Studio installation."""
    vswhere = Path(
        "C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe"
    )

    if vswhere.exists():
        result = subprocess.run([
            str(vswhere),
            "-latest",
            "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
            "-property", "installationPath"
        ], capture_output=True, text=True)

        return Path(result.stdout.strip())

    raise RuntimeError("Visual Studio not found")
```

### Windows-Specific Configuration

```toml
# pyproject.toml
[tool.hwb.isolation.venv]
# Windows-specific settings
[tool.hwb.isolation.venv.windows]
# Disable xformers for SM 12.0 (RTX 5080)
env = { "XFORMERS_DISABLED" = "1" }

# Use specific Python
python-path = "C:/Python312/python.exe"
```

---

## Build Matrix

Build for multiple Python versions and platforms.

```bash
# Build full matrix
hwb matrix

# Custom matrix
hwb matrix --python 3.11,3.12 --platform linux,windows

# Parallel builds
hwb matrix --parallel 8
```

**Configuration**:
```toml
# pyproject.toml
[tool.hwb.matrix]
python = ["3.10", "3.11", "3.12", "3.13"]

[tool.hwb.matrix.linux]
architectures = ["x86_64", "aarch64"]
manylinux = "2_28"

[tool.hwb.matrix.macos]
architectures = ["x86_64", "arm64"]
universal2 = true
deployment-target = "11.0"

[tool.hwb.matrix.windows]
architectures = ["x86_64"]

# Exclude specific combinations
[[tool.hwb.matrix.exclude]]
python = "3.10"
platform = "windows"
arch = "arm64"
```

---

## Troubleshooting

### Docker Issues

**"Cannot connect to Docker daemon"**
```bash
# Start Docker
sudo systemctl start docker

# Or on macOS
open -a Docker
```

**"Image not found"**
```bash
# Pull manylinux image manually
docker pull quay.io/pypa/manylinux_2_28_x86_64
```

**"No space left on device"**
```bash
# Clean Docker
docker system prune -a
```

### venv Issues

**"Python version not found"**
```bash
# Install with uv
uv python install 3.12

# Or with pyenv
pyenv install 3.12
```

**"uv not found"**
```bash
# Install uv
pip install uv

# Or via installer
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Build Dependency Issues

**"Could not find a version that satisfies"**
```bash
# Check build dependencies are available
pip index versions hatchling

# Use verbose mode
hwb build -vvv
```

**"gcc not found" (Linux)**
```bash
# Install build tools
sudo apt install build-essential  # Debian/Ubuntu
sudo yum groupinstall "Development Tools"  # RHEL/CentOS
```

---

## Changelog

| Date | Changes |
|------|---------|
| 2026-01-23 | Initial isolation documentation |
