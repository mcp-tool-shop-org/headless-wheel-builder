"""Tests for GitHub module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from headless_wheel_builder.exceptions import (
    GitHubAuthError,
    GitHubError,
    GitHubRateLimitError,
)
from headless_wheel_builder.github.client import GitHubClient
from headless_wheel_builder.github.models import (
    GitHubConfig,
    Issue,
    PullRequest,
    Release,
    ReleaseAsset,
    ReleaseResult,
    Repository,
    WorkflowRun,
)


class TestGitHubConfig:
    """Tests for GitHubConfig."""

    def test_default_config(self):
        """Test default configuration."""
        with patch.dict("os.environ", {}, clear=True):
            config = GitHubConfig()
            assert config.token is None
            assert config.base_url == "https://api.github.com"
            assert config.timeout == 30.0
            assert config.max_retries == 3

    def test_token_from_env_github_token(self):
        """Test token resolution from GITHUB_TOKEN."""
        with patch.dict("os.environ", {"GITHUB_TOKEN": "ghp_test123"}):
            config = GitHubConfig()
            assert config.token == "ghp_test123"

    def test_token_from_env_gh_token(self):
        """Test token resolution from GH_TOKEN."""
        with patch.dict("os.environ", {"GH_TOKEN": "ghp_test456"}, clear=True):
            config = GitHubConfig()
            assert config.token == "ghp_test456"

    def test_explicit_token_overrides_env(self):
        """Test explicit token overrides environment."""
        with patch.dict("os.environ", {"GITHUB_TOKEN": "env_token"}):
            config = GitHubConfig(token="explicit_token")
            assert config.token == "explicit_token"

    def test_base_url_normalization(self):
        """Test base URL trailing slash removal."""
        config = GitHubConfig(base_url="https://github.example.com/api/")
        assert config.base_url == "https://github.example.com/api"


class TestRepository:
    """Tests for Repository model."""

    def test_parse_valid_repo(self):
        """Test parsing valid owner/repo string."""
        repo = Repository.parse("owner/repo")
        assert repo.owner == "owner"
        assert repo.name == "repo"
        assert repo.full_name == "owner/repo"

    def test_parse_with_dashes(self):
        """Test parsing repo with dashes."""
        repo = Repository.parse("my-org/my-repo")
        assert repo.owner == "my-org"
        assert repo.name == "my-repo"

    def test_parse_invalid_no_slash(self):
        """Test parsing invalid repo without slash."""
        with pytest.raises(ValueError, match="Invalid repository format"):
            Repository.parse("invalid")

    def test_parse_invalid_empty_parts(self):
        """Test parsing invalid repo with empty parts."""
        with pytest.raises(ValueError, match="Invalid repository format"):
            Repository.parse("/repo")
        with pytest.raises(ValueError, match="Invalid repository format"):
            Repository.parse("owner/")

    def test_from_api(self):
        """Test creating from API response."""
        data = {
            "owner": {"login": "octocat"},
            "name": "hello-world",
            "full_name": "octocat/hello-world",
            "description": "My first repository",
            "private": False,
            "default_branch": "main",
            "html_url": "https://github.com/octocat/hello-world",
            "clone_url": "https://github.com/octocat/hello-world.git",
            "ssh_url": "git@github.com:octocat/hello-world.git",
        }
        repo = Repository.from_api(data)
        assert repo.owner == "octocat"
        assert repo.name == "hello-world"
        assert repo.description == "My first repository"
        assert repo.private is False


class TestRelease:
    """Tests for Release model."""

    def test_from_api(self):
        """Test creating release from API response."""
        data = {
            "id": 123,
            "tag_name": "v1.0.0",
            "name": "Version 1.0.0",
            "body": "Release notes",
            "draft": False,
            "prerelease": False,
            "html_url": "https://github.com/owner/repo/releases/tag/v1.0.0",
            "upload_url": "https://uploads.github.com/repos/owner/repo/releases/123/assets{?name,label}",
            "tarball_url": "https://github.com/owner/repo/tarball/v1.0.0",
            "created_at": "2024-01-15T10:00:00Z",
            "published_at": "2024-01-15T10:05:00Z",
            "assets": [],
            "target_commitish": "main",
        }
        release = Release.from_api(data)
        assert release.id == 123
        assert release.tag_name == "v1.0.0"
        assert release.name == "Version 1.0.0"
        assert release.draft is False
        assert release.prerelease is False
        assert release.created_at is not None

    def test_from_api_with_assets(self):
        """Test release with assets."""
        data = {
            "id": 123,
            "tag_name": "v1.0.0",
            "name": "Release",
            "body": None,
            "draft": True,
            "prerelease": True,
            "html_url": "https://github.com/owner/repo/releases/tag/v1.0.0",
            "upload_url": "https://uploads.github.com/...",
            "assets": [
                {
                    "id": 1,
                    "name": "package-1.0.0.whl",
                    "label": "Python wheel",
                    "content_type": "application/octet-stream",
                    "size": 12345,
                    "url": "https://api.github.com/...",
                    "browser_download_url": "https://github.com/...",
                    "state": "uploaded",
                    "download_count": 100,
                }
            ],
        }
        release = Release.from_api(data)
        assert release.draft is True
        assert release.prerelease is True
        assert len(release.assets) == 1
        assert release.assets[0].name == "package-1.0.0.whl"
        assert release.assets[0].download_count == 100


class TestReleaseResult:
    """Tests for ReleaseResult."""

    def test_failure_creation(self):
        """Test creating failure result."""
        result = ReleaseResult.failure("Something went wrong")
        assert result.success is False
        assert "Something went wrong" in result.errors

    def test_add_uploaded(self):
        """Test adding uploaded asset."""
        result = ReleaseResult(success=True)
        asset = ReleaseAsset(
            id=1,
            name="test.whl",
            label=None,
            content_type="application/octet-stream",
            size=1000,
            download_url="",
            browser_download_url="",
        )
        result.add_uploaded(asset)
        assert len(result.assets_uploaded) == 1
        assert result.assets_uploaded[0].name == "test.whl"

    def test_add_failed(self):
        """Test adding failed asset."""
        result = ReleaseResult(success=True)
        result.add_failed(Path("test.whl"), "Upload failed")
        assert len(result.assets_failed) == 1
        assert "test.whl" in str(result.assets_failed[0][0])
        assert "Upload failed" in result.errors[0]


class TestPullRequest:
    """Tests for PullRequest model."""

    def test_from_api(self):
        """Test creating PR from API response."""
        data = {
            "number": 42,
            "title": "Add new feature",
            "body": "Description here",
            "state": "open",
            "draft": False,
            "html_url": "https://github.com/owner/repo/pull/42",
            "head": {"ref": "feature-branch"},
            "base": {"ref": "main"},
            "merged": False,
            "mergeable": True,
            "labels": [{"name": "enhancement"}, {"name": "needs-review"}],
        }
        pr = PullRequest.from_api(data)
        assert pr.number == 42
        assert pr.title == "Add new feature"
        assert pr.head_ref == "feature-branch"
        assert pr.base_ref == "main"
        assert "enhancement" in pr.labels


class TestIssue:
    """Tests for Issue model."""

    def test_from_api(self):
        """Test creating issue from API response."""
        data = {
            "number": 10,
            "title": "Bug report",
            "body": "Details",
            "state": "open",
            "html_url": "https://github.com/owner/repo/issues/10",
            "labels": [{"name": "bug"}],
            "assignees": [{"login": "user1"}],
        }
        issue = Issue.from_api(data)
        assert issue.number == 10
        assert issue.title == "Bug report"
        assert "bug" in issue.labels
        assert "user1" in issue.assignees


class TestWorkflowRun:
    """Tests for WorkflowRun model."""

    def test_from_api(self):
        """Test creating workflow run from API response."""
        data = {
            "id": 12345,
            "name": "CI",
            "workflow_id": 100,
            "head_branch": "main",
            "head_sha": "abc123",
            "status": "completed",
            "conclusion": "success",
            "html_url": "https://github.com/owner/repo/actions/runs/12345",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:05:00Z",
        }
        run = WorkflowRun.from_api(data)
        assert run.id == 12345
        assert run.name == "CI"
        assert run.status == "completed"
        assert run.conclusion == "success"


class TestGitHubClient:
    """Tests for GitHubClient."""

    @pytest.fixture
    def client(self):
        """Create a client with test config."""
        config = GitHubConfig(token="test_token")
        return GitHubClient(config)

    @pytest.fixture
    def mock_response(self):
        """Create a mock httpx response factory."""

        def _create(
            status_code: int = 200,
            json_data: dict | list | None = None,
            headers: dict | None = None,
        ):
            response = MagicMock(spec=httpx.Response)
            response.status_code = status_code
            response.headers = headers or {}
            response.text = json.dumps(json_data) if json_data else ""
            response.json.return_value = json_data
            return response

        return _create

    @pytest.mark.asyncio
    async def test_context_manager(self, client):
        """Test async context manager."""
        async with client:
            assert client._client is not None
        assert client._client is None

    @pytest.mark.asyncio
    async def test_check_credentials_valid(self, client, mock_response):
        """Test credential check with valid token."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"login": "user"}
            result = await client.check_credentials()
            assert result is True
            mock_req.assert_called_once_with("GET", "/user")

    @pytest.mark.asyncio
    async def test_check_credentials_invalid(self, client):
        """Test credential check with invalid token."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = GitHubAuthError()
            result = await client.check_credentials()
            assert result is False

    @pytest.mark.asyncio
    async def test_get_repo(self, client):
        """Test getting repository info."""
        repo_data = {
            "owner": {"login": "owner"},
            "name": "repo",
            "full_name": "owner/repo",
            "private": False,
            "default_branch": "main",
        }
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = repo_data
            repo = await client.get_repo("owner/repo")
            assert repo.full_name == "owner/repo"
            mock_req.assert_called_once_with("GET", "/repos/owner/repo")

    @pytest.mark.asyncio
    async def test_create_release(self, client):
        """Test creating a release."""
        release_data = {
            "id": 1,
            "tag_name": "v1.0.0",
            "name": "Version 1.0.0",
            "body": "Notes",
            "draft": False,
            "prerelease": False,
            "html_url": "https://github.com/owner/repo/releases/tag/v1.0.0",
            "upload_url": "https://uploads.github.com/...",
            "assets": [],
        }
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = release_data
            release = await client.create_release(
                repo="owner/repo",
                tag="v1.0.0",
                name="Version 1.0.0",
                body="Notes",
            )
            assert release.tag_name == "v1.0.0"
            assert release.name == "Version 1.0.0"

    @pytest.mark.asyncio
    async def test_get_release_not_found(self, client):
        """Test getting non-existent release returns None."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = GitHubError("Not found", status_code=404)
            release = await client.get_release("owner/repo", "v999.0.0")
            assert release is None

    @pytest.mark.asyncio
    async def test_list_releases(self, client):
        """Test listing releases."""
        releases_data = [
            {
                "id": 1,
                "tag_name": "v1.0.0",
                "name": "v1.0.0",
                "body": None,
                "draft": False,
                "prerelease": False,
                "html_url": "",
                "upload_url": "",
                "assets": [],
            },
            {
                "id": 2,
                "tag_name": "v0.9.0",
                "name": "v0.9.0",
                "body": None,
                "draft": False,
                "prerelease": False,
                "html_url": "",
                "upload_url": "",
                "assets": [],
            },
        ]
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = releases_data
            releases = await client.list_releases("owner/repo")
            assert len(releases) == 2
            assert releases[0].tag_name == "v1.0.0"

    @pytest.mark.asyncio
    async def test_create_pull_request(self, client):
        """Test creating a pull request."""
        pr_data = {
            "number": 42,
            "title": "New feature",
            "body": "Description",
            "state": "open",
            "draft": False,
            "html_url": "https://github.com/owner/repo/pull/42",
            "head": {"ref": "feature"},
            "base": {"ref": "main"},
            "labels": [],
        }
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = pr_data
            pr = await client.create_pull_request(
                repo="owner/repo",
                title="New feature",
                head="feature",
                base="main",
            )
            assert pr.number == 42

    @pytest.mark.asyncio
    async def test_create_issue(self, client):
        """Test creating an issue."""
        issue_data = {
            "number": 10,
            "title": "Bug",
            "body": "Details",
            "state": "open",
            "html_url": "https://github.com/owner/repo/issues/10",
            "labels": [{"name": "bug"}],
            "assignees": [],
        }
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = issue_data
            issue = await client.create_issue(
                repo="owner/repo",
                title="Bug",
                body="Details",
                labels=["bug"],
            )
            assert issue.number == 10
            assert "bug" in issue.labels

    @pytest.mark.asyncio
    async def test_trigger_workflow(self, client):
        """Test triggering a workflow."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {}
            await client.trigger_workflow(
                repo="owner/repo",
                workflow="build.yml",
                ref="main",
                inputs={"version": "1.0.0"},
            )
            mock_req.assert_called_once()
            call_args = mock_req.call_args
            assert call_args[0] == (
                "POST",
                "/repos/owner/repo/actions/workflows/build.yml/dispatches",
            )
            assert call_args[1]["json"]["ref"] == "main"
            assert call_args[1]["json"]["inputs"]["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_detect_repo_https(self, client):
        """Test detecting repo from HTTPS remote."""
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(
                return_value=(b"https://github.com/owner/repo.git\n", b"")
            )
            mock_exec.return_value = mock_process

            repo = await client.detect_repo()
            assert repo is not None
            assert repo.owner == "owner"
            assert repo.name == "repo"

    @pytest.mark.asyncio
    async def test_detect_repo_ssh(self, client):
        """Test detecting repo from SSH remote."""
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.communicate = AsyncMock(
                return_value=(b"git@github.com:owner/repo.git\n", b"")
            )
            mock_exec.return_value = mock_process

            repo = await client.detect_repo()
            assert repo is not None
            assert repo.owner == "owner"
            assert repo.name == "repo"

    @pytest.mark.asyncio
    async def test_detect_repo_not_git(self, client):
        """Test detecting repo in non-git directory."""
        with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
            mock_process = MagicMock()
            mock_process.returncode = 128  # Not a git repo
            mock_process.communicate = AsyncMock(return_value=(b"", b"fatal: not a git repository"))
            mock_exec.return_value = mock_process

            repo = await client.detect_repo()
            assert repo is None


class TestGitHubClientErrors:
    """Tests for error handling in GitHubClient."""

    @pytest.fixture
    def client(self):
        """Create a client with test config."""
        config = GitHubConfig(token="test_token")
        return GitHubClient(config)

    @pytest.mark.asyncio
    async def test_auth_error(self, client):
        """Test 401 raises GitHubAuthError."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401
        mock_response.headers = {}
        mock_response.text = "Unauthorized"

        with patch.object(client, "_ensure_client", new_callable=AsyncMock) as mock_client:
            mock_http_client = MagicMock()
            mock_http_client.request = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_http_client

            with pytest.raises(GitHubAuthError):
                await client._request("GET", "/user")

    @pytest.mark.asyncio
    async def test_rate_limit_error(self, client):
        """Test rate limit error handling."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403
        mock_response.headers = {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1700000000"}
        mock_response.text = "Rate limit exceeded"

        with patch.object(client, "_ensure_client", new_callable=AsyncMock) as mock_client:
            mock_http_client = MagicMock()
            mock_http_client.request = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_http_client

            with pytest.raises(GitHubRateLimitError) as exc_info:
                await client._request("GET", "/repos/owner/repo")

            assert exc_info.value.reset_timestamp == 1700000000

    @pytest.mark.asyncio
    async def test_not_found_error(self, client):
        """Test 404 raises GitHubError with status code."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 404
        mock_response.headers = {}
        mock_response.text = "Not found"

        with patch.object(client, "_ensure_client", new_callable=AsyncMock) as mock_client:
            mock_http_client = MagicMock()
            mock_http_client.request = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_http_client

            with pytest.raises(GitHubError) as exc_info:
                await client._request("GET", "/repos/owner/nonexistent")

            assert exc_info.value.status_code == 404


