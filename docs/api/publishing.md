# Publishing API

The publish module provides publishers for uploading wheels to package registries.

## Overview

Two publishers are available:

- **PyPIPublisher** - PyPI, TestPyPI, and compatible registries
- **S3Publisher** - AWS S3 and S3-compatible storage

## Quick Start

```python
from pathlib import Path
from headless_wheel_builder.publish import (
    PublishConfig,
    PyPIPublisher,
    S3Publisher,
)
from headless_wheel_builder.publish.pypi import PyPIConfig
from headless_wheel_builder.publish.s3 import S3Config

# Publish to PyPI
pypi_config = PyPIConfig(repository="testpypi")
publisher = PyPIPublisher(pypi_config)

result = await publisher.publish(
    PublishConfig(files=[Path("dist/my_package-1.0.0-py3-none-any.whl")])
)

if result.success:
    print(f"Published to: {result.urls[0]}")
```

---

## PublishConfig

Common configuration for all publishers.

### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `files` | `list[Path]` | `[]` | Files to publish |
| `skip_existing` | `bool` | `False` | Skip existing versions |
| `dry_run` | `bool` | `False` | Validate without uploading |
| `verbose` | `bool` | `False` | Verbose output |
| `metadata` | `dict[str, str]` | `{}` | Custom metadata |

---

## PublishResult

Result of a publish operation.

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `success` | `bool` | Overall success |
| `files_published` | `list[Path]` | Successfully published files |
| `files_skipped` | `list[Path]` | Skipped files |
| `files_failed` | `list[Path]` | Failed files |
| `errors` | `list[str]` | Error messages |
| `urls` | `list[str]` | Published URLs |

### Methods

#### failure()

```python
@classmethod
def failure(error: str) -> PublishResult
```

Create a failure result.

### Example

```python
result = await publisher.publish(config)

if result.success:
    for path, url in zip(result.files_published, result.urls):
        print(f"Published {path.name} to {url}")
else:
    for error in result.errors:
        print(f"Error: {error}")
```

---

## PyPIPublisher

Publisher for PyPI and compatible registries.

### Constructor

```python
PyPIPublisher(config: PyPIConfig | None = None)
```

### PyPIConfig

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `repository` | `RepositoryType` | `"pypi"` | Repository type |
| `repository_url` | `str \| None` | `None` | Custom URL |
| `token` | `str \| None` | `None` | API token |
| `username` | `str \| None` | `None` | Username |
| `password` | `str \| None` | `None` | Password |
| `use_trusted_publisher` | `bool` | `False` | Use OIDC |
| `attestations` | `bool` | `False` | PEP 740 attestations |
| `verify_ssl` | `bool` | `True` | Verify SSL |
| `ca_bundle` | `str \| None` | `None` | CA bundle path |
| `max_retries` | `int` | `3` | Max upload retries |
| `retry_delay` | `float` | `1.0` | Retry delay (seconds) |
| `extra_args` | `list[str]` | `[]` | Extra twine args |

### Repository Types

```python
RepositoryType = Literal["pypi", "testpypi", "custom"]
```

### Methods

#### publish()

```python
async def publish(config: PublishConfig) -> PublishResult
```

Publish packages to registry.

#### check_credentials()

```python
async def check_credentials() -> bool
```

Verify credentials are valid.

#### check_package_exists()

```python
async def check_package_exists(name: str, version: str) -> bool
```

Check if package version exists.

### Authentication

Priority order:

1. `token` parameter
2. `username`/`password` parameters
3. Environment variables (`PYPI_TOKEN`, `TWINE_PASSWORD`)
4. Trusted Publisher (OIDC) for CI

### Example

```python
import os
from pathlib import Path
from headless_wheel_builder.publish.pypi import (
    PyPIConfig,
    PyPIPublisher,
    publish_to_pypi,
)
from headless_wheel_builder.publish import PublishConfig

# PyPI with token
config = PyPIConfig(
    repository="pypi",
    token=os.environ["PYPI_TOKEN"],
)
publisher = PyPIPublisher(config)

# TestPyPI
config = PyPIConfig(repository="testpypi")
publisher = PyPIPublisher(config)

# Custom registry
config = PyPIConfig(
    repository="custom",
    repository_url="https://pypi.example.com/simple/",
    token="my-token",
)
publisher = PyPIPublisher(config)

# Publish
result = await publisher.publish(
    PublishConfig(
        files=[Path("dist/my_package-1.0.0-py3-none-any.whl")],
        skip_existing=True,
    )
)

# Convenience function
result = await publish_to_pypi(
    files=[Path("dist/my_package-1.0.0-py3-none-any.whl")],
    repository="pypi",
    skip_existing=True,
)
```

### Trusted Publishers (OIDC)

For GitHub Actions with OIDC:

```python
config = PyPIConfig(
    repository="pypi",
    use_trusted_publisher=True,  # No token needed
)
```

Requires PyPI project configuration for trusted publishers.

---

## S3Publisher

Publisher for S3-compatible storage.

### Constructor

```python
S3Publisher(config: S3Config)
```

