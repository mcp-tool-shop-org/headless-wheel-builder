"""PyPI and compatible registry publisher."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from headless_wheel_builder.exceptions import PublishError
from headless_wheel_builder.publish.base import BasePublisher, PublishConfig, PublishResult

if TYPE_CHECKING:
    from pathlib import Path

# Well-known PyPI endpoints
PYPI_URL = "https://upload.pypi.org/legacy/"
TEST_PYPI_URL = "https://test.pypi.org/legacy/"


RepositoryType = Literal["pypi", "testpypi", "custom"]


@dataclass
class PyPIConfig:
    """Configuration for PyPI publishing."""

    # Repository selection
    repository: RepositoryType = "pypi"
    repository_url: str | None = None  # Override URL for custom registries

    # Authentication
    # Priority: token > username/password > keyring > environment
    token: str | None = None  # API token (preferred)
    username: str | None = None
    password: str | None = None

    # Trusted Publisher (OIDC) - for GitHub Actions
    # No credentials needed when running in GitHub Actions with OIDC configured
    use_trusted_publisher: bool = False

    # Attestations (PEP 740) - optional cryptographic signatures
    attestations: bool = False

    # TLS settings
    verify_ssl: bool = True
    ca_bundle: str | None = None

    # Retry settings
    max_retries: int = 3
    retry_delay: float = 1.0

    # Extra twine options
    extra_args: list[str] = field(default_factory=list)


class PyPIPublisher(BasePublisher):
    """
    Publisher for PyPI and compatible registries.

    Supports:
    - PyPI (production)
    - TestPyPI (testing)
    - Private PyPI servers (devpi, Artifactory, Nexus, etc.)
    - Trusted Publishers (OIDC) for keyless publishing from CI
    - API tokens (recommended)
    - Username/password authentication

    Example:
        >>> config = PyPIConfig(repository="testpypi", token=os.environ["PYPI_TOKEN"])
        >>> publisher = PyPIPublisher(config)
        >>> result = await publisher.publish(PublishConfig(files=[Path("dist/my_package-1.0.0-py3-none-any.whl")]))
    """

    def __init__(self, config: PyPIConfig | None = None) -> None:
        self.config = config or PyPIConfig()

    def _get_repository_url(self) -> str:
        """Get the repository URL based on config."""
        if self.config.repository_url:
            return self.config.repository_url

        if self.config.repository == "testpypi":
            return TEST_PYPI_URL
        elif self.config.repository == "pypi":
            return PYPI_URL
        else:
            raise PublishError("Custom repository requires repository_url to be set")

    def _get_credentials(self) -> tuple[str | None, str | None]:
        """Get credentials for authentication."""
        # Token authentication (preferred)
        if self.config.token:
            return "__token__", self.config.token

        # Username/password
        if self.config.username and self.config.password:
            return self.config.username, self.config.password

        # Environment variables
        token = os.environ.get("PYPI_TOKEN") or os.environ.get("TWINE_PASSWORD")
        if token:
            username = os.environ.get("TWINE_USERNAME", "__token__")
            return username, token

        # Try repository-specific env vars
        if self.config.repository == "testpypi":
            token = os.environ.get("TEST_PYPI_TOKEN")
            if token:
                return "__token__", token

        return None, None

    async def check_credentials(self) -> bool:
        """Check if credentials are available and valid."""
        # Trusted publisher doesn't need credentials
        if self.config.use_trusted_publisher:
            # Check if we're in GitHub Actions with OIDC
            return self._in_github_actions_with_oidc()

        username, password = self._get_credentials()
        return username is not None and password is not None

    def _in_github_actions_with_oidc(self) -> bool:
        """Check if running in GitHub Actions with OIDC configured."""
        return (
            os.environ.get("GITHUB_ACTIONS") == "true"
            and os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL") is not None
        )

    async def publish(self, config: PublishConfig) -> PublishResult:
        """
        Publish packages to PyPI or compatible registry.

        Uses twine for the actual upload to ensure compatibility
        with all PyPI features including attestations.
        """
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

        # Dry run - just validate (no credentials needed)
        if config.dry_run:
            for path in config.files:
                info = self._get_package_info(path)
                result.add_published(path)
                result.errors.append(
                    f"[DRY RUN] Would publish {info['name']} {info['version']} to {self._get_repository_url()}"
                )
            return result

        # Check credentials (only for actual upload)
        if not await self.check_credentials():
            return PublishResult.failure(
                "No credentials found. Set PYPI_TOKEN environment variable, "
                "use --token option, or configure Trusted Publishers for CI."
            )

        # Upload each file
        for path in config.files:
            try:
                url = await self._upload_file(path, config)
                result.add_published(path, url)
            except PublishError as e:
                if config.skip_existing and "already exists" in str(e).lower():
                    result.add_skipped(path, "Already exists")
                else:
                    result.add_failed(path, str(e))

        return result

    async def _upload_file(self, path: Path, config: PublishConfig) -> str:
        """Upload a single file using twine."""
        # Build twine command
        cmd = ["python", "-m", "twine", "upload"]

        # Repository URL
        repo_url = self._get_repository_url()
        cmd.extend(["--repository-url", repo_url])

        # Credentials
        username, password = self._get_credentials()
        if username and password:
            cmd.extend(["--username", username])
            cmd.extend(["--password", password])

        # Skip existing
        if config.skip_existing:
            cmd.append("--skip-existing")

        # Verbose
        if config.verbose:
            cmd.append("--verbose")

        # SSL settings
        if not self.config.verify_ssl:
            cmd.append("--disable-progress-bar")  # twine doesn't have --no-verify directly
        if self.config.ca_bundle:
            cmd.extend(["--cert", self.config.ca_bundle])

        # Attestations (PEP 740)
        if self.config.attestations:
            cmd.append("--attestations")

        # Extra args
        cmd.extend(self.config.extra_args)

        # File to upload
        cmd.append(str(path))

        # Run with retries
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env={**os.environ, "TWINE_NON_INTERACTIVE": "1"},
                )
                stdout, stderr = await process.communicate()

                if process.returncode == 0:
                    # Success - construct URL
                    info = self._get_package_info(path)
                    if self.config.repository == "pypi":
                        url = f"https://pypi.org/project/{info['name']}/{info['version']}/"
                    elif self.config.repository == "testpypi":
                        url = f"https://test.pypi.org/project/{info['name']}/{info['version']}/"
                    else:
                        url = repo_url
                    return url

                error_msg = stderr.decode() or stdout.decode()
                last_error = error_msg

                # Check for non-retryable errors
                if "already exists" in error_msg.lower():
                    raise PublishError(f"Package already exists: {error_msg}")
                if "invalid credentials" in error_msg.lower():
                    raise PublishError(f"Invalid credentials: {error_msg}")
                if "403" in error_msg:
                    raise PublishError(f"Permission denied: {error_msg}")

            except PublishError:
                raise
            except Exception as e:
                last_error = str(e)

            # Wait before retry
            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(self.config.retry_delay * (attempt + 1))

        raise PublishError(f"Upload failed after {self.config.max_retries} attempts: {last_error}")

    async def check_package_exists(self, name: str, version: str) -> bool:
        """Check if a package version already exists on the registry."""
        import urllib.error
        import urllib.request

        if self.config.repository == "pypi":
            url = f"https://pypi.org/pypi/{name}/{version}/json"
        elif self.config.repository == "testpypi":
            url = f"https://test.pypi.org/pypi/{name}/{version}/json"
        else:
            # Can't check custom registries easily
            return False

        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status == 200
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            raise PublishError(f"Failed to check package: {e}")
        except Exception as e:
            raise PublishError(f"Failed to check package: {e}")


# Convenience function
async def publish_to_pypi(
    files: list[Path],
    token: str | None = None,
    repository: RepositoryType = "pypi",
    skip_existing: bool = False,
    dry_run: bool = False,
) -> PublishResult:
    """
    Publish files to PyPI.

    Args:
        files: List of wheel/sdist files to publish
        token: PyPI API token (or set PYPI_TOKEN env var)
        repository: "pypi", "testpypi", or "custom"
        skip_existing: Don't fail if version already exists
        dry_run: Validate without uploading

    Returns:
        PublishResult with status and any errors

    Example:
        >>> result = await publish_to_pypi(
        ...     files=[Path("dist/mypackage-1.0.0-py3-none-any.whl")],
        ...     token=os.environ["PYPI_TOKEN"],
        ... )
        >>> if result.success:
        ...     print(f"Published to: {result.urls[0]}")
    """
    pypi_config = PyPIConfig(repository=repository, token=token)
    publisher = PyPIPublisher(pypi_config)

    publish_config = PublishConfig(
        files=files,
        skip_existing=skip_existing,
        dry_run=dry_run,
    )

    return await publisher.publish(publish_config)
