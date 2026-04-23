"""Unit tests for GitHubCodeFetcher.

Tests use mocked HTTP responses to verify CodeContext structure,
caching, file pattern filtering, and error handling.
"""

from unittest.mock import AsyncMock, patch, MagicMock

import httpx
import pytest

from agents.github_code_fetcher import (
    GitHubCodeFetcher,
    _parse_repo_url,
    _matches_any_pattern,
)


# ── Unit Tests: Helper Functions ──────────────────────────────


class TestParseRepoUrl:
    def test_standard_url(self):
        owner, repo = _parse_repo_url("https://github.com/acme/frontend")
        assert owner == "acme"
        assert repo == "frontend"

    def test_url_with_git_suffix(self):
        owner, repo = _parse_repo_url("https://github.com/acme/frontend.git")
        assert owner == "acme"
        assert repo == "frontend"

    def test_url_with_tree_path(self):
        owner, repo = _parse_repo_url(
            "https://github.com/acme/frontend/tree/main/src"
        )
        assert owner == "acme"
        assert repo == "frontend"

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError):
            _parse_repo_url("https://gitlab.com/acme/repo")

    def test_incomplete_url_raises(self):
        with pytest.raises(ValueError):
            _parse_repo_url("https://github.com/acme")


class TestMatchesAnyPattern:
    def test_matches_component_pattern(self):
        assert _matches_any_pattern(
            "src/components/Button.tsx", ["src/components/**"]
        )

    def test_matches_screen_pattern(self):
        assert _matches_any_pattern(
            "src/screens/LoginScreen.tsx", ["src/screens/**"]
        )

    def test_no_match(self):
        assert not _matches_any_pattern(
            "src/utils/helpers.ts", ["src/components/**", "src/screens/**"]
        )


# ── Integration Tests: GitHubCodeFetcher ─────────────────────


class TestGitHubCodeFetcher:
    @pytest.mark.asyncio
    async def test_fetch_returns_code_context(self):
        """Mock the GitHub API and verify CodeContext structure."""
        fetcher = GitHubCodeFetcher(github_token="test-token")

        # Mock the tree response
        tree_response = MagicMock()
        tree_response.json.return_value = {
            "tree": [
                {"path": "src/components/Button.tsx", "type": "blob"},
                {"path": "src/components/Input.tsx", "type": "blob"},
                {"path": "src/utils/helpers.ts", "type": "blob"},
                {"path": "src/screens/LoginScreen.tsx", "type": "blob"},
            ]
        }
        tree_response.raise_for_status = MagicMock()

        # Mock file content responses
        file_response = MagicMock()
        file_response.text = "export const Button = () => <button>Click</button>;"
        file_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[tree_response, file_response, file_response])
        mock_client.is_closed = False

        fetcher._client = mock_client

        context = await fetcher.fetch(
            "https://github.com/acme/frontend",
            file_patterns=["src/components/**"],
        )

        assert context.repo_url == "https://github.com/acme/frontend"
        assert len(context.fetched_files) == 2  # Button.tsx and Input.tsx
        assert "src/components/Button.tsx" in context.fetched_files
        assert "src/components/Input.tsx" in context.fetched_files

    @pytest.mark.asyncio
    async def test_fetch_returns_empty_context_on_invalid_url(self):
        """Invalid GitHub URL should return empty context."""
        fetcher = GitHubCodeFetcher()
        context = await fetcher.fetch("https://gitlab.com/acme/repo")

        assert context.components == []
        assert context.fetched_files == []
        assert context.repo_url == "https://gitlab.com/acme/repo"

    @pytest.mark.asyncio
    async def test_fetch_returns_empty_context_on_network_error(self):
        """Network errors should return empty context, not raise."""
        fetcher = GitHubCodeFetcher()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        mock_client.is_closed = False
        fetcher._client = mock_client

        context = await fetcher.fetch("https://github.com/acme/frontend")

        assert context.components == []
        assert context.fetched_files == []

    @pytest.mark.asyncio
    async def test_caching_returns_same_context(self):
        """Second fetch with same URL should return cached result."""
        fetcher = GitHubCodeFetcher()

        # Pre-populate cache
        from models.schemas import CodeContext

        cached = CodeContext(
            components=[{"name": "CachedButton"}],
            screen_layouts=[],
            design_tokens={},
            repo_url="https://github.com/acme/frontend",
            fetched_files=["src/components/CachedButton.tsx"],
        )
        cache_key = fetcher._cache_key(
            "https://github.com/acme/frontend", None
        )
        fetcher._cache[cache_key] = cached

        context = await fetcher.fetch("https://github.com/acme/frontend")
        assert context.components == [{"name": "CachedButton"}]

    @pytest.mark.asyncio
    async def test_clear_cache(self):
        """clear_cache should empty the cache."""
        fetcher = GitHubCodeFetcher()
        fetcher._cache["key"] = MagicMock()
        fetcher.clear_cache()
        assert len(fetcher._cache) == 0
