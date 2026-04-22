"""GitHub MCP Code Fetcher — fetches frontend source code from GitHub repos.

Uses GitHub REST API to retrieve file contents for LLM code context.
Supports file pattern filtering and session-level caching.
"""

import fnmatch
import logging
import re
from urllib.parse import urlparse

import httpx

from models.schemas import CodeContext

logger = logging.getLogger(__name__)

# Default file patterns to fetch when none are specified
DEFAULT_FILE_PATTERNS = [
    "src/components/**",
    "src/screens/**",
    "src/styles/**",
    "src/theme/**",
]

# GitHub API base URL
GITHUB_API_BASE = "https://api.github.com"

# Max total file size (bytes) to include in context to avoid oversized LLM prompts
MAX_TOTAL_CONTENT_BYTES = 500_000


def _parse_repo_url(repo_url: str) -> tuple[str, str]:
    """Extract owner and repo name from a GitHub URL.

    Supports:
      - https://github.com/owner/repo
      - https://github.com/owner/repo.git
      - https://github.com/owner/repo/tree/main/...

    Raises ValueError if the URL cannot be parsed.
    """
    parsed = urlparse(repo_url.strip())
    if parsed.hostname not in ("github.com", "www.github.com"):
        raise ValueError(f"Not a GitHub URL: {repo_url}")

    # Remove leading slash and split path segments
    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(path_parts) < 2:
        raise ValueError(f"Cannot extract owner/repo from URL: {repo_url}")

    owner = path_parts[0]
    repo = path_parts[1].removesuffix(".git")
    return owner, repo


def _matches_any_pattern(file_path: str, patterns: list[str]) -> bool:
    """Check if a file path matches any of the given glob-style patterns."""
    for pattern in patterns:
        # Support ** for recursive matching by converting to fnmatch-friendly form
        regex_pattern = pattern.replace("**", "DOUBLE_STAR").replace("*", "[^/]*").replace("DOUBLE_STAR", ".*")
        if re.fullmatch(regex_pattern, file_path):
            return True
        # Also try fnmatch for simple patterns
        if fnmatch.fnmatch(file_path, pattern):
            return True
    return False


