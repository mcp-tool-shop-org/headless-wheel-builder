"""Wheel registry client for private package hosting."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx

from headless_wheel_builder.cache.models import CacheEntry, RegistryConfig

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class RegistryEntry:
    """Entry in a wheel registry.

    Attributes:
        package: Package name
        version: Package version
        wheel_name: Wheel filename
        sha256: SHA256 hash
        url: Download URL
        size_bytes: Size in bytes
        requires_python: Python version requirement
        metadata: Additional metadata
    """

    package: str
    version: str
    wheel_name: str
    sha256: str
    url: str
    size_bytes: int = 0
    requires_python: str = ""
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "package": self.package,
            "version": self.version,
            "wheel_name": self.wheel_name,
            "sha256": self.sha256,
            "url": self.url,
            "size_bytes": self.size_bytes,
            "requires_python": self.requires_python,
            "metadata": self.metadata or {},
        }


class WheelRegistry:
    """Client for wheel registry (PEP 503 compatible).

    Supports private registries for hosting internal wheels.
    """

    def __init__(self, config: RegistryConfig) -> None:
        """Initialize registry client.

        Args:
            config: Registry configuration
        """
        self.config = config
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            auth = None
            if self.config.username and self.config.password:
                auth = (self.config.username, self.config.password)

            self._client = httpx.AsyncClient(
                auth=auth,
                verify=self.config.verify_ssl,
                timeout=self.config.timeout,
            )

        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def list_packages(self) -> list[str]:
        """List all packages in registry.

        Returns:
            List of package names
        """
        client = await self._get_client()
        url = f"{self.config.url.rstrip('/')}/simple/"

        response = await client.get(url, headers={"Accept": "application/json"})
        response.raise_for_status()

        # Try JSON API (PEP 691)
        if "application/json" in response.headers.get("content-type", ""):
            data = response.json()
            return [p["name"] for p in data.get("projects", [])]

        # Fall back to HTML parsing
        content = response.text
        packages: list[str] = []
        # Simple HTML parsing for <a href="package/">package</a>
        import re

        for match in re.finditer(r'<a[^>]+href="([^"]+)/"[^>]*>([^<]+)</a>', content):
            packages.append(match.group(2))

        return packages

    async def list_versions(self, package: str) -> list[RegistryEntry]:
        """List all versions of a package.

        Args:
            package: Package name

        Returns:
            List of registry entries
        """
        client = await self._get_client()
        # Normalize package name (PEP 503)
        normalized = package.lower().replace("_", "-")
        url = f"{self.config.url.rstrip('/')}/simple/{normalized}/"

        response = await client.get(url, headers={"Accept": "application/json"})
        response.raise_for_status()

        entries: list[RegistryEntry] = []

        # Try JSON API (PEP 691)
        if "application/json" in response.headers.get("content-type", ""):
            data = response.json()
            for file in data.get("files", []):
                if not file.get("filename", "").endswith(".whl"):
                    continue

                # Parse version from filename
                parts = file["filename"].split("-")
                version = parts[1] if len(parts) > 1 else ""

                entries.append(
                    RegistryEntry(
                        package=package,
                        version=version,
                        wheel_name=file["filename"],
                        sha256=file.get("hashes", {}).get("sha256", ""),
                        url=file.get("url", ""),
                        size_bytes=file.get("size", 0),
                        requires_python=file.get("requires-python", ""),
                    )
                )

            return entries

        # Fall back to HTML parsing
        content = response.text
        import re

        for match in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>([^<]+\.whl)</a>', content):
            href = match.group(1)
            filename = match.group(2)

            # Extract hash from URL fragment
            sha256 = ""
            if "#sha256=" in href:
                sha256 = href.split("#sha256=")[1]

            # Parse version from filename
            parts = filename.split("-")
            version = parts[1] if len(parts) > 1 else ""

            # Build full URL
            file_url = href if href.startswith("http") else f"{url}{href}"

            entries.append(
                RegistryEntry(
                    package=package,
                    version=version,
                    wheel_name=filename,
                    sha256=sha256,
                    url=file_url.split("#")[0],
                )
            )

        return entries

    async def download(
        self,
        entry: RegistryEntry,
        destination: Path,
        verify_hash: bool = True,
    ) -> Path:
        """Download a wheel from the registry.

        Args:
            entry: Registry entry to download
            destination: Destination directory
            verify_hash: Whether to verify SHA256 hash

        Returns:
            Path to downloaded wheel

        Raises:
            ValueError: If hash verification fails
        """
        client = await self._get_client()
        dest_path = destination / entry.wheel_name

        # Download file
        async with client.stream("GET", entry.url) as response:
            response.raise_for_status()

            with open(dest_path, "wb") as f:
                async for chunk in response.aiter_bytes():
                    f.write(chunk)

        # Verify hash
        if verify_hash and entry.sha256:
            sha256 = hashlib.sha256()
            with open(dest_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)

            if sha256.hexdigest() != entry.sha256:
                dest_path.unlink()
                raise ValueError(
                    f"Hash mismatch for {entry.wheel_name}: "
                    f"expected {entry.sha256}, got {sha256.hexdigest()}"
                )

        return dest_path

    async def upload(
        self,
        wheel_path: Path,
        package: str,
        version: str,
    ) -> RegistryEntry:
        """Upload a wheel to the registry.

        Args:
            wheel_path: Path to wheel file
            package: Package name
            version: Package version

        Returns:
            Registry entry for uploaded wheel

        Note:
            This assumes the registry supports wheel upload.
            The exact API depends on the registry implementation.
        """
        client = await self._get_client()

        # Calculate hash
        sha256 = hashlib.sha256()
        with open(wheel_path, "rb") as f:
            content = f.read()
            sha256.update(content)

        hash_value = sha256.hexdigest()
        size_bytes = wheel_path.stat().st_size

        # Upload - this is a simplified implementation
        # Real registries may have different APIs
        normalized = package.lower().replace("_", "-")
        upload_url = f"{self.config.url.rstrip('/')}/upload/{normalized}/{version}/"

        files = {"file": (wheel_path.name, content, "application/zip")}
        data = {
            "sha256": hash_value,
            "package": package,
            "version": version,
        }

        response = await client.post(upload_url, files=files, data=data)
        response.raise_for_status()

        return RegistryEntry(
            package=package,
            version=version,
            wheel_name=wheel_path.name,
            sha256=hash_value,
            url=f"{self.config.url.rstrip('/')}/simple/{normalized}/{wheel_path.name}",
            size_bytes=size_bytes,
        )

    async def check_exists(self, package: str, version: str) -> bool:
        """Check if a package version exists in the registry.

        Args:
            package: Package name
            version: Package version

        Returns:
            True if version exists
        """
        try:
            entries = await self.list_versions(package)
            return any(e.version == version for e in entries)
        except httpx.HTTPStatusError:
            return False

    def to_cache_entry(
        self,
        registry_entry: RegistryEntry,
        wheel_path: Path,
    ) -> CacheEntry:
        """Convert registry entry to cache entry.

        Args:
            registry_entry: Registry entry
            wheel_path: Path to downloaded wheel

        Returns:
            Cache entry
        """
        return CacheEntry(
            package=registry_entry.package,
            version=registry_entry.version,
            wheel_name=registry_entry.wheel_name,
            sha256=registry_entry.sha256,
            size_bytes=wheel_path.stat().st_size,
            source="registry",
            metadata={"registry_url": self.config.url},
        )
