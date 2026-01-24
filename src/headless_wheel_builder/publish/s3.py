"""S3-compatible storage publisher."""

from __future__ import annotations

import asyncio
import hashlib
import mimetypes
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal
from urllib.parse import urljoin

from headless_wheel_builder.exceptions import PublishError
from headless_wheel_builder.publish.base import BasePublisher, PublishConfig, PublishResult

if TYPE_CHECKING:
    from pathlib import Path

S3Provider = Literal["aws", "minio", "r2", "gcs", "custom"]


@dataclass
class S3Config:
    """Configuration for S3 publishing."""

    # Bucket settings
    bucket: str = ""
    prefix: str = ""  # Key prefix (e.g., "wheels/")
    region: str = "us-east-1"

    # Provider selection
    provider: S3Provider = "aws"
    endpoint_url: str | None = None  # For MinIO, R2, custom endpoints

    # Authentication
    access_key_id: str | None = None
    secret_access_key: str | None = None
    session_token: str | None = None  # For temporary credentials
    profile: str | None = None  # AWS profile name

    # Upload settings
    acl: str = "private"  # private, public-read, etc.
    storage_class: str = "STANDARD"  # STANDARD, REDUCED_REDUNDANCY, etc.
    content_type: str | None = None  # Auto-detect if not set

    # Checksums
    add_checksums: bool = True  # Add MD5/SHA256 metadata

    # Generate index
    generate_index: bool = False  # Generate simple HTML index (PEP 503)
    index_prefix: str = "simple/"  # Prefix for index files

    # Public URL settings
    public_url: str | None = None  # Custom public URL for the bucket
    use_path_style: bool = False  # Use path-style URLs (for MinIO)


