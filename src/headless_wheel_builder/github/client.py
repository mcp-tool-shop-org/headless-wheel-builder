"""Async GitHub API client."""

from __future__ import annotations

import asyncio
import mimetypes
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

from headless_wheel_builder.exceptions import GitHubAuthError, GitHubError, GitHubRateLimitError

from .models import (
    GitHubConfig,
    Issue,
    PullRequest,
    Release,
    ReleaseAsset,
    ReleaseResult,
    Repository,
    WorkflowRun,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


class GitHubClient:
    """Async GitHub API client.

    Provides a high-level interface for GitHub operations with:
    - Automatic token resolution from environment
    - Exponential backoff retry for rate limits
    - Proper error handling and typed responses

    Example:
        >>> async with GitHubClient() as client:
        ...     release = await client.create_release(
        ...         repo="owner/repo",
        ...         tag="v1.0.0",
        ...         name="Release v1.0.0",
        ...     )
        ...     print(release.html_url)
    """

    def __init__(self, config: GitHubConfig | None = None) -> None:
        """Initialize the client.

        Args:
            config: GitHub configuration. If not provided, uses defaults
                    with token from GITHUB_TOKEN environment variable.
        """
        self.config = config or GitHubConfig()
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> GitHubClient:
        """Enter async context."""
        await self._ensure_client()
        return self

    async def __aexit__(self, *args: object) -> None:
        """Exit async context."""
        await self.close()

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure HTTP client is initialized."""
        if self._client is None:
            headers = {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            if self.config.token:
                headers["Authorization"] = f"Bearer {self.config.token}"

            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers=headers,
                timeout=self.config.timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        content: bytes | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Make an API request with retry logic.

        Args:
            method: HTTP method
            endpoint: API endpoint (relative to base URL)
            json: JSON body
            params: Query parameters
            headers: Additional headers
            content: Raw content for uploads

        Returns:
            Parsed JSON response

        Raises:
            GitHubAuthError: Authentication failed
            GitHubRateLimitError: Rate limit exceeded
            GitHubError: Other API errors
        """
        client = await self._ensure_client()
        last_error: Exception | None = None

        for attempt in range(self.config.max_retries + 1):
            try:
                response = await client.request(
                    method,
                    endpoint,
                    json=json,
                    params=params,
                    headers=headers,
                    content=content,
                )

                # Handle rate limiting
                if response.status_code == 403:
                    remaining = response.headers.get("x-ratelimit-remaining", "0")
                    if remaining == "0":
                        reset_time = int(response.headers.get("x-ratelimit-reset", "0"))
                        raise GitHubRateLimitError(
                            "GitHub API rate limit exceeded",
                            reset_timestamp=reset_time,
                        )

                # Handle auth errors
                if response.status_code == 401:
                    raise GitHubAuthError("GitHub authentication failed. Check your token.")

                # Handle not found
                if response.status_code == 404:
                    raise GitHubError(f"Resource not found: {endpoint}", status_code=404)

                # Handle other errors
                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        message = error_data.get("message", response.text)
                    except Exception:
                        message = response.text
                    raise GitHubError(message, status_code=response.status_code)

                # Success - return JSON or empty dict for 204
                if response.status_code == 204:
                    return {}

                return response.json()

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_error = e
                if attempt < self.config.max_retries:
                    delay = self.config.retry_delay * (2**attempt)
                    await asyncio.sleep(delay)
                continue

            except GitHubRateLimitError:
                raise

            except GitHubError:
                raise

        raise GitHubError(f"Request failed after {self.config.max_retries} retries: {last_error}")

    # =========================================================================
    # Repository Operations
    # =========================================================================

    async def get_repo(self, repo: str | Repository) -> Repository:
        """Get repository information.

        Args:
            repo: Repository in 'owner/repo' format or Repository object

        Returns:
            Repository information
        """
        if isinstance(repo, Repository):
            repo = repo.full_name

        data = await self._request("GET", f"/repos/{repo}")
        return Repository.from_api(data)  # type: ignore[arg-type]

    async def detect_repo(self, path: Path | str = ".") -> Repository | None:
        """Detect repository from git remote.

        Args:
            path: Path to git repository

        Returns:
            Repository if detected, None otherwise
        """
        import re

        path = Path(path)

        try:
            process = await asyncio.create_subprocess_exec(
                "git",
                "-C",
                str(path),
                "remote",
                "get-url",
                "origin",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            if process.returncode != 0:
                return None

            url = stdout.decode().strip()

            # Parse GitHub URL patterns
            # https://github.com/owner/repo.git
            # git@github.com:owner/repo.git
            patterns = [
                r"github\.com[:/]([^/]+)/([^/\s]+?)(?:\.git)?$",
                r"github\.com[:/]([^/]+)/([^/\s]+)$",
            ]

            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return Repository(
                        owner=match.group(1),
                        name=match.group(2),
                        full_name=f"{match.group(1)}/{match.group(2)}",
                    )

            return None

        except Exception:
            return None

    # =========================================================================
    # Release Operations
    # =========================================================================

    async def get_release(self, repo: str, tag: str) -> Release | None:
        """Get a release by tag.

        Args:
            repo: Repository in 'owner/repo' format
            tag: Tag name

        Returns:
            Release if found, None otherwise
        """
        try:
            data = await self._request("GET", f"/repos/{repo}/releases/tags/{tag}")
            return Release.from_api(data)  # type: ignore[arg-type]
        except GitHubError as e:
            if e.status_code == 404:
                return None
            raise

    async def get_latest_release(self, repo: str) -> Release | None:
        """Get the latest release.

        Args:
            repo: Repository in 'owner/repo' format

        Returns:
            Latest release if found, None otherwise
        """
        try:
            data = await self._request("GET", f"/repos/{repo}/releases/latest")
            return Release.from_api(data)  # type: ignore[arg-type]
        except GitHubError as e:
            if e.status_code == 404:
                return None
            raise

    async def list_releases(
        self,
        repo: str,
        per_page: int = 30,
        page: int = 1,
    ) -> list[Release]:
        """List releases for a repository.

        Args:
            repo: Repository in 'owner/repo' format
            per_page: Results per page (max 100)
            page: Page number

        Returns:
            List of releases
        """
        data = await self._request(
            "GET",
            f"/repos/{repo}/releases",
            params={"per_page": per_page, "page": page},
        )
        return [Release.from_api(r) for r in data]  # type: ignore[union-attr]

    async def create_release(
        self,
        repo: str,
        tag: str,
        *,
        name: str | None = None,
        body: str | None = None,
        draft: bool = False,
        prerelease: bool = False,
        target_commitish: str | None = None,
        generate_release_notes: bool = False,
    ) -> Release:
        """Create a new release.

        Args:
            repo: Repository in 'owner/repo' format
            tag: Tag name for the release
            name: Release title (defaults to tag name)
            body: Release description/notes
            draft: Create as draft release
            prerelease: Mark as prerelease
            target_commitish: Branch or commit SHA to tag
            generate_release_notes: Auto-generate release notes

        Returns:
            Created release
        """
        payload: dict[str, Any] = {
            "tag_name": tag,
            "name": name or tag,
            "draft": draft,
            "prerelease": prerelease,
            "generate_release_notes": generate_release_notes,
        }

        if body:
            payload["body"] = body
        if target_commitish:
            payload["target_commitish"] = target_commitish

        data = await self._request("POST", f"/repos/{repo}/releases", json=payload)
        return Release.from_api(data)  # type: ignore[arg-type]

    async def update_release(
        self,
        repo: str,
        release_id: int,
        *,
        tag: str | None = None,
        name: str | None = None,
        body: str | None = None,
        draft: bool | None = None,
        prerelease: bool | None = None,
    ) -> Release:
        """Update an existing release.

        Args:
            repo: Repository in 'owner/repo' format
            release_id: Release ID
            tag: New tag name
            name: New release title
            body: New release description
            draft: Update draft status
            prerelease: Update prerelease status

        Returns:
            Updated release
        """
        payload: dict[str, Any] = {}
        if tag is not None:
            payload["tag_name"] = tag
        if name is not None:
            payload["name"] = name
        if body is not None:
            payload["body"] = body
        if draft is not None:
            payload["draft"] = draft
        if prerelease is not None:
            payload["prerelease"] = prerelease

        data = await self._request(
            "PATCH",
            f"/repos/{repo}/releases/{release_id}",
            json=payload,
        )
        return Release.from_api(data)  # type: ignore[arg-type]

    async def delete_release(self, repo: str, release_id: int) -> None:
        """Delete a release.

        Args:
            repo: Repository in 'owner/repo' format
            release_id: Release ID
        """
        await self._request("DELETE", f"/repos/{repo}/releases/{release_id}")

    # =========================================================================
    # Asset Operations
    # =========================================================================

    async def upload_asset(
        self,
        upload_url: str,
        file_path: Path,
        *,
        name: str | None = None,
        label: str | None = None,
    ) -> ReleaseAsset:
        """Upload an asset to a release.

        Args:
            upload_url: Upload URL from release (contains {?name,label})
            file_path: Path to file to upload
            name: Asset name (defaults to filename)
            label: Asset label/description

        Returns:
            Uploaded asset information
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise GitHubError(f"File not found: {file_path}")

        # Parse upload URL - remove the {?name,label} template
        base_url = upload_url.split("{")[0]

        # Determine content type
        content_type, _ = mimetypes.guess_type(str(file_path))
        if content_type is None:
            content_type = "application/octet-stream"

        # Read file content
        content = file_path.read_bytes()

        # Build params
        params: dict[str, str] = {"name": name or file_path.name}
        if label:
            params["label"] = label

        # Upload using direct httpx call (different host than API)
        client = await self._ensure_client()

        headers = {
            "Content-Type": content_type,
            "Accept": "application/vnd.github+json",
        }
        if self.config.token:
            headers["Authorization"] = f"Bearer {self.config.token}"

        response = await client.post(
            base_url,
            params=params,
            content=content,
            headers=headers,
        )

        if response.status_code >= 400:
            try:
                error_msg = response.json().get("message", response.text)
            except Exception:
                error_msg = response.text
            raise GitHubError(f"Asset upload failed: {error_msg}", status_code=response.status_code)

        return ReleaseAsset.from_api(response.json())

    async def upload_assets(
        self,
        upload_url: str,
        files: Sequence[Path | str],
        *,
        parallel: bool = True,
    ) -> ReleaseResult:
        """Upload multiple assets to a release.

        Args:
            upload_url: Upload URL from release
            files: Paths to files to upload
            parallel: Upload files in parallel (default: True)

        Returns:
            ReleaseResult with upload status
        """
        result = ReleaseResult(success=True)
        file_paths = [Path(f) for f in files]

        if parallel:
            # Upload in parallel
            tasks = [self.upload_asset(upload_url, fp) for fp in file_paths]
            outcomes = await asyncio.gather(*tasks, return_exceptions=True)

            for fp, outcome in zip(file_paths, outcomes, strict=False):
                if isinstance(outcome, BaseException):
                    result.add_failed(fp, str(outcome))
                    result.success = False
                else:
                    # outcome is ReleaseAsset after BaseException check
                    result.add_uploaded(outcome)
        else:
            # Upload sequentially
            for fp in file_paths:
                try:
                    asset = await self.upload_asset(upload_url, fp)
                    result.add_uploaded(asset)
                except Exception as e:
                    result.add_failed(fp, str(e))
                    result.success = False

        return result

    async def delete_asset(self, repo: str, asset_id: int) -> None:
        """Delete a release asset.

        Args:
            repo: Repository in 'owner/repo' format
            asset_id: Asset ID
        """
        await self._request("DELETE", f"/repos/{repo}/releases/assets/{asset_id}")

    # =========================================================================
    # High-Level Release Operations
    # =========================================================================

    async def create_release_with_assets(
        self,
        repo: str,
        tag: str,
        assets: Sequence[Path | str],
        *,
        name: str | None = None,
        body: str | None = None,
        draft: bool = False,
        prerelease: bool = False,
        target_commitish: str | None = None,
        generate_release_notes: bool = False,
    ) -> ReleaseResult:
        """Create a release and upload assets in one operation.

        Args:
            repo: Repository in 'owner/repo' format
            tag: Tag name
            assets: Paths to files to upload as release assets
            name: Release title
            body: Release description
            draft: Create as draft
            prerelease: Mark as prerelease
            target_commitish: Branch or commit to tag
            generate_release_notes: Auto-generate notes

        Returns:
            ReleaseResult with release and asset upload status
        """
        # Create the release
        try:
            release = await self.create_release(
                repo=repo,
                tag=tag,
                name=name,
                body=body,
                draft=draft,
                prerelease=prerelease,
                target_commitish=target_commitish,
                generate_release_notes=generate_release_notes,
            )
        except GitHubError as e:
            return ReleaseResult.failure(f"Failed to create release: {e}")

        result = ReleaseResult(success=True, release=release)

        # Upload assets if provided
        if assets:
            upload_result = await self.upload_assets(release.upload_url, assets)
            result.assets_uploaded = upload_result.assets_uploaded
            result.assets_failed = upload_result.assets_failed
            result.errors = upload_result.errors
            result.success = upload_result.success

        return result

    # =========================================================================
    # Pull Request Operations
    # =========================================================================

    async def create_pull_request(
        self,
        repo: str,
        *,
        title: str,
        head: str,
        base: str,
        body: str | None = None,
        draft: bool = False,
    ) -> PullRequest:
        """Create a pull request.

        Args:
            repo: Repository in 'owner/repo' format
            title: PR title
            head: Branch containing changes
            base: Branch to merge into
            body: PR description
            draft: Create as draft PR

        Returns:
            Created pull request
        """
        payload: dict[str, Any] = {
            "title": title,
            "head": head,
            "base": base,
            "draft": draft,
        }
        if body:
            payload["body"] = body

        data = await self._request("POST", f"/repos/{repo}/pulls", json=payload)
        return PullRequest.from_api(data)  # type: ignore[arg-type]

    async def get_pull_request(self, repo: str, number: int) -> PullRequest:
        """Get a pull request by number.

        Args:
            repo: Repository in 'owner/repo' format
            number: PR number

        Returns:
            Pull request
        """
        data = await self._request("GET", f"/repos/{repo}/pulls/{number}")
        return PullRequest.from_api(data)  # type: ignore[arg-type]

    async def list_pull_requests(
        self,
        repo: str,
        *,
        state: str = "open",
        per_page: int = 30,
        page: int = 1,
    ) -> list[PullRequest]:
        """List pull requests.

        Args:
            repo: Repository in 'owner/repo' format
            state: Filter by state (open, closed, all)
            per_page: Results per page
            page: Page number

        Returns:
            List of pull requests
        """
        data = await self._request(
            "GET",
            f"/repos/{repo}/pulls",
            params={"state": state, "per_page": per_page, "page": page},
        )
        return [PullRequest.from_api(pr) for pr in data]  # type: ignore[union-attr]

    # =========================================================================
    # Issue Operations
    # =========================================================================

    async def create_issue(
        self,
        repo: str,
        *,
        title: str,
        body: str | None = None,
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
    ) -> Issue:
        """Create an issue.

        Args:
            repo: Repository in 'owner/repo' format
            title: Issue title
            body: Issue description
            labels: Labels to apply
            assignees: Users to assign

        Returns:
            Created issue
        """
        payload: dict[str, Any] = {"title": title}
        if body:
            payload["body"] = body
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees

        data = await self._request("POST", f"/repos/{repo}/issues", json=payload)
        return Issue.from_api(data)  # type: ignore[arg-type]

    async def get_issue(self, repo: str, number: int) -> Issue:
        """Get an issue by number.

        Args:
            repo: Repository in 'owner/repo' format
            number: Issue number

        Returns:
            Issue
        """
        data = await self._request("GET", f"/repos/{repo}/issues/{number}")
        return Issue.from_api(data)  # type: ignore[arg-type]

    async def list_issues(
        self,
        repo: str,
        *,
        state: str = "open",
        per_page: int = 30,
        page: int = 1,
    ) -> list[Issue]:
        """List issues for a repository.

        Args:
            repo: Repository in 'owner/repo' format
            state: Filter by state (open, closed, all)
            per_page: Results per page (max 100)
            page: Page number

        Returns:
            List of issues
        """
        data = await self._request(
            "GET",
            f"/repos/{repo}/issues",
            params={"state": state, "per_page": per_page, "page": page},
        )
        return [Issue.from_api(i) for i in data]  # type: ignore[union-attr]

    # =========================================================================
    # Workflow Operations
    # =========================================================================

    async def trigger_workflow(
        self,
        repo: str,
        workflow: str | int,
        *,
        ref: str = "main",
        inputs: dict[str, str] | None = None,
    ) -> None:
        """Trigger a workflow dispatch event.

        Args:
            repo: Repository in 'owner/repo' format
            workflow: Workflow filename or ID
            ref: Branch or tag to run on
            inputs: Workflow inputs
        """
        payload: dict[str, Any] = {"ref": ref}
        if inputs:
            payload["inputs"] = inputs

        await self._request(
            "POST",
            f"/repos/{repo}/actions/workflows/{workflow}/dispatches",
            json=payload,
        )

    async def get_workflow_run(self, repo: str, run_id: int) -> WorkflowRun:
        """Get a workflow run by ID.

        Args:
            repo: Repository in 'owner/repo' format
            run_id: Workflow run ID

        Returns:
            Workflow run
        """
        data = await self._request("GET", f"/repos/{repo}/actions/runs/{run_id}")
        return WorkflowRun.from_api(data)  # type: ignore[arg-type]

    async def list_workflow_runs(
        self,
        repo: str,
        *,
        workflow: str | int | None = None,
        branch: str | None = None,
        status: str | None = None,
        per_page: int = 30,
        page: int = 1,
    ) -> list[WorkflowRun]:
        """List workflow runs.

        Args:
            repo: Repository in 'owner/repo' format
            workflow: Filter by workflow filename or ID
            branch: Filter by branch
            status: Filter by status
            per_page: Results per page
            page: Page number

        Returns:
            List of workflow runs
        """
        if workflow:
            endpoint = f"/repos/{repo}/actions/workflows/{workflow}/runs"
        else:
            endpoint = f"/repos/{repo}/actions/runs"

        params: dict[str, Any] = {"per_page": per_page, "page": page}
        if branch:
            params["branch"] = branch
        if status:
            params["status"] = status

        data = await self._request("GET", endpoint, params=params)
        return [WorkflowRun.from_api(r) for r in data.get("workflow_runs", [])]  # type: ignore[union-attr]

    # =========================================================================
    # Utility Methods
    # =========================================================================

    async def check_credentials(self) -> bool:
        """Check if current credentials are valid.

        Returns:
            True if authenticated, False otherwise
        """
        try:
            await self._request("GET", "/user")
            return True
        except GitHubAuthError:
            return False
        except GitHubError:
            return False
