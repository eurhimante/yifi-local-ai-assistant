"""Read-only GitHub release metadata from the public GitHub API."""
import re
import httpx

_REPO_PART = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")

GITHUB_RELEASE_TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "github_latest_release",
        "description": (
            "Fetch the latest published stable GitHub release directly from the official "
            "GitHub REST API, including tag, publication date and exact release URL. "
            "For questions asking about a project's latest stable release, use this "
            "instead of relying on web search snippets."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "GitHub repository owner, for example ollama"},
                "repo": {"type": "string", "description": "GitHub repository name, for example ollama"},
            },
            "required": ["owner", "repo"],
            "additionalProperties": False,
        },
    },
}


async def github_latest_release(arguments):
    if not isinstance(arguments, dict) or set(arguments) != {"owner", "repo"}:
        return {"error": "Expected exactly owner and repo"}
    owner, repo = arguments["owner"], arguments["repo"]
    if not all(isinstance(v, str) and _REPO_PART.fullmatch(v) for v in (owner, repo)):
        return {"error": "Invalid GitHub repository identifier"}

    # Fixed HTTPS host and endpoint. No user-specified URL or redirect destination.
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=False, trust_env=False) as client:
            response = await client.get(
                url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "YIFI-local-assistant",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            if response.status_code == 404:
                return {"error": "Repository not found or no published stable release", "api_url": url}
            response.raise_for_status()
            data = response.json()

        if not isinstance(data, dict) or data.get("draft") or data.get("prerelease"):
            return {"error": "API did not return a published stable release"}
        html_url = data.get("html_url")
        expected_prefix = f"https://github.com/{owner}/{repo}/releases/tag/"
        # github.com may normalize owner or repository capitalization.
        if not isinstance(html_url, str) or not html_url.lower().startswith(expected_prefix.lower()):
            return {"error": "Unexpected release URL returned by GitHub"}
        return {
            "verified_by": "GitHub REST API (releases/latest)",
            "repository": f"{owner}/{repo}",
            "tag": data.get("tag_name"),
            "name": data.get("name"),
            "published_at": data.get("published_at"),
            "url": html_url,
            "api_url": url,
            "note": "Latest release per GitHub API; this does not check third-party distribution channels.",
        }
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        return {"error": f"GitHub API request failed: {type(exc).__name__}"}
