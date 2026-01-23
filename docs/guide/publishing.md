# Publishing

Headless Wheel Builder supports publishing to PyPI, TestPyPI, private registries, and S3-compatible storage.

## Quick Start

### Publish to PyPI

```bash
hwb publish dist/*.whl
```

### Publish to TestPyPI

```bash
hwb publish dist/*.whl --repository testpypi
```

### Dry Run

Validate without uploading:

```bash
hwb publish dist/*.whl --dry-run
```

## Authentication

### API Token (Recommended)

Set your PyPI API token as an environment variable:

```bash
export TWINE_PASSWORD=pypi-xxxxxxxxxxxxxxxxxxxxx
hwb publish dist/*.whl
```

Or use the `--token` option:

```bash
hwb publish dist/*.whl --token pypi-xxxxxxxxxxxxxxxxxxxxx
```

### Username/Password

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-xxxxxxxxxxxxxxxxxxxxx
hwb publish dist/*.whl
```

Or interactively:

```bash
hwb publish dist/*.whl --username __token__
# Will prompt for password
```

### Trusted Publishing (OIDC)

For GitHub Actions, use trusted publishing without storing credentials:

```yaml
# .github/workflows/release.yml
jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
    steps:
      - uses: pypa/gh-action-pypi-publish@release/v1
```

See [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/) for setup.

## Registries

### PyPI

The default registry:

```bash
hwb publish dist/*.whl
# or explicitly
hwb publish dist/*.whl --repository pypi
```

### TestPyPI

For testing before production:

```bash
hwb publish dist/*.whl --repository testpypi
```

!!! tip
    Always test on TestPyPI first to verify your package uploads correctly.

### Private Registries

#### Custom URL

```bash
hwb publish dist/*.whl --repository-url https://pypi.example.com/simple/
```

#### Artifactory

```bash
hwb publish dist/*.whl \
  --repository-url https://artifactory.example.com/api/pypi/pypi-local/ \
  --username admin \
  --token your-token
```

#### GitLab Package Registry

```bash
hwb publish dist/*.whl \
  --repository-url https://gitlab.com/api/v4/projects/PROJECT_ID/packages/pypi \
  --username __token__ \
  --token ${GITLAB_TOKEN}
```

#### AWS CodeArtifact

```bash
# Get token
TOKEN=$(aws codeartifact get-authorization-token --domain mydomain --query authorizationToken --output text)

hwb publish dist/*.whl \
  --repository-url https://mydomain-123456789.d.codeartifact.us-east-1.amazonaws.com/pypi/my-repo/simple/ \
  --token ${TOKEN}
```

## S3-Compatible Storage

Publish wheels to S3 or compatible services (MinIO, Cloudflare R2).

### AWS S3

```bash
hwb publish dist/*.whl \
  --target s3 \
  --s3-bucket my-pypi-bucket \
  --s3-prefix packages/
```

Configure AWS credentials via environment or ~/.aws/credentials:

```bash
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-east-1
```

### MinIO

```bash
hwb publish dist/*.whl \
  --target s3 \
  --s3-endpoint http://localhost:9000 \
  --s3-bucket wheels \
  --s3-access-key minioadmin \
  --s3-secret-key minioadmin
```

### Cloudflare R2

```bash
hwb publish dist/*.whl \
  --target s3 \
  --s3-endpoint https://ACCOUNT_ID.r2.cloudflarestorage.com \
  --s3-bucket my-wheels \
  --s3-access-key your-access-key \
  --s3-secret-key your-secret-key
```

### PEP 503 Simple Index

When publishing to S3, a PEP 503 compliant index is automatically generated:

```
my-bucket/
├── simple/
│   ├── index.html          # Package listing
│   ├── my-package/
│   │   └── index.html      # Version listing
│   └── other-package/
│       └── index.html
└── packages/
    ├── my_package-1.0.0-py3-none-any.whl
    └── other_package-2.0.0-py3-none-any.whl
```

Install from your S3 index:

```bash
pip install my-package --index-url https://my-bucket.s3.amazonaws.com/simple/
```

## Publishing Options

### Skip Existing

Don't fail if the version already exists:

```bash
hwb publish dist/*.whl --skip-existing
```

### Verbose Output

```bash
hwb publish dist/*.whl --verbose
```

### Specify Files

```bash
# All wheels
hwb publish dist/*.whl

# Specific wheel
hwb publish dist/my_package-1.0.0-py3-none-any.whl

# Wheels and sdist
hwb publish dist/*
```

### Sign Packages

Sign packages with GPG:

```bash
hwb publish dist/*.whl --sign
```

## Configuration File

Create `.pypirc` for registry configuration:

```ini
[distutils]
index-servers =
    pypi
    testpypi
    private

[pypi]
username = __token__
password = pypi-xxxxxxxxxxxxxxxxxxxxx

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-xxxxxxxxxxxxxxxxxxxxx

[private]
repository = https://pypi.example.com/simple/
username = myuser
password = mypassword
```

Then use:

```bash
hwb publish dist/*.whl --repository private
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Publish

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      id-token: write  # For trusted publishing
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install headless-wheel-builder[publish]

      - name: Build
        run: hwb build --output dist/

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

### GitLab CI

```yaml
publish:
  stage: deploy
  image: python:3.12
  script:
    - pip install headless-wheel-builder[publish]
    - hwb build --output dist/
    - hwb publish dist/*.whl --token ${PYPI_TOKEN}
  only:
    - tags
```

## Programmatic Usage

```python
from headless_wheel_builder.publish.pypi import PyPIPublisher, PyPIConfig

# Configure
config = PyPIConfig(
    repository_url="https://upload.pypi.org/legacy/",
    api_token="pypi-xxxxxxxxxxxxxxxxxxxxx",
)

# Publish
publisher = PyPIPublisher(config)
result = await publisher.publish(
    files=["dist/my_package-1.0.0-py3-none-any.whl"],
    skip_existing=True,
)

if result.success:
    print(f"Published: {result.uploaded_files}")
else:
    print(f"Failed: {result.errors}")
```

### S3 Publishing

```python
from headless_wheel_builder.publish.s3 import S3Publisher, S3Config

config = S3Config(
    bucket="my-pypi-bucket",
    prefix="packages/",
    access_key="AKIA...",
    secret_key="...",
    region="us-east-1",
)

publisher = S3Publisher(config)
result = await publisher.publish(
    files=["dist/my_package-1.0.0-py3-none-any.whl"],
    generate_index=True,
)
```

## Troubleshooting

### Authentication Failed

```
Error: 403 Forbidden - Invalid or missing credentials
```

**Solution:** Check your API token is valid and has upload permissions.

### Package Already Exists

```
Error: 400 Bad Request - File already exists
```

**Solution:** Use `--skip-existing` or bump your version number.

### Invalid Wheel

```
Error: Invalid wheel filename
```

**Solution:** Ensure the wheel follows PEP 427 naming conventions.

### Network Error

```
Error: Connection failed
```

**Solution:** Check internet connection and firewall settings.
