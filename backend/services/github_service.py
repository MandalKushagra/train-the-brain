"""GitHub Service — fetches code from a GitHub repo URL.

Used when PM provides a GitHub link instead of pasting code directly.
Fetches the repo tree and concatenates relevant source files.
"""
import os
import httpx

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
RELEVANT_EXTENSIONS = {".kt", ".java", ".py", ".js", ".ts", ".tsx", ".jsx", ".xml", ".swift"}
MAX_FILE_SIZE = 100_000  # skip files larger than 100KB


def fetch_repo_code(repo_url: str) -> str:
    """Fetch concatenated source code from a GitHub repo URL.

    Accepts URLs like:
      https://github.com/owner/repo
      https://github.com/owner/repo/tree/main/src/some/path

    Returns concatenated source code as a single string.
    """
    owner, repo, path = _parse_github_url(repo_url)
    if not owner or not repo:
        return f"[Could not parse GitHub URL: {repo_url}]"

    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    try:
        # Get the repo tree recursively
        api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"
        resp = httpx.get(api_url, headers=headers, timeout=30)
        resp.raise_for_status()
        tree = resp.json().get("tree", [])

        # Filter to relevant source files under the specified path
        source_files = []
        for item in tree:
            if item["type"] != "blob":
                continue
            file_path = item["path"]
            if path and not file_path.startswith(path):
                continue
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in RELEVANT_EXTENSIONS:
                continue
            if item.get("size", 0) > MAX_FILE_SIZE:
                continue
            source_files.append(file_path)

        # Fetch each file's content
        parts = []
        for file_path in source_files[:30]:  # cap at 30 files to avoid token explosion
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{file_path}"
            file_resp = httpx.get(raw_url, headers=headers, timeout=15)
            if file_resp.status_code == 200:
                parts.append(f"// === {file_path} ===\n{file_resp.text}")

        if not parts:
            return "[No relevant source files found in repository]"

        return "\n\n".join(parts)

    except Exception as e:
        return f"[GitHub fetch error: {e}]"


def _parse_github_url(url: str) -> tuple[str, str, str]:
    """Parse owner, repo, and optional path from a GitHub URL."""
    url = url.strip().rstrip("/")
    # Remove protocol
    for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
        if url.startswith(prefix):
            url = url[len(prefix):]
            break

    parts = url.split("/")
    if len(parts) < 2:
        return "", "", ""

    owner = parts[0]
    repo = parts[1]
    path = ""

    # Handle /tree/branch/path format
    if len(parts) > 3 and parts[2] == "tree":
        # parts[3] is branch, rest is path
        path = "/".join(parts[4:]) if len(parts) > 4 else ""

    return owner, repo, path
