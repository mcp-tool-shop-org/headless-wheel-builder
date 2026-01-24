"""Workflow templates for GitHub Actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TemplateType(Enum):
    """Types of workflow templates."""

    RELEASE = "release"
    CI = "ci"
    PUBLISH = "publish"
    TEST = "test"
    DOCS = "docs"
    SECURITY = "security"


@dataclass
class WorkflowTemplate:
    """Template for a GitHub Actions workflow.

    Attributes:
        name: Template name
        description: Brief description
        template_type: Category of template
        filename: Default output filename
        triggers: Default workflow triggers
        content: YAML template content
        variables: Variables that can be customized
    """

    name: str
    description: str
    template_type: TemplateType
    filename: str
    triggers: list[str]
    content: str
    variables: dict[str, Any] = field(default_factory=lambda: {})


# Release workflow template
RELEASE_TEMPLATE = WorkflowTemplate(
    name="release",
    description="Build and release on tag push",
    template_type=TemplateType.RELEASE,
    filename="release.yml",
    triggers=["push tags"],
    variables={
        "python_version": "3.12",
        "generate_changelog": True,
    },
    content="""name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

jobs:
  release:
    name: Build and Release
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for changelog

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '{python_version}'

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install hwb
        run: uv pip install headless-wheel-builder

      - name: Build and Release
        env:
          GITHUB_TOKEN: ${{{{ secrets.GITHUB_TOKEN }}}}
        run: |
          hwb pipeline release ${{{{ github.ref_name }}}} \\
            --repo ${{{{ github.repository }}}} \\
            {changelog_flag}
""",
)

# CI workflow template
CI_TEMPLATE = WorkflowTemplate(
    name="ci",
    description="Continuous integration with tests",
    template_type=TemplateType.CI,
    filename="ci.yml",
    triggers=["push", "pull_request"],
    variables={
        "python_versions": ["3.10", "3.11", "3.12"],
        "platforms": ["ubuntu-latest", "windows-latest"],
    },
    content="""name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  test:
    name: Test (Python ${{{{ matrix.python-version }}}}, ${{{{ matrix.os }}}})
    runs-on: ${{{{ matrix.os }}}}
    strategy:
      fail-fast: false
      matrix:
        os: {platforms}
        python-version: {python_versions}

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{{{ matrix.python-version }}}}
        uses: actions/setup-python@v5
        with:
          python-version: ${{{{ matrix.python-version }}}}

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install dependencies
        run: uv sync --dev

      - name: Run tests
        run: uv run pytest --cov --cov-report=xml

      - name: Type check
        run: uv run pyright

  build:
    name: Build wheel
    runs-on: ubuntu-latest
    needs: test

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Build
        run: uv build

      - name: Upload wheel
        uses: actions/upload-artifact@v4
        with:
          name: wheel
          path: dist/*.whl
""",
)

# Publish to PyPI template
PUBLISH_TEMPLATE = WorkflowTemplate(
    name="publish",
    description="Publish to PyPI on release",
    template_type=TemplateType.PUBLISH,
    filename="publish.yml",
    triggers=["release published"],
    variables={
        "use_trusted_publishing": True,
    },
    content="""name: Publish to PyPI

on:
  release:
    types: [published]

permissions:
  id-token: write  # Required for trusted publishing

jobs:
  publish:
    name: Publish to PyPI
    runs-on: ubuntu-latest
    environment: pypi

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Build
        run: uv build

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
""",
)

# Test-only template
TEST_TEMPLATE = WorkflowTemplate(
    name="test",
    description="Run tests on push/PR",
    template_type=TemplateType.TEST,
    filename="test.yml",
    triggers=["push", "pull_request"],
    variables={
        "python_version": "3.12",
    },
    content="""name: Tests

on:
  push:
    branches: [main, master]
  pull_request:

jobs:
  test:
    name: Run Tests
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '{python_version}'

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install dependencies
        run: uv sync --dev

      - name: Run tests
        run: uv run pytest -v --tb=short
""",
)

# Security scanning template
SECURITY_TEMPLATE = WorkflowTemplate(
    name="security",
    description="Security scanning with CodeQL and dependency audit",
    template_type=TemplateType.SECURITY,
    filename="security.yml",
    triggers=["push", "schedule"],
    variables={},
    content="""name: Security

on:
  push:
    branches: [main, master]
  pull_request:
  schedule:
    - cron: '0 0 * * 1'  # Weekly on Monday

jobs:
  codeql:
    name: CodeQL Analysis
    runs-on: ubuntu-latest
    permissions:
      security-events: write

    steps:
      - uses: actions/checkout@v4

      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: python

      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v3

  deps:
    name: Dependency Audit
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install pip-audit
        run: pip install pip-audit

      - name: Audit dependencies
        run: pip-audit
""",
)

# Documentation template
DOCS_TEMPLATE = WorkflowTemplate(
    name="docs",
    description="Build and deploy documentation",
    template_type=TemplateType.DOCS,
    filename="docs.yml",
    triggers=["push main"],
    variables={
        "docs_dir": "docs",
    },
    content="""name: Documentation

on:
  push:
    branches: [main, master]
    paths:
      - 'docs/**'
      - 'mkdocs.yml'
      - '.github/workflows/docs.yml'

permissions:
  contents: write

jobs:
  deploy:
    name: Deploy Documentation
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install dependencies
        run: uv sync --group docs

      - name: Build and deploy
        run: uv run mkdocs gh-deploy --force
""",
)

# All templates indexed by name
TEMPLATES: dict[str, WorkflowTemplate] = {
    "release": RELEASE_TEMPLATE,
    "ci": CI_TEMPLATE,
    "publish": PUBLISH_TEMPLATE,
    "test": TEST_TEMPLATE,
    "security": SECURITY_TEMPLATE,
    "docs": DOCS_TEMPLATE,
}


def get_template(name: str) -> WorkflowTemplate | None:
    """Get a template by name.

    Args:
        name: Template name

    Returns:
        WorkflowTemplate or None if not found
    """
    return TEMPLATES.get(name.lower())


def list_templates() -> list[WorkflowTemplate]:
    """List all available templates.

    Returns:
        List of all WorkflowTemplates
    """
    return list(TEMPLATES.values())
