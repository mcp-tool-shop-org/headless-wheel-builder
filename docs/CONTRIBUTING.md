# Headless Wheel Builder - Contributing Guide

> **Purpose**: Development standards, testing guidelines, and contribution workflow for HWB contributors.
> **Last Updated**: 2026-01-23

---

## 2026 Best Practices Applied

> **Sources**: [Python Packaging User Guide](https://packaging.python.org/), [uv Documentation](https://docs.astral.sh/uv/), [Conventional Commits](https://www.conventionalcommits.org/), [Pytest Best Practices](https://docs.pytest.org/), [Ruff Linter](https://docs.astral.sh/ruff/)

This contributing guide follows 2026 Python development best practices:

1. **uv for Development**: Use uv for fast, reproducible development environments.

2. **Ruff for Linting**: Fast, comprehensive Python linter replacing flake8, isort, and more.

3. **Pyright for Types**: Strict type checking for better code quality.

4. **Pytest for Testing**: Standard testing framework with async support.

5. **Conventional Commits**: Standardized commit messages for automated releases.

6. **Pre-commit Hooks**: Automated quality checks before commits.

7. **Windows-First Mindset**: Test on Windows early and often (target platform).

8. **Documentation as Code**: Docs live with code and are part of CI.

---

## Quick Start

### Prerequisites

- Python 3.10+ (3.12 recommended)
- Git
- Docker (optional, for manylinux testing)
- uv (recommended) or pip

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/your-org/headless-wheel-builder.git
cd headless-wheel-builder

# Create virtual environment with uv (recommended)
uv venv
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows

# Install in development mode
uv pip install -e ".[dev,test,docs]"

# Install pre-commit hooks
pre-commit install

# Verify setup
pytest --version
ruff --version
pyright --version
```

### Alternative: pip Setup

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

pip install -e ".[dev,test,docs]"
pre-commit install
```

---

## Project Structure

```
headless-wheel-builder/
├── src/
│   └── headless_wheel_builder/
│       ├── __init__.py
│       ├── cli/                    # CLI commands
│       │   ├── __init__.py
│       │   ├── main.py             # CLI entry point
│       │   ├── build.py            # hwb build
│       │   ├── publish.py          # hwb publish
│       │   └── version.py          # hwb version
│       ├── core/                   # Core functionality
│       │   ├── __init__.py
│       │   ├── source.py           # Source resolution
│       │   ├── analyzer.py         # Project analysis
│       │   ├── builder.py          # Build engine
│       │   └── output.py           # Artifact management
│       ├── isolation/              # Build isolation
│       │   ├── __init__.py
│       │   ├── venv.py             # Virtual environment
│       │   ├── docker.py           # Docker containers
│       │   └── strategy.py         # Strategy selection
│       ├── publish/                # Publishing
│       │   ├── __init__.py
│       │   ├── pypi.py             # PyPI publishing
│       │   ├── registry.py         # Private registries
│       │   └── s3.py               # S3 storage
│       └── version/                # Versioning
│           ├── __init__.py
│           ├── manager.py          # Version management
│           ├── commits.py          # Conventional commits
│           └── changelog.py        # Changelog generation
├── tests/
│   ├── conftest.py                 # Pytest fixtures
│   ├── unit/                       # Unit tests
│   ├── integration/                # Integration tests
│   └── e2e/                        # End-to-end tests
├── docs/                           # Documentation
├── pyproject.toml                  # Project configuration
├── README.md
└── CHANGELOG.md
```

---

## Development Workflow

### 1. Create Feature Branch

```bash
# Sync with main
git checkout main
git pull origin main

# Create feature branch
git checkout -b feat/add-feature-x
```

### 2. Make Changes

Follow the coding standards below while implementing your changes.

### 3. Run Tests Locally

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_builder.py

# Run with coverage
pytest --cov=headless_wheel_builder --cov-report=html

# Run only fast tests
pytest -m "not slow"
```

### 4. Run Linters

```bash
# Run all checks
ruff check .
ruff format --check .
pyright

# Auto-fix issues
ruff check --fix .
ruff format .
```

### 5. Commit Changes

Use Conventional Commits format:

```bash
# Feature
git commit -m "feat: add Docker GPU support"

# Bug fix
git commit -m "fix: resolve Windows path handling"

# With scope
git commit -m "feat(cli): add --verbose flag to build command"

# Breaking change
git commit -m "feat!: change default isolation to venv"
```

### 6. Push and Create PR

```bash
git push origin feat/add-feature-x
# Create PR via GitHub UI
```

---

## Coding Standards

### Python Style

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.

```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # Pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
    "ARG",    # flake8-unused-arguments
    "SIM",    # flake8-simplify
]
ignore = [
    "E501",   # line too long (handled by formatter)
]

