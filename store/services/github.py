"""GitHub integration service for plugin downloads."""

import re
from dataclasses import dataclass
from typing import Any

import httpx
import structlog

from store.core.config import settings

logger = structlog.get_logger(__name__)


@dataclass
class GitHubRepoInfo:
    """GitHub repository information."""

    owner: str
    repo: str
    full_name: str
    description: str | None
    html_url: str
    default_branch: str
    stargazers_count: int
    forks_count: int
    language: str | None
    topics: list[str]


class GitHubService:
    """Service for interacting with GitHub API."""

    def __init__(self, token: str | None = None):
        self.token = token or settings.github_token
        self.base_url = settings.github_api_base
        self._client = httpx.Client(
            timeout=30.0,
            headers={"Authorization": f"Bearer {self.token}"} if self.token else {},
        )

    def parse_github_url(self, url: str) -> tuple[str, str] | None:
        """Parse GitHub repository URL to extract owner and repo."""
        patterns = [
            r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$",
            r"github\.com[:/]([^/]+)/([^/]+?)/tree/[^/]+",
            r"github\.com[:/]([^/]+)/([^/]+?)/blob/[^/]+",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                owner = match.group(1)
                repo = match.group(2).replace(".git", "")
                return owner, repo

        return None

    def get_repo_info(self, owner: str, repo: str) -> GitHubRepoInfo | None:
        """Get repository information from GitHub."""
        try:
            response = self._client.get(f"{self.base_url}/repos/{owner}/{repo}")
            response.raise_for_status()
            data = response.json()

            return GitHubRepoInfo(
                owner=data["owner"]["login"],
                repo=data["name"],
                full_name=data["full_name"],
                description=data.get("description"),
                html_url=data.get("html_url"),
                default_branch=data.get("default_branch", "main"),
                stargazers_count=data.get("stargazers_count", 0),
                forks_count=data.get("forks_count", 0),
                language=data.get("language"),
                topics=data.get("topics", []),
            )
        except httpx.HTTPError as e:
            logger.error("Failed to get repo info", owner=owner, repo=repo, error=str(e))
            return None
        except Exception as e:
            logger.error("Unexpected error getting repo info", owner=owner, repo=repo, error=str(e))
            return None

    def get_download_url(
        self, owner: str, repo: str, branch: str | None = None, ref: str | None = None
    ) -> str:
        """Get ZIP download URL for repository."""
        if ref:
            return f"https://github.com/{owner}/{repo}/archive/{ref}.zip"
        elif branch:
            return f"https://github.com/{owner}/{repo}/archive/{branch}.zip"
        else:
            return f"https://github.com/{owner}/{repo}/archive/main.zip"

    def download_repo(
        self, owner: str, repo: str, branch: str = "main", dest_path: str | None = None
    ) -> bytes | None:
        """Download repository as ZIP."""
        try:
            zip_url = self.get_download_url(owner, repo, branch)
            response = self._client.get(zip_url, follow_redirects=True)
            response.raise_for_status()

            if dest_path:
                from pathlib import Path

                Path(dest_path).write_bytes(response.content)
                return None

            return response.content

        except httpx.HTTPError as e:
            logger.error(
                "Failed to download repo", owner=owner, repo=repo, branch=branch, error=str(e)
            )
            return None
        except Exception as e:
            logger.error(
                "Unexpected error downloading repo", owner=owner, repo=repo, error=str(e)
            )
            return None

    def list_releases(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """List repository releases."""
        try:
            response = self._client.get(
                f"{self.base_url}/repos/{owner}/{repo}/releases"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to list releases", owner=owner, repo=repo, error=str(e))
            return []

    def get_latest_release(self, owner: str, repo: str) -> dict[str, Any] | None:
        """Get latest release information."""
        try:
            response = self._client.get(
                f"{self.base_url}/repos/{owner}/{repo}/releases/latest"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to get latest release", owner=owner, repo=repo, error=str(e))
            return None

    def search_repositories(
        self, query: str, language: str | None = None, topics: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Search for repositories."""
        search_query = query
        if language:
            search_query += f" language:{language}"
        if topics:
            for topic in topics:
                search_query += f" topic:{topic}"

        try:
            response = self._client.get(
                f"{self.base_url}/search/repositories",
                params={"q": search_query, "per_page": 30},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])
        except Exception as e:
            logger.error("Failed to search repositories", query=query, error=str(e))
            return []


# Singleton instance
github_service = GitHubService()