class S3Publisher(BasePublisher):
    """
    Publisher for S3-compatible storage.

    Supports:
    - AWS S3
    - MinIO
    - Cloudflare R2
    - Google Cloud Storage (with S3 compatibility)
    - Any S3-compatible storage

    Can generate PEP 503 simple index for pip compatibility.

    Example:
        >>> config = S3Config(
        ...     bucket="my-wheels",
        ...     prefix="packages/",
        ...     region="us-west-2",
        ... )
        >>> publisher = S3Publisher(config)
        >>> result = await publisher.publish(PublishConfig(files=[wheel_path]))
    """

    def __init__(self, config: S3Config) -> None:
        if not config.bucket:
            raise ValueError("S3 bucket is required")
        self.config = config
        self._client = None

    def _get_client(self):
        """Get or create S3 client."""
        if self._client is not None:
            return self._client

        try:
            import boto3
            from botocore.config import Config
        except ImportError:
            raise PublishError(
                "boto3 is required for S3 publishing. "
                "Install with: pip install headless-wheel-builder[s3]"
            )

        # Build client kwargs
        kwargs = {
            "region_name": self.config.region,
        }

        # Endpoint URL for non-AWS providers
        if self.config.endpoint_url:
            kwargs["endpoint_url"] = self.config.endpoint_url
        elif self.config.provider == "minio":
            # MinIO typically runs on localhost
            kwargs["endpoint_url"] = "http://localhost:9000"
        elif self.config.provider == "r2":
            # Cloudflare R2
            account_id = os.environ.get("R2_ACCOUNT_ID", "")
            kwargs["endpoint_url"] = f"https://{account_id}.r2.cloudflarestorage.com"

        # Credentials
        if self.config.access_key_id and self.config.secret_access_key:
            kwargs["aws_access_key_id"] = self.config.access_key_id
            kwargs["aws_secret_access_key"] = self.config.secret_access_key
            if self.config.session_token:
                kwargs["aws_session_token"] = self.config.session_token
        elif self.config.profile:
            # Use AWS profile
            session = boto3.Session(profile_name=self.config.profile)
            self._client = session.client("s3", **kwargs)
            return self._client

        # Environment variables as fallback
        if not kwargs.get("aws_access_key_id"):
            kwargs["aws_access_key_id"] = os.environ.get("AWS_ACCESS_KEY_ID")
            kwargs["aws_secret_access_key"] = os.environ.get("AWS_SECRET_ACCESS_KEY")

        # Path-style config
        if self.config.use_path_style:
            kwargs["config"] = Config(s3={"addressing_style": "path"})

        self._client = boto3.client("s3", **kwargs)
        return self._client

    async def check_credentials(self) -> bool:
        """Check if credentials are valid by listing bucket."""
        try:
            client = self._get_client()
            # Try to list (with max 1 item) to verify access
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: client.list_objects_v2(
                    Bucket=self.config.bucket,
                    MaxKeys=1,
                ),
            )
            return True
        except Exception:
            return False

    async def publish(self, config: PublishConfig) -> PublishResult:
        """Publish packages to S3."""
        result = PublishResult(success=True)

        # Validate files
        errors = self._validate_files(config.files)
        if errors:
            for error in errors:
                result.errors.append(error)
            result.success = False
            return result

        if not config.files:
            return PublishResult.failure("No files to publish")

        # Check credentials
        if not await self.check_credentials():
            return PublishResult.failure(
                "S3 credentials invalid or bucket not accessible. "
                "Check AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY or bucket permissions."
            )

        # Get client
        client = self._get_client()
        loop = asyncio.get_event_loop()

        # Track packages for index generation
        packages: dict[str, list[dict]] = {}

        # Upload each file
        for path in config.files:
            info = self._get_package_info(path)
            key = self._get_key(path)

            # Dry run
            if config.dry_run:
                url = self._get_public_url(key)
                result.add_published(path, url)
                result.errors.append(f"[DRY RUN] Would upload to s3://{self.config.bucket}/{key}")
                continue

            try:
                # Check if exists
                if config.skip_existing:
                    try:
                        await loop.run_in_executor(
                            None,
                            lambda: client.head_object(
                                Bucket=self.config.bucket,
                                Key=key,
                            ),
                        )
                        result.add_skipped(path, "Already exists")
                        continue
                    except Exception:
                        pass  # Doesn't exist, proceed with upload

                # Calculate checksums
                checksums = self._calculate_checksums(path) if self.config.add_checksums else {}

                # Prepare upload args
                extra_args = {
                    "ACL": self.config.acl,
                    "StorageClass": self.config.storage_class,
                    "ContentType": self._get_content_type(path),
                    "Metadata": {
                        "package-name": info["name"],
                        "package-version": info["version"],
                        **checksums,
                    },
                }

                # Upload
                await loop.run_in_executor(
                    None,
                    lambda: client.upload_file(
                        str(path),
                        self.config.bucket,
                        key,
                        ExtraArgs=extra_args,
                    ),
                )

                url = self._get_public_url(key)
                result.add_published(path, url)

                # Track for index
                if self.config.generate_index:
                    pkg_name = info["name"].lower().replace("-", "_")
                    if pkg_name not in packages:
                        packages[pkg_name] = []
                    packages[pkg_name].append(
                        {
                            "filename": path.name,
                            "url": url,
                            "sha256": checksums.get("sha256", ""),
                        }
                    )

            except Exception as e:
                result.add_failed(path, str(e))

        # Generate index if requested
        if self.config.generate_index and packages and not config.dry_run:
            try:
                await self._generate_index(packages)
            except Exception as e:
                result.errors.append(f"Failed to generate index: {e}")

        return result

    def _get_key(self, path: Path) -> str:
        """Get S3 key for a file."""
        prefix = self.config.prefix.strip("/")
        if prefix:
            return f"{prefix}/{path.name}"
        return path.name

    def _get_public_url(self, key: str) -> str:
        """Get public URL for an S3 object."""
        if self.config.public_url:
            return urljoin(self.config.public_url.rstrip("/") + "/", key)

        if self.config.provider == "r2":
            # R2 public URLs
            return f"https://{self.config.bucket}.r2.dev/{key}"

        # AWS S3 public URL
        if self.config.use_path_style:
            return f"https://s3.{self.config.region}.amazonaws.com/{self.config.bucket}/{key}"
        return f"https://{self.config.bucket}.s3.{self.config.region}.amazonaws.com/{key}"

    def _get_content_type(self, path: Path) -> str:
        """Get content type for a file."""
        if self.config.content_type:
            return self.config.content_type

        if path.suffix == ".whl":
            return "application/zip"
        elif path.suffix == ".gz":
            return "application/gzip"

        mime_type, _ = mimetypes.guess_type(str(path))
        return mime_type or "application/octet-stream"

    def _calculate_checksums(self, path: Path) -> dict[str, str]:
        """Calculate checksums for a file."""
        md5 = hashlib.md5()
        sha256 = hashlib.sha256()

        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5.update(chunk)
                sha256.update(chunk)

        return {
            "md5": md5.hexdigest(),
            "sha256": sha256.hexdigest(),
        }

    async def _generate_index(self, packages: dict[str, list[dict]]) -> None:
        """Generate PEP 503 simple index."""
        client = self._get_client()
        loop = asyncio.get_event_loop()
        index_prefix = self.config.index_prefix.strip("/")

        # Generate package index pages
        for pkg_name, files in packages.items():
            html = self._generate_package_index(pkg_name, files)
            key = f"{index_prefix}/{pkg_name}/index.html"

            await loop.run_in_executor(
                None,
                lambda: client.put_object(
                    Bucket=self.config.bucket,
                    Key=key,
                    Body=html.encode(),
                    ContentType="text/html",
                    ACL=self.config.acl,
                ),
            )

        # Generate root index
        root_html = self._generate_root_index(list(packages.keys()))
        root_key = f"{index_prefix}/index.html"

        await loop.run_in_executor(
            None,
            lambda: client.put_object(
                Bucket=self.config.bucket,
                Key=root_key,
                Body=root_html.encode(),
                ContentType="text/html",
                ACL=self.config.acl,
            ),
        )

    def _generate_package_index(self, pkg_name: str, files: list[dict]) -> str:
        """Generate PEP 503 package index page."""
        links = []
        for f in files:
            sha = f.get("sha256", "")
            if sha:
                links.append(f'<a href="{f["url"]}#sha256={sha}">{f["filename"]}</a>')
            else:
                links.append(f'<a href="{f["url"]}">{f["filename"]}</a>')

        return f"""<!DOCTYPE html>
<html>
<head><title>Links for {pkg_name}</title></head>
<body>
<h1>Links for {pkg_name}</h1>
{chr(10).join(links)}
</body>
</html>"""

    def _generate_root_index(self, package_names: list[str]) -> str:
        """Generate PEP 503 root index page."""
        links = [f'<a href="{name}/">{name}</a>' for name in sorted(package_names)]

        return f"""<!DOCTYPE html>
<html>
<head><title>Simple Index</title></head>
<body>
<h1>Simple Index</h1>
{chr(10).join(links)}
</body>
</html>"""


# Convenience function
async def publish_to_s3(
    files: list[Path],
    bucket: str,
    prefix: str = "",
    region: str = "us-east-1",
    skip_existing: bool = False,
    dry_run: bool = False,
    generate_index: bool = False,
) -> PublishResult:
    """
    Publish files to S3.

    Args:
        files: List of wheel/sdist files to publish
        bucket: S3 bucket name
        prefix: Key prefix for uploaded files
        region: AWS region
        skip_existing: Don't fail if file already exists
        dry_run: Validate without uploading
        generate_index: Generate PEP 503 simple index

    Returns:
        PublishResult with status and URLs

    Example:
        >>> result = await publish_to_s3(
        ...     files=[Path("dist/mypackage-1.0.0-py3-none-any.whl")],
        ...     bucket="my-wheels",
        ...     prefix="packages/",
        ... )
        >>> if result.success:
        ...     print(f"Published to: {result.urls[0]}")
    """
    s3_config = S3Config(
        bucket=bucket,
        prefix=prefix,
        region=region,
        generate_index=generate_index,
    )
    publisher = S3Publisher(s3_config)

    publish_config = PublishConfig(
        files=files,
        skip_existing=skip_existing,
        dry_run=dry_run,
    )

    return await publisher.publish(publish_config)