### S3Config

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `bucket` | `str` | Required | Bucket name |
| `prefix` | `str` | `""` | Key prefix |
| `region` | `str` | `"us-east-1"` | AWS region |
| `provider` | `S3Provider` | `"aws"` | Provider type |
| `endpoint_url` | `str \| None` | `None` | Custom endpoint |
| `access_key_id` | `str \| None` | `None` | Access key |
| `secret_access_key` | `str \| None` | `None` | Secret key |
| `session_token` | `str \| None` | `None` | Session token |
| `profile` | `str \| None` | `None` | AWS profile |
| `acl` | `str` | `"private"` | Object ACL |
| `storage_class` | `str` | `"STANDARD"` | Storage class |
| `content_type` | `str \| None` | Auto | Content type |
| `add_checksums` | `bool` | `True` | Add checksums |
| `generate_index` | `bool` | `False` | Generate PEP 503 index |
| `index_prefix` | `str` | `"simple/"` | Index prefix |
| `public_url` | `str \| None` | `None` | Custom public URL |
| `use_path_style` | `bool` | `False` | Path-style URLs |

### Provider Types

```python
S3Provider = Literal["aws", "minio", "r2", "gcs", "custom"]
```

### Methods

#### publish()

```python
async def publish(config: PublishConfig) -> PublishResult
```

Upload packages to S3.

#### check_credentials()

```python
async def check_credentials() -> bool
```

Verify S3 credentials and bucket access.

### Example

```python
import os
from pathlib import Path
from headless_wheel_builder.publish.s3 import (
    S3Config,
    S3Publisher,
    publish_to_s3,
)
from headless_wheel_builder.publish import PublishConfig

# AWS S3
config = S3Config(
    bucket="my-wheels",
    prefix="packages/",
    region="us-west-2",
)
publisher = S3Publisher(config)

# MinIO
config = S3Config(
    bucket="wheels",
    provider="minio",
    endpoint_url="http://localhost:9000",
    access_key_id="minioadmin",
    secret_access_key="minioadmin",
    use_path_style=True,
)

# Cloudflare R2
config = S3Config(
    bucket="my-wheels",
    provider="r2",
    access_key_id=os.environ["R2_ACCESS_KEY"],
    secret_access_key=os.environ["R2_SECRET_KEY"],
)

# With PEP 503 index
config = S3Config(
    bucket="my-wheels",
    generate_index=True,
    index_prefix="simple/",
    acl="public-read",  # Make index public
)

# Publish
result = await publisher.publish(
    PublishConfig(files=[Path("dist/my_package-1.0.0-py3-none-any.whl")])
)

# Convenience function
result = await publish_to_s3(
    files=[Path("dist/my_package-1.0.0-py3-none-any.whl")],
    bucket="my-wheels",
    prefix="packages/",
    generate_index=True,
)
```

### PEP 503 Index

When `generate_index=True`, creates:

```
s3://bucket/simple/index.html           # Root index
s3://bucket/simple/my-package/index.html  # Package index
```

Use with pip:

```bash
pip install --index-url https://bucket.s3.amazonaws.com/simple/ my-package
```

---

## Convenience Functions

### publish_to_pypi()

```python
async def publish_to_pypi(
    files: list[Path],
    token: str | None = None,
    repository: RepositoryType = "pypi",
    skip_existing: bool = False,
    dry_run: bool = False,
) -> PublishResult
```

Publish files to PyPI.

### publish_to_s3()

```python
async def publish_to_s3(
    files: list[Path],
    bucket: str,
    prefix: str = "",
    region: str = "us-east-1",
    skip_existing: bool = False,
    dry_run: bool = False,
    generate_index: bool = False,
) -> PublishResult
```

Publish files to S3.

---

## CI/CD Examples

### GitHub Actions (PyPI)

```yaml
- name: Publish to PyPI
  env:
    PYPI_TOKEN: ${{ secrets.PYPI_TOKEN }}
  run: |
    python -c "
    import asyncio
    from pathlib import Path
    from headless_wheel_builder.publish.pypi import publish_to_pypi

    files = list(Path('dist').glob('*.whl'))
    result = asyncio.run(publish_to_pypi(files))
    assert result.success
    "
```

### GitHub Actions (Trusted Publisher)

```yaml
permissions:
  id-token: write  # Required for OIDC

- name: Publish to PyPI
  run: |
    python -c "
    import asyncio
    from pathlib import Path
    from headless_wheel_builder.publish.pypi import PyPIConfig, PyPIPublisher
    from headless_wheel_builder.publish import PublishConfig

    config = PyPIConfig(use_trusted_publisher=True)
    publisher = PyPIPublisher(config)
    files = list(Path('dist').glob('*.whl'))
    result = asyncio.run(publisher.publish(PublishConfig(files=files)))
    assert result.success
    "
```

### S3 with GitHub Actions

```yaml
- name: Publish to S3
  env:
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
  run: |
    python -c "
    import asyncio
    from pathlib import Path
    from headless_wheel_builder.publish.s3 import publish_to_s3

    files = list(Path('dist').glob('*.whl'))
    result = asyncio.run(publish_to_s3(
        files=files,
        bucket='my-wheels',
        generate_index=True,
    ))
    assert result.success
    "
```