class TestGitHubClientAssetUpload:
    """Tests for asset upload functionality."""

    @pytest.fixture
    def client(self):
        """Create a client with test config."""
        config = GitHubConfig(token="test_token")
        return GitHubClient(config)

    @pytest.mark.asyncio
    async def test_upload_asset_file_not_found(self, client):
        """Test upload with non-existent file."""
        with pytest.raises(GitHubError, match="File not found"):
            await client.upload_asset(
                "https://uploads.github.com/...",
                Path("/nonexistent/file.whl"),
            )

    @pytest.mark.asyncio
    async def test_upload_assets_parallel(self, client, tmp_path):
        """Test parallel asset upload."""
        # Create test files
        file1 = tmp_path / "test1.whl"
        file2 = tmp_path / "test2.whl"
        file1.write_bytes(b"content1")
        file2.write_bytes(b"content2")

        with patch.object(client, "upload_asset", new_callable=AsyncMock) as mock_upload:
            asset1 = ReleaseAsset(
                id=1,
                name="test1.whl",
                label=None,
                content_type="application/octet-stream",
                size=8,
                download_url="",
                browser_download_url="",
            )
            asset2 = ReleaseAsset(
                id=2,
                name="test2.whl",
                label=None,
                content_type="application/octet-stream",
                size=8,
                download_url="",
                browser_download_url="",
            )
            mock_upload.side_effect = [asset1, asset2]

            result = await client.upload_assets(
                "https://uploads.github.com/...",
                [file1, file2],
                parallel=True,
            )

            assert result.success
            assert len(result.assets_uploaded) == 2

    @pytest.mark.asyncio
    async def test_upload_assets_with_failure(self, client, tmp_path):
        """Test asset upload with partial failure."""
        file1 = tmp_path / "test1.whl"
        file2 = tmp_path / "test2.whl"
        file1.write_bytes(b"content1")
        file2.write_bytes(b"content2")

        with patch.object(client, "upload_asset", new_callable=AsyncMock) as mock_upload:
            asset1 = ReleaseAsset(
                id=1,
                name="test1.whl",
                label=None,
                content_type="application/octet-stream",
                size=8,
                download_url="",
                browser_download_url="",
            )
            mock_upload.side_effect = [asset1, Exception("Upload failed")]

            result = await client.upload_assets(
                "https://uploads.github.com/...",
                [file1, file2],
                parallel=True,
            )

            assert result.success is False
            assert len(result.assets_uploaded) == 1
            assert len(result.assets_failed) == 1


