# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x     | Yes       |
| < 1.0.0 | No        |

## Reporting a Vulnerability

Email: **64996768+mcp-tool-shop@users.noreply.github.com**

Include:
- Description of the vulnerability
- Steps to reproduce
- Version affected
- Potential impact

### Response timeline

| Action | Target |
|--------|--------|
| Acknowledge report | 48 hours |
| Assess severity | 7 days |
| Release fix | 30 days |

## Scope

This tool builds and publishes Python wheels. It interacts with the filesystem, git, Docker, and package registries.

- **Data touched:** Python source code (read-only), build artifacts (dist/), pyproject.toml, git history, Docker containers, package registry APIs (PyPI, DevPi, S3)
- **Data NOT touched:** user credentials directly (uses environment variables and OIDC tokens), system files outside the project directory
- **Network egress:** connects to package registries (PyPI, DevPi), GitHub API, Docker Hub — only when explicitly requested via CLI commands
- **Secrets handling:** reads `GITHUB_TOKEN`, `PYPI_TOKEN` from environment variables only; never logs or stores tokens; tokens are passed via environment to subprocesses
- **No telemetry** is collected or sent
- **Docker isolation:** when using Docker builds, code runs inside ephemeral containers with limited host access