[tool.ruff.lint.isort]
known-first-party = ["headless_wheel_builder"]
```

### Type Annotations

All public APIs must have type annotations. Use [Pyright](https://github.com/microsoft/pyright) for checking.

```python
# Good
async def build_wheel(
    source: str | Path,
    output_dir: str | Path = "dist",
    python: str = "3.12",
) -> BuildResult:
    """Build a wheel from source."""
    ...

# Bad - missing types
def build_wheel(source, output_dir="dist", python="3.12"):
    ...
```

```toml
# pyproject.toml
[tool.pyright]
pythonVersion = "3.10"
typeCheckingMode = "strict"
reportMissingImports = true
reportMissingTypeStubs = false
```

### Docstrings

Use Google-style docstrings:

```python
async def build_wheel(
    source: str | Path,
    output_dir: str | Path = "dist",
    python: str = "3.12",
    isolation: Literal["auto", "venv", "docker", "none"] = "auto",
) -> BuildResult:
    """Build a wheel from source.

    Args:
        source: Path to project or git URL.
        output_dir: Directory for output files.
        python: Python version to use.
        isolation: Build isolation strategy.

    Returns:
        BuildResult containing wheel path and metadata.

    Raises:
        BuildError: If build fails.
        SourceError: If source cannot be resolved.

    Example:
        >>> result = await build_wheel(".", python="3.12")
        >>> print(result.wheel_path)
        dist/mypackage-1.0.0-py3-none-any.whl
    """
