# Headless Wheel Builder - Publishing Documentation

> **Purpose**: Comprehensive guide for publishing wheels to PyPI, TestPyPI, and private registries.
> **Last Updated**: 2026-01-23

---

## 2026 Best Practices Applied

> **Sources**: [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/), [PyPI Publishing Guide](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/), [DevPi Documentation](https://devpi.net/docs/devpi/devpi/stable/%2Bd/index.html), [Artifactory PyPI](https://jfrog.com/help/r/jfrog-artifactory-documentation/pypi-repositories), [Google Artifact Registry](https://cloud.google.com/artifact-registry/docs/python), [Cloudsmith Python](https://help.cloudsmith.io/docs/python-repository)

This publishing guide follows 2026 best practices:

1. **Trusted Publishers First**: OIDC-based publishing eliminates long-lived API tokens. This is the recommended approach for all CI/CD workflows.

2. **TestPyPI for Validation**: Always test uploads on TestPyPI before production releases.

3. **Automated Releases**: Releases triggered by git tags with full CI/CD validation.

4. **Multi-Registry Support**: Support for PyPI, private registries, and S3-compatible storage.

5. **Attestation Ready**: Architecture supports SLSA provenance and Sigstore signing.

6. **Index Compatibility**: Private registries follow PEP 503 Simple API for pip compatibility.

7. **Credential Rotation**: Short-lived tokens preferred; long-lived tokens rotated regularly.

8. **Release Checklist**: Automated validation before publishing.

---

## Quick Start

### Publish to PyPI with Trusted Publisher (Recommended)

**1. Configure Trusted Publisher on PyPI**

Go to https://pypi.org/manage/project/YOUR_PROJECT/settings/publishing/ and add:

- **Publisher**: GitHub Actions
- **Owner**: your-username
- **Repository**: your-repo
- **Workflow name**: release.yml
- **Environment**: release (optional, adds approval requirement)

**2. Create GitHub Actions Workflow**

```yaml
# .github/workflows/release.yml
name: Release to PyPI

on:
  push:
    tags:
      - 'v*'

permissions:
  id-token: write  # Required for Trusted Publishing
  contents: read

jobs:
  release:
    runs-on: ubuntu-latest
    environment: release  # Optional: requires approval

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install hwb
        run: pip install headless-wheel-builder

      - name: Build wheel
        run: hwb build --sdist --checksum

      - name: Publish to PyPI
        run: hwb publish --trusted-publisher
```

**3. Create a Release**

```bash
# Bump version and create tag
hwb version bump patch --commit --tag --push

# Or manually
git tag v1.0.0
git push origin v1.0.0
```

---

## PyPI Publishing

### Using Trusted Publishers (OIDC)

Trusted Publishers is PyPI's preferred authentication method, using OpenID Connect (OIDC) for short-lived token exchange.

**Supported CI Providers**:
| Provider | Supported | Notes |
|----------|-----------|-------|
| GitHub Actions | Yes | Full support |
| GitLab CI/CD | Yes | gitlab.com only (not self-hosted) |
| Google Cloud Build | Yes | Via service account |
| Azure Pipelines | Planned | Coming soon |
| CircleCI | No | Use API tokens |

**Benefits**:
- No secrets to manage or rotate
- Tokens expire in 15 minutes
- Cryptographically verified identity
- Full audit trail

**GitHub Actions Setup**:
```yaml
permissions:
  id-token: write  # This permission is required

steps:
  - name: Publish
    run: hwb publish --trusted-publisher
```

**GitLab CI/CD Setup**:
```yaml
publish:
  image: python:3.12
  id_tokens:
    PYPI_ID_TOKEN:
      aud: pypi  # Audience for PyPI

  script:
    - pip install headless-wheel-builder
    - hwb build
    - hwb publish --trusted-publisher
```

### Using API Tokens

For CI systems without OIDC support, use API tokens.

**Generate Token**:
1. Go to https://pypi.org/manage/account/token/
2. Create token scoped to specific project
3. Store as CI secret (never in code)

**Usage**:
```bash
# Via environment variable (recommended)
export PYPI_TOKEN=pypi-AgEIcH...
hwb publish

# Via CLI argument (less secure - visible in process list)
hwb publish --token "$PYPI_TOKEN"
```

**GitHub Actions with Token**:
```yaml
- name: Publish to PyPI
  env:
    PYPI_TOKEN: ${{ secrets.PYPI_TOKEN }}
  run: hwb publish
```

### TestPyPI

Always test on TestPyPI before production releases.

**1. Configure TestPyPI Trusted Publisher**

Same process at https://test.pypi.org/manage/project/YOUR_PROJECT/settings/publishing/

**2. Publish to TestPyPI**:
```bash
hwb publish --repository testpypi --trusted-publisher
```

**3. Test Installation**:
```bash
pip install --index-url https://test.pypi.org/simple/ mypackage
```

**Configuration**:
```toml
# pyproject.toml
[tool.hwb.publish]
# Test on TestPyPI first
test-repository = "testpypi"
```

---

## Private Registry Publishing

### DevPi

DevPi is a popular self-hosted Python package server.

**Setup DevPi Server**:
```bash
pip install devpi-server devpi-web
devpi-server --init
devpi-server --start --host 0.0.0.0 --port 3141
```

**Configure HWB**:
```toml
# pyproject.toml
[tool.hwb.registries.internal]
url = "https://devpi.internal.company.com/company/packages/"
username = "${DEVPI_USER}"
password = "${DEVPI_PASSWORD}"
```

**Publish**:
```bash
# Using named registry
hwb publish --repository internal

# Or direct URL
hwb publish --url https://devpi.internal.company.com/company/packages/
```

### JFrog Artifactory

Enterprise-grade artifact repository.

**Configure Repository** (in Artifactory):
1. Create PyPI repository (local)
2. Set repository key (e.g., `pypi-local`)
3. Configure virtual repository for resolution

**Configure HWB**:
```toml
# pyproject.toml
[tool.hwb.registries.artifactory]
url = "https://artifactory.company.com/artifactory/api/pypi/pypi-local/"
username = "${ARTIFACTORY_USER}"
password = "${ARTIFACTORY_TOKEN}"  # API key or access token
```

**Publish**:
```bash
hwb publish --repository artifactory
```

### AWS CodeArtifact

AWS-managed package repository.

**Setup**:
```bash
# Get authorization token
export CODEARTIFACT_AUTH_TOKEN=$(aws codeartifact get-authorization-token \
    --domain my-domain \
    --query authorizationToken \
    --output text)

# Get repository URL
export CODEARTIFACT_URL=$(aws codeartifact get-repository-endpoint \
    --domain my-domain \
    --repository my-repo \
    --format pypi \
    --query repositoryEndpoint \
    --output text)
```

**Configure HWB**:
```toml
# pyproject.toml
[tool.hwb.registries.codeartifact]
url = "${CODEARTIFACT_URL}"
username = "aws"
password = "${CODEARTIFACT_AUTH_TOKEN}"
```

### Google Artifact Registry

GCP-managed package repository.

**Setup**:
```bash
# Create repository
gcloud artifacts repositories create python-packages \
    --repository-format=python \
    --location=us-central1

# Configure authentication
gcloud auth configure-docker us-central1-python.pkg.dev
```

**Configure HWB**:
```toml
# pyproject.toml
[tool.hwb.registries.gar]
url = "https://us-central1-python.pkg.dev/my-project/python-packages/"
# Uses gcloud credentials automatically
```

**Publish with OIDC (GCP Workload Identity)**:
```yaml
# GitHub Actions with GCP Workload Identity
- uses: google-github-actions/auth@v2
  with:
    workload_identity_provider: 'projects/123456/locations/global/workloadIdentityPools/my-pool/providers/my-provider'
    service_account: 'my-sa@my-project.iam.gserviceaccount.com'

- name: Publish
  run: hwb publish --repository gar
```

### Azure Artifacts

Azure DevOps package repository.

**Configure**:
```toml
# pyproject.toml
[tool.hwb.registries.azure]
url = "https://pkgs.dev.azure.com/org/project/_packaging/feed/pypi/upload/"
username = "${AZURE_ARTIFACTS_USER}"
password = "${AZURE_ARTIFACTS_PAT}"  # Personal Access Token
```

### Cloudsmith

Cloud-hosted package registry.

**Configure**:
```toml
# pyproject.toml
[tool.hwb.registries.cloudsmith]
url = "https://python.cloudsmith.io/org/repo/"
username = "${CLOUDSMITH_API_USER}"
password = "${CLOUDSMITH_API_KEY}"
```

---

## S3-Compatible Storage

Host packages on S3 with a PEP 503-compatible index.

### Setup

**1. Create S3 Bucket**:
```bash
aws s3 mb s3://my-python-packages
```

**2. Configure HWB**:
```toml
# pyproject.toml
[tool.hwb.registries.s3]
type = "s3"
bucket = "my-python-packages"
region = "us-east-1"
prefix = "packages/"

# Optional: CloudFront CDN
cdn_url = "https://d1234567890.cloudfront.net"

# Generate PEP 503 index
generate_index = true
```

**3. Publish**:
```bash
hwb publish --repository s3
```

### Generated Index Structure

```
s3://my-python-packages/
├── packages/
│   └── mypackage/
│       ├── mypackage-1.0.0-py3-none-any.whl
│       ├── mypackage-1.0.1-py3-none-any.whl
│       └── mypackage-1.0.1.tar.gz
└── simple/                          # PEP 503 Simple API
    ├── index.html
    └── mypackage/
        └── index.html
```

### Install from S3

```bash
# Direct S3 URL
pip install --index-url https://my-python-packages.s3.amazonaws.com/simple/ mypackage

# Via CloudFront CDN
pip install --index-url https://d1234567890.cloudfront.net/simple/ mypackage
```

---

## Multi-Registry Publishing

Publish to multiple registries in a single command.

**Configure Multiple Registries**:
```toml
# pyproject.toml
[tool.hwb.publish]
# Publish to all these registries
registries = ["pypi", "internal", "s3-backup"]

[tool.hwb.registries.internal]
url = "https://devpi.company.com/company/prod/"
username = "${DEVPI_USER}"
password = "${DEVPI_PASSWORD}"

[tool.hwb.registries.s3-backup]
type = "s3"
bucket = "python-packages-backup"
```

**Publish to All**:
```bash
# Publish to all configured registries
hwb publish --all

# Publish to specific registries
hwb publish --repository pypi --repository internal
```

---

## Release Workflow

### Complete Release Automation

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  id-token: write
  contents: write  # For GitHub releases

jobs:
  # Validate before building
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install hwb
        run: pip install headless-wheel-builder

      - name: Validate project
        run: hwb inspect --check-all

  # Build on multiple platforms
  build:
    needs: validate
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python: ['3.10', '3.11', '3.12', '3.13']

    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}

      - name: Build wheel
        run: |
          pip install headless-wheel-builder
          hwb build --python ${{ matrix.python }}

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: wheels-${{ matrix.os }}-${{ matrix.python }}
          path: dist/*.whl

  # Build manylinux wheels
  build-manylinux:
    needs: validate
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Build manylinux wheels
        run: |
          pip install headless-wheel-builder
          hwb matrix --platform linux --isolation docker

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: wheels-manylinux
          path: dist/*.whl

  # Publish to PyPI
  publish:
    needs: [build, build-manylinux]
    runs-on: ubuntu-latest
    environment: release

    steps:
      - uses: actions/checkout@v4

      - name: Download all wheels
        uses: actions/download-artifact@v4
        with:
          path: dist
          merge-multiple: true

      - name: Install hwb
        run: pip install headless-wheel-builder

      - name: Publish to PyPI
        run: hwb publish dist/*.whl --trusted-publisher

  # Create GitHub Release
  github-release:
    needs: publish
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Download all wheels
        uses: actions/download-artifact@v4
        with:
          path: dist
          merge-multiple: true

      - name: Generate changelog
        run: |
          pip install headless-wheel-builder
          hwb version changelog --format github > RELEASE_NOTES.md

      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          body_path: RELEASE_NOTES.md
          files: dist/*
```

### Pre-Release Checklist

HWB validates before publishing:

```bash
# Manual validation
hwb publish --dry-run

# Automated checks:
# ✓ Version not already on PyPI
# ✓ All required metadata present
# ✓ README renders correctly
# ✓ License file exists
# ✓ Wheel structure valid
# ✓ No sensitive files included
```

---

## Troubleshooting

### Common Errors

**"Invalid or non-existent authentication information"**
- Check that Trusted Publisher is configured correctly
- Verify workflow name matches exactly
- Ensure `id-token: write` permission is set

**"File already exists"**
- Version already published (versions are immutable)
- Bump version: `hwb version bump patch`
- Or use `--skip-existing` flag

**"400 Bad Request: description failed to render"**
- README has invalid markup
- Test with: `hwb inspect --check-metadata`
- Use `long_description_content_type` in metadata

**"403 Forbidden"**
- Token doesn't have permission for this project
- Create project-scoped token
- Check Trusted Publisher repository settings

### Debug Mode

```bash
# Verbose output
hwb publish -vvv

# See exact twine command
hwb publish --dry-run -vvv
```

---

## Registry Comparison

| Feature | PyPI | DevPi | Artifactory | CodeArtifact | GAR |
|---------|------|-------|-------------|--------------|-----|
| Free tier | Yes | Self-hosted | No | Limited | Limited |
| OIDC auth | Yes | No | Yes | Yes | Yes |
| Private packages | No | Yes | Yes | Yes | Yes |
| Caching/proxy | No | Yes | Yes | Yes | Yes |
| Access control | Basic | Basic | Enterprise | IAM | IAM |
| High availability | Yes | Manual | Yes | Yes | Yes |
| Geo-replication | CDN | Manual | Yes | Cross-region | Multi-region |

---

## Changelog

| Date | Changes |
|------|---------|
| 2026-01-23 | Initial publishing documentation |
