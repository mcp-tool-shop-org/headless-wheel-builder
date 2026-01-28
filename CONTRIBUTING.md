# Contributing to Headless Wheel Builder

Thank you for your interest in contributing! This project provides a universal Python wheel builder with headless GitHub operations for CI/CD pipelines.

## Development Setup

```bash
git clone https://github.com/mcp-tool-shop/headless-wheel-builder.git
cd headless-wheel-builder
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev,test]"
pre-commit install
```

## How to Contribute

### Reporting Issues

If you find a bug or have a feature request:

1. Check existing [issues](https://github.com/mcp-tool-shop/headless-wheel-builder/issues)
2. If not found, create a new issue with:
   - Clear description of the problem or feature
   - Steps to reproduce (for bugs)
   - Expected vs. actual behavior
   - Your environment (Python version, OS)
   - Example wheel build configuration if relevant

### Contributing Code

1. **Fork the repository** and create a branch from `main`
2. **Make your changes**
   - Follow the existing code style (enforced by ruff)
   - Use type hints (checked by pyright)
   - Add tests for new functionality
3. **Test your changes**
   ```bash
   pytest
   pyright
   ruff check
   ```
4. **Commit your changes**
   - Use clear, descriptive commit messages
   - Reference issue numbers when applicable
5. **Submit a pull request**
   - Describe what your PR does and why
   - Link to related issues

## Project Structure

```
headless-wheel-builder/
├── src/
│   └── headless_wheel_builder/
│       ├── __init__.py
│       ├── cli.py          # Click CLI interface
│       ├── builder.py      # Core wheel building logic
│       ├── github.py       # GitHub API integration
│       ├── config.py       # Configuration management
│       └── utils.py        # Shared utilities
├── tests/                  # Test suite
├── docs/                   # MkDocs documentation
└── pyproject.toml          # Project metadata
```

## Testing

Run the test suite:

```bash
pytest                      # All tests
pytest tests/test_builder.py  # Specific test file
pytest -v                   # Verbose output
pytest --cov                # With coverage report
```

## Code Quality

We use several tools to maintain code quality:

### Ruff (Linter + Formatter)
```bash
ruff check .                # Check for issues
ruff check --fix .          # Auto-fix issues
ruff format .               # Format code
```

### Pyright (Type Checker)
```bash
pyright                     # Type check all code
```

### Pre-commit Hooks
```bash
pre-commit run --all-files  # Run all hooks manually
```

## Adding New Features

### Adding a New Build Target

1. Add configuration schema in `config.py`
2. Implement build logic in `builder.py`
3. Add CLI command in `cli.py`
4. Add tests in `tests/`
5. Update documentation in `docs/`

### Adding GitHub Integration Features

1. Add API methods in `github.py`
2. Handle authentication and rate limiting
3. Add error handling for API failures
4. Test with mock responses

## Documentation

Update documentation when adding features:

```bash
mkdocs serve                # Preview docs locally
```

Documentation is in `docs/` and uses MkDocs with the Material theme.

## Release Process

(For maintainers)

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md` with changes
3. Create git tag: `git tag v0.x.x`
4. Push tag: `git push origin v0.x.x`
5. GitHub Actions will build and publish to PyPI

## Design Principles

- **Headless by default**: Designed for CI/CD environments
- **Configuration-driven**: Support multiple build configurations
- **Error handling**: Clear, actionable error messages
- **Type safety**: Full type coverage with Pyright
- **Testing**: Comprehensive test coverage
- **Security**: Validate inputs, handle credentials safely

## Common Tasks

### Building Wheels Locally

```bash
hwb build                   # Build with default config
hwb build --config custom.toml  # Custom config
hwb build --validate        # Validate before building
```

### GitHub Operations

```bash
hwb github release create --tag v1.0.0
hwb github upload --tag v1.0.0 dist/*.whl
```

## Questions?

Open an issue or start a discussion in the [MCP Tool Shop](https://github.com/mcp-tool-shop) organization.