class TestCreateReleaseWithAssets:
    """Tests for create_release_with_assets."""

    @pytest.fixture
    def client(self):
        """Create a client with test config."""
        config = GitHubConfig(token="test_token")
        return GitHubClient(config)

    @pytest.mark.asyncio
    async def test_create_release_with_assets_success(self, client, tmp_path):
        """Test creating release with assets."""
        wheel_file = tmp_path / "pkg-1.0.0.whl"
        wheel_file.write_bytes(b"wheel content")

        release = Release(
            id=1,
            tag_name="v1.0.0",
            name="v1.0.0",
            body=None,
            draft=False,
            prerelease=False,
            html_url="https://github.com/owner/repo/releases/tag/v1.0.0",
            upload_url="https://uploads.github.com/...",
        )

        asset = ReleaseAsset(
            id=1,
            name="pkg-1.0.0.whl",
            label=None,
            content_type="application/octet-stream",
            size=13,
            download_url="",
            browser_download_url="",
        )

        upload_result = ReleaseResult(success=True)
        upload_result.add_uploaded(asset)

        with (
            patch.object(client, "create_release", new_callable=AsyncMock) as mock_create,
            patch.object(client, "upload_assets", new_callable=AsyncMock) as mock_upload,
        ):
            mock_create.return_value = release
            mock_upload.return_value = upload_result

            result = await client.create_release_with_assets(
                repo="owner/repo",
                tag="v1.0.0",
                assets=[wheel_file],
            )

            assert result.success
            assert result.release is not None
            assert result.release.tag_name == "v1.0.0"
            assert len(result.assets_uploaded) == 1

    @pytest.mark.asyncio
    async def test_create_release_failure(self, client):
        """Test release creation failure."""
        with patch.object(client, "create_release", new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = GitHubError("Failed to create release")

            result = await client.create_release_with_assets(
                repo="owner/repo",
                tag="v1.0.0",
                assets=[],
            )

            assert result.success is False
            assert "Failed to create release" in result.errors[0]