class GitHubCodeFetcher:
    """Fetches frontend code from GitHub repos via GitHub REST API.

    Provides code context (component definitions, screen layouts, design tokens)
    to inform the Vision AI Extractor and manifest generation.
    """

    def __init__(self, github_token: str | None = None):
        self._token = github_token
        self._cache: dict[str, CodeContext] = {}
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def fetch(
        self,
        repo_url: str,
        file_patterns: list[str] | None = None,
    ) -> CodeContext:
        """Fetch relevant frontend source code from a GitHub repo.

        Args:
            repo_url: GitHub repository URL.
            file_patterns: Optional glob patterns (e.g. ``['src/components/**']``).
                           Defaults to common frontend paths.

        Returns:
            A ``CodeContext`` populated with component definitions, screen
            layouts, design tokens, and raw file contents.  On any error
            (network, auth, invalid URL) an *empty* ``CodeContext`` is
            returned so the pipeline can proceed with screenshot-only
            extraction.
        """
        cache_key = self._cache_key(repo_url, file_patterns)
        if cache_key in self._cache:
            logger.info("Returning cached CodeContext for %s", repo_url)
            return self._cache[cache_key]

        try:
            owner, repo = _parse_repo_url(repo_url)
        except ValueError as exc:
            logger.warning("Invalid GitHub URL '%s': %s", repo_url, exc)
            return self._empty_context(repo_url)

        patterns = file_patterns or DEFAULT_FILE_PATTERNS

        try:
            source_files = await self._fetch_repo_files(owner, repo, patterns)
        except Exception as exc:
            logger.warning(
                "Failed to fetch repo %s/%s: %s", owner, repo, exc
            )
            empty = self._empty_context(repo_url)
            self._cache[cache_key] = empty
            return empty

        context = self._build_context(repo_url, source_files)
        self._cache[cache_key] = context
        return context

    def clear_cache(self) -> None:
        """Clear the session cache (call when a new authoring session starts)."""
        self._cache.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _cache_key(self, repo_url: str, patterns: list[str] | None) -> str:
        """Produce a deterministic cache key."""
        normalized = repo_url.strip().rstrip("/").removesuffix(".git")
        pat_key = ",".join(sorted(patterns)) if patterns else "default"
        return f"{normalized}|{pat_key}"

    def _empty_context(self, repo_url: str) -> CodeContext:
        """Return an empty CodeContext so the pipeline can continue."""
        return CodeContext(
            components=[],
            screen_layouts=[],
            design_tokens={},
            repo_url=repo_url,
            fetched_files=[],
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazily create an httpx async client with auth headers."""
        if self._client is None or self._client.is_closed:
            headers: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"
            self._client = httpx.AsyncClient(
                base_url=GITHUB_API_BASE,
                headers=headers,
                timeout=30.0,
            )
        return self._client

    async def _fetch_repo_files(
        self, owner: str, repo: str, patterns: list[str]
    ) -> list[dict[str, str]]:
        """Fetch the repo tree, filter by patterns, then download file contents."""
        client = await self._get_client()

        # 1. Get the full recursive tree from the default branch
        tree_resp = await client.get(
            f"/repos/{owner}/{repo}/git/trees/HEAD",
            params={"recursive": "1"},
        )
        tree_resp.raise_for_status()
        tree_data = tree_resp.json()

        # 2. Filter to blobs matching the requested patterns
        matching_paths: list[str] = []
        for item in tree_data.get("tree", []):
            if item.get("type") != "blob":
                continue
            if _matches_any_pattern(item["path"], patterns):
                matching_paths.append(item["path"])

        if not matching_paths:
            logger.info("No files matched patterns %s in %s/%s", patterns, owner, repo)
            return []

        # 3. Download file contents (respect size budget)
        source_files: list[dict[str, str]] = []
        total_bytes = 0
        for path in matching_paths:
            if total_bytes >= MAX_TOTAL_CONTENT_BYTES:
                logger.info(
                    "Reached content size limit (%d bytes); skipping remaining files",
                    MAX_TOTAL_CONTENT_BYTES,
                )
                break
            try:
                content = await self._fetch_file_content(client, owner, repo, path)
                total_bytes += len(content.encode("utf-8"))
                source_files.append({"path": path, "content": content})
            except Exception as exc:
                logger.warning("Failed to fetch file %s: %s", path, exc)

        return source_files

    async def _fetch_file_content(
        self, client: httpx.AsyncClient, owner: str, repo: str, path: str
    ) -> str:
        """Download a single file's raw content from GitHub."""
        resp = await client.get(
            f"/repos/{owner}/{repo}/contents/{path}",
            headers={"Accept": "application/vnd.github.v3.raw"},
        )
        resp.raise_for_status()
        return resp.text

    def _build_context(
        self, repo_url: str, source_files: list[dict[str, str]]
    ) -> CodeContext:
        """Build a CodeContext from fetched source files."""
        components = self._extract_components(source_files)
        screen_layouts = self._extract_screen_layouts(source_files)
        design_tokens = self._extract_design_tokens(source_files)

        return CodeContext(
            components=components,
            screen_layouts=screen_layouts,
            design_tokens=design_tokens,
            repo_url=repo_url,
            fetched_files=[f["path"] for f in source_files],
        )

    # ------------------------------------------------------------------
    # Code analysis helpers
    # ------------------------------------------------------------------

    def _extract_components(
        self, source_files: list[dict[str, str]]
    ) -> list[dict]:
        """Parse fetched source to extract component definitions."""
        components: list[dict] = []
        component_pattern = re.compile(
            r"(?:export\s+(?:default\s+)?)?(?:function|const)\s+(\w+)",
            re.MULTILINE,
        )
        for f in source_files:
            path = f["path"]
            if not any(
                seg in path for seg in ("component", "Component", "widget", "Widget")
            ):
                continue
            for match in component_pattern.finditer(f["content"]):
                name = match.group(1)
                # Heuristic: component names start with uppercase
                if name[0].isupper():
                    components.append(
                        {"name": name, "file": path, "snippet": f["content"][:500]}
                    )
        return components

    def _extract_screen_layouts(
        self, source_files: list[dict[str, str]]
    ) -> list[dict]:
        """Extract screen layout information from source files."""
        layouts: list[dict] = []
        for f in source_files:
            path = f["path"]
            if not any(
                seg in path for seg in ("screen", "Screen", "page", "Page", "view", "View")
            ):
                continue
            layouts.append({"file": path, "snippet": f["content"][:500]})
        return layouts

    def _extract_design_tokens(
        self, source_files: list[dict[str, str]]
    ) -> dict:
        """Extract design system tokens (colors, spacing, typography)."""
        tokens: dict = {"colors": {}, "spacing": {}, "typography": {}}
        for f in source_files:
            path = f["path"]
            if not any(
                seg in path
                for seg in ("theme", "Theme", "token", "Token", "style", "Style", "design")
            ):
                continue
            # Include the raw content for the LLM to interpret
            tokens.setdefault("raw_files", []).append(
                {"file": path, "snippet": f["content"][:1000]}
            )
        return tokens

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
