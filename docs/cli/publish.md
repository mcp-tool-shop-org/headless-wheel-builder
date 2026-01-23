# Publish Command

Publish wheels to PyPI, TestPyPI, or S3-compatible storage.

## Synopsis

```bash
hwb publish [OPTIONS] [FILES]...
```

## Description

The `publish` command uploads wheel and source distributions to package repositories. It supports PyPI, TestPyPI, custom PyPI-compatible registries, and S3-compatible storage.

## Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `FILES` | `dist/*` | Wheel/sdist files to publish |

If no files are specified, all `.whl` and `.tar.gz` files in `dist/` are published.

## Options

### Repository Options

| Option | Default | Description |
|--------|---------|-------------|
| `-r, --repository TYPE` | `pypi` | Target repository (`pypi`, `testpypi`, `s3`) |
| `--repository-url URL` | - | Custom repository URL |
| `--token TOKEN` | `$PYPI_TOKEN` | PyPI API token |

### Publishing Options

| Option | Default | Description |
|--------|---------|-------------|
| `--skip-existing` | Off | Skip if version already exists |
| `--dry-run` | Off | Validate without uploading |
| `--attestations` | Off | Generate attestations (PEP 740) |

### S3 Options

Only applicable when `-r s3`:

| Option | Default | Description |
|--------|---------|-------------|
| `--bucket BUCKET` | - | S3 bucket name (required) |
| `--prefix PREFIX` | `` | S3 key prefix |
| `--region REGION` | `us-east-1` | S3 region |
| `--generate-index` | Off | Generate PEP 503 index |

## Examples

### PyPI Publishing

```bash
# Publish all files in dist/
hwb publish

# Publish specific files
hwb publish dist/my_package-1.0.0-py3-none-any.whl

# Publish with explicit token
hwb publish --token pypi-AgEIcHlw...

# Skip if version exists
hwb publish --skip-existing
```

### TestPyPI

```bash
# Publish to TestPyPI
hwb publish -r testpypi

# With token
hwb publish -r testpypi --token pypi-AgEIcHlw...
```

### Validation

```bash
# Dry run (validate without uploading)
hwb publish --dry-run

# Verbose dry run
hwb publish --dry-run -v
```

### Custom Registry

```bash
# Private PyPI server
hwb publish --repository-url https://pypi.example.com/simple/

# With authentication
hwb publish --repository-url https://pypi.example.com/simple/ --token my-token
```

### S3 Publishing

```bash
# Publish to S3
hwb publish -r s3 --bucket my-wheels

# With prefix
hwb publish -r s3 --bucket my-wheels --prefix packages/

# Generate PEP 503 index
hwb publish -r s3 --bucket my-wheels --generate-index

# Custom region
hwb publish -r s3 --bucket my-wheels --region eu-west-1
```

### CI/CD Integration

```bash
# GitHub Actions example
hwb publish --skip-existing
# PYPI_TOKEN is read from environment

# With verification
hwb publish --dry-run && hwb publish
```

## Output

### Text Output (default)

```
Publishing to pypi
  Files: 2

╭─────────────── Publish Successful ───────────────╮
│ Status     File                                URL │
│ Published  my_package-1.0.0-py3-none-any.whl  https://pypi.org/... │
│ Published  my_package-1.0.0.tar.gz            https://pypi.org/... │
╰──────────────────────────────────────────────────╯
```

### JSON Output

```json
{
  "success": true,
  "published": [
    "dist/my_package-1.0.0-py3-none-any.whl",
    "dist/my_package-1.0.0.tar.gz"
  ],
  "skipped": [],
  "failed": [],
  "urls": [
    "https://pypi.org/project/my-package/1.0.0/",
    "https://pypi.org/project/my-package/1.0.0/"
  ],
  "errors": []
}
```

## Authentication

### PyPI Token

Set via environment variable (recommended):

```bash
export PYPI_TOKEN=pypi-AgEIcHlwaS5...
hwb publish
```

Or via command line:

```bash
hwb publish --token pypi-AgEIcHlwaS5...
```

### Getting a PyPI Token

1. Go to https://pypi.org/manage/account/token/
2. Create a new token with appropriate scope
3. Store securely (e.g., as a GitHub secret)

### S3 Authentication

Uses standard AWS credentials:

```bash
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
hwb publish -r s3 --bucket my-bucket
```

Or configure via `~/.aws/credentials`.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All files published successfully |
| 3 | One or more files failed to publish |

## See Also

- [Publishing Guide](../guide/publishing.md) - Detailed publishing guide
- [Build Command](build.md) - Build wheels before publishing