```

### Async Code

Use async/await for I/O-bound operations:

```python
# Good - async for I/O
async def clone_repository(url: str, dest: Path) -> None:
    process = await asyncio.create_subprocess_exec(
        "git", "clone", url, str(dest),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await process.wait()

# Bad - blocking I/O in async function
async def clone_repository(url: str, dest: Path) -> None:
    subprocess.run(["git", "clone", url, str(dest)])  # Blocks event loop!
```

### Error Handling

Use custom exceptions with clear messages:

```python
class HWBError(Exception):
    """Base exception for HWB."""
    pass

class BuildError(HWBError):
    """Build-related error."""

    def __init__(self, message: str, build_log: str = ""):
        super().__init__(message)
        self.build_log = build_log

class SourceError(HWBError):
    """Source resolution error."""
    pass

# Usage
try:
    result = await build_wheel(source)
except BuildError as e:
    logger.error(f"Build failed: {e}")
    logger.debug(f"Build log:\n{e.build_log}")
    raise
```

### Windows Compatibility

**CRITICAL**: All code must work on Windows.

```python
# Good - use pathlib
from pathlib import Path
output_dir = Path("dist")
wheel_path = output_dir / "mypackage-1.0.0-py3-none-any.whl"

# Bad - Unix-specific
output_dir = "dist"
wheel_path = output_dir + "/mypackage-1.0.0-py3-none-any.whl"

# Good - proper subprocess on Windows
process = await asyncio.create_subprocess_exec(
    str(python_path), "-m", "pip", "install", package,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)

# Bad - shell=True on Windows
process = subprocess.run(
    f"{python_path} -m pip install {package}",
    shell=True,  # Security risk and Windows issues
)

# Good - handle Windows-specific environment
env = os.environ.copy()
if sys.platform == "win32":
    env["XFORMERS_DISABLED"] = "1"  # RTX 5080 SM 12.0 unsupported
```

---

## Testing

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Fast, isolated tests
│   ├── test_source.py
│   ├── test_analyzer.py
│   └── test_builder.py
├── integration/             # Tests with real dependencies
│   ├── test_venv_isolation.py
│   └── test_docker_isolation.py
└── e2e/                     # Full workflow tests
    ├── test_build_workflow.py
    └── test_publish_workflow.py
```

### Writing Tests

```python
# tests/unit/test_analyzer.py
import pytest
from pathlib import Path
from headless_wheel_builder.core.analyzer import ProjectAnalyzer, ProjectMetadata

@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """Create a sample project for testing."""
    project_dir = tmp_path / "sample"
    project_dir.mkdir()

    pyproject = project_dir / "pyproject.toml"
    pyproject.write_text('''
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "sample"
version = "1.0.0"
''')

    return project_dir


class TestProjectAnalyzer:
    """Tests for ProjectAnalyzer."""

    async def test_analyze_pyproject(self, sample_project: Path):
        """Test analyzing a pyproject.toml project."""
        analyzer = ProjectAnalyzer()
        metadata = await analyzer.analyze(sample_project)

        assert metadata.name == "sample"
        assert metadata.version == "1.0.0"
        assert metadata.backend.name == "hatchling"

    async def test_analyze_missing_project(self, tmp_path: Path):
        """Test error handling for missing project."""
        analyzer = ProjectAnalyzer()

        with pytest.raises(SourceError):
            await analyzer.analyze(tmp_path / "nonexistent")

    @pytest.mark.parametrize("backend,expected", [
        ("hatchling.build", "hatchling"),
        ("setuptools.build_meta", "setuptools"),
        ("flit_core.buildapi", "flit"),
    ])
    async def test_backend_detection(
        self, tmp_path: Path, backend: str, expected: str
    ):
        """Test build backend detection."""
        # Setup project with specified backend
        ...
```

### Test Markers

```python
# Mark slow tests
@pytest.mark.slow
async def test_full_build():
    ...

# Mark tests requiring Docker
@pytest.mark.docker
async def test_manylinux_build():
    ...

# Mark Windows-specific tests
@pytest.mark.windows
async def test_windows_paths():
    ...

# Skip on CI
@pytest.mark.skipif(os.environ.get("CI"), reason="Not in CI")
async def test_local_only():
    ...
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=headless_wheel_builder --cov-report=html
open htmlcov/index.html

# Only unit tests
pytest tests/unit/

# Skip slow tests
pytest -m "not slow"

# Skip Docker tests (no Docker available)
pytest -m "not docker"

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

### Test Coverage Requirements

| Category | Minimum Coverage |
|----------|------------------|
| Core modules | 90% |
| CLI | 80% |
| Integration | 70% |
| Overall | 85% |

---

## Pre-commit Hooks

Pre-commit runs checks before each commit.

### Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-added-large-files

  - repo: local
    hooks:
      - id: pyright
        name: pyright
        entry: pyright
        language: system
        types: [python]
        pass_filenames: false
```

### Usage

```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files

# Skip hooks (emergency only)
git commit --no-verify -m "emergency fix"
```

---

## Pull Request Guidelines

### Before Submitting

- [ ] Tests pass locally: `pytest`
- [ ] Linters pass: `ruff check . && ruff format --check . && pyright`
- [ ] Documentation updated if needed
- [ ] Changelog entry added (for user-facing changes)
- [ ] Commit messages follow Conventional Commits

### PR Title

Use Conventional Commits format for PR title:

```
feat: add GPU support for Docker builds
fix: resolve Windows path handling in source resolver
docs: add publishing guide for private registries
```

### PR Description Template

```markdown
## Summary
Brief description of changes.

## Changes
- Added X
- Fixed Y
- Updated Z

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing performed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings introduced
```

### Review Process

1. CI must pass
2. At least one approval required
3. All comments addressed
4. Squash and merge (for clean history)

---

## Documentation

### Building Docs

```bash
# Build documentation
cd docs
make html

# Open in browser
open _build/html/index.html
```

### Doc Style

- Use clear, concise language
- Include code examples
- Add type annotations in examples
- Keep examples runnable

---

## Release Process

Releases are automated via GitHub Actions when tags are pushed.

### Creating a Release

```bash
# 1. Ensure main is up to date
git checkout main
git pull

# 2. Run full test suite
pytest

# 3. Bump version
hwb version bump minor --commit --tag

# 4. Push (triggers release workflow)
git push origin main --tags
```

### Manual Release (Emergency)

```bash
# Build
hwb build --sdist

# Publish (requires token)
hwb publish --token $PYPI_TOKEN
```

---

## Getting Help

- **Questions**: Open a Discussion
- **Bugs**: Open an Issue with reproduction steps
- **Features**: Open an Issue with use case description
- **Security**: Email security@example.com (do not open public issue)

---

## Code of Conduct

Be respectful, inclusive, and constructive. See CODE_OF_CONDUCT.md for details.

---

## License

By contributing, you agree that your contributions will be licensed under the project's MIT License.

---

## Changelog

| Date | Changes |
|------|---------|
| 2026-01-23 | Initial contributing guide |
