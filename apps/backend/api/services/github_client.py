#!/usr/bin/env python3
"""
GitHub API Client for MagnetarCode

Provides integration with GitHub for:
- Repository operations
- Pull request creation and management
- Issue management
- Code review automation

Protected by circuit breaker to prevent cascading failures.
"""

import logging
import sys
from pathlib import Path
from typing import Any

import httpx

# Import circuit breaker and retry
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.constants import CACHE_TTL_SHORT
from services.cache_service import get_cache
from utils.circuit_breaker import get_circuit_breaker
from utils.retry import retry

logger = logging.getLogger(__name__)
cache = get_cache()

# Initialize circuit breaker for GitHub API
github_circuit_breaker = get_circuit_breaker(
    name="github",
    failure_threshold=5,  # Open after 5 failures
    success_threshold=2,  # Close after 2 successes
    timeout=60,  # Try recovery after 60 seconds
    expected_exception=Exception,
)


class GitHubClient:
    """Client for GitHub REST API v3"""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str | None = None):
        """
        Initialize GitHub client

        Args:
            token: GitHub personal access token (required for authenticated requests)
        """
        self.token = token
        self.timeout = httpx.Timeout(30.0, connect=10.0)

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with authentication"""
        headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "MagnetarCode/1.0"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        """
        Make an authenticated request to GitHub API

        Protected by circuit breaker to prevent cascading failures.
        """

        @retry(
            max_attempts=3,
            initial_delay=2.0,
            retry_on=(httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError),
        )
        @github_circuit_breaker.call()
        async def _make_request():
            url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self._get_headers(),
                    json=json_data,
                    params=params,
                )

                if response.status_code >= 400:
                    error_msg = response.json().get("message", "Unknown error")
                    raise Exception(f"GitHub API error: {error_msg}")

                return response.json() if response.content else {}

        return await _make_request()

    # ===== Repository Operations =====

    async def get_repo(self, owner: str, repo: str) -> dict[str, Any]:
        """Get repository information (cached)"""
        cache_key = f"github:repo:{owner}:{repo}"
        cached = await cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for repo: {owner}/{repo}")
            return cached

        result = await self._request("GET", f"/repos/{owner}/{repo}")
        await cache.set(cache_key, result, ttl=CACHE_TTL_SHORT)
        return result

    async def list_branches(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """List repository branches (cached)"""
        cache_key = f"github:branches:{owner}:{repo}"
        cached = await cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for branches: {owner}/{repo}")
            return cached

        result = await self._request("GET", f"/repos/{owner}/{repo}/branches")
        await cache.set(cache_key, result, ttl=CACHE_TTL_SHORT)
        return result

    async def get_file_content(
        self, owner: str, repo: str, path: str, ref: str | None = None
    ) -> dict[str, Any]:
        """Get file content from repository (cached)"""
        ref_str = ref or "default"
        cache_key = f"github:file:{owner}:{repo}:{path}:{ref_str}"
        cached = await cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for file: {owner}/{repo}/{path}")
            return cached

        params = {"ref": ref} if ref else {}
        result = await self._request("GET", f"/repos/{owner}/{repo}/contents/{path}", params=params)
        await cache.set(cache_key, result, ttl=CACHE_TTL_SHORT)
        return result

    # ===== Pull Request Operations =====

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str = "main",
        body: str | None = None,
        draft: bool = False,
    ) -> dict[str, Any]:
        """
        Create a new pull request

        Args:
            owner: Repository owner
            repo: Repository name
            title: PR title
            head: Branch containing changes
            base: Base branch (default: main)
            body: PR description
            draft: Create as draft PR

        Returns:
            Created PR data
        """
        data = {"title": title, "head": head, "base": base, "draft": draft}
        if body:
            data["body"] = body

        return await self._request("POST", f"/repos/{owner}/{repo}/pulls", json_data=data)

    async def list_pull_requests(
        self, owner: str, repo: str, state: str = "open"
    ) -> list[dict[str, Any]]:
        """
        List pull requests

        Args:
            owner: Repository owner
            repo: Repository name
            state: PR state (open, closed, all)

        Returns:
            List of PRs
        """
        return await self._request("GET", f"/repos/{owner}/{repo}/pulls", params={"state": state})

    async def get_pull_request(self, owner: str, repo: str, pr_number: int) -> dict[str, Any]:
        """Get pull request details (cached)"""
        cache_key = f"github:pr:{owner}:{repo}:{pr_number}"
        cached = await cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for PR: {owner}/{repo}#{pr_number}")
            return cached

        result = await self._request("GET", f"/repos/{owner}/{repo}/pulls/{pr_number}")
        await cache.set(cache_key, result, ttl=CACHE_TTL_SHORT)
        return result

    async def update_pull_request(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
    ) -> dict[str, Any]:
        """
        Update a pull request

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
            title: New title
            body: New description
            state: New state (open, closed)

        Returns:
            Updated PR data
        """
        data = {}
        if title:
            data["title"] = title
        if body:
            data["body"] = body
        if state:
            data["state"] = state

        return await self._request(
            "PATCH", f"/repos/{owner}/{repo}/pulls/{pr_number}", json_data=data
        )

    async def merge_pull_request(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_title: str | None = None,
        commit_message: str | None = None,
        merge_method: str = "merge",
    ) -> dict[str, Any]:
        """
        Merge a pull request

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
            commit_title: Title for merge commit
            commit_message: Message for merge commit
            merge_method: merge, squash, or rebase

        Returns:
            Merge result
        """
        data = {"merge_method": merge_method}
        if commit_title:
            data["commit_title"] = commit_title
        if commit_message:
            data["commit_message"] = commit_message

        return await self._request(
            "PUT", f"/repos/{owner}/{repo}/pulls/{pr_number}/merge", json_data=data
        )

    async def create_review_comment(
        self, owner: str, repo: str, pr_number: int, body: str, commit_id: str, path: str, line: int
    ) -> dict[str, Any]:
        """
        Add a review comment to a pull request

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
            body: Comment body
            commit_id: SHA of commit to comment on
            path: File path
            line: Line number

        Returns:
            Created comment
        """
        data = {"body": body, "commit_id": commit_id, "path": path, "line": line}

        return await self._request(
            "POST", f"/repos/{owner}/{repo}/pulls/{pr_number}/comments", json_data=data
        )

    # ===== Issue Operations =====

    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str | None = None,
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new issue

        Args:
            owner: Repository owner
            repo: Repository name
            title: Issue title
            body: Issue description
            labels: List of label names
            assignees: List of usernames to assign

        Returns:
            Created issue data
        """
        data = {"title": title}
        if body:
            data["body"] = body
        if labels:
            data["labels"] = labels
        if assignees:
            data["assignees"] = assignees

        return await self._request("POST", f"/repos/{owner}/{repo}/issues", json_data=data)

    async def list_issues(
        self, owner: str, repo: str, state: str = "open", labels: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        List repository issues

        Args:
            owner: Repository owner
            repo: Repository name
            state: Issue state (open, closed, all)
            labels: Filter by labels

        Returns:
            List of issues
        """
        params = {"state": state}
        if labels:
            params["labels"] = ",".join(labels)

        return await self._request("GET", f"/repos/{owner}/{repo}/issues", params=params)

    async def update_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        """Update an issue"""
        data = {}
        if title:
            data["title"] = title
        if body:
            data["body"] = body
        if state:
            data["state"] = state
        if labels:
            data["labels"] = labels

        return await self._request(
            "PATCH", f"/repos/{owner}/{repo}/issues/{issue_number}", json_data=data
        )

    async def add_issue_comment(
        self, owner: str, repo: str, issue_number: int, body: str
    ) -> dict[str, Any]:
        """Add a comment to an issue"""
        return await self._request(
            "POST",
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
            json_data={"body": body},
        )

    # ===== Commit Operations =====

    async def get_commit(self, owner: str, repo: str, sha: str) -> dict[str, Any]:
        """Get commit details"""
        return await self._request("GET", f"/repos/{owner}/{repo}/commits/{sha}")

    async def compare_commits(self, owner: str, repo: str, base: str, head: str) -> dict[str, Any]:
        """Compare two commits"""
        return await self._request("GET", f"/repos/{owner}/{repo}/compare/{base}...{head}")


# Global instance
_github_client: GitHubClient | None = None


def get_github_client(token: str | None = None) -> GitHubClient:
    """Get or create global GitHub client"""
    global _github_client
    if _github_client is None or token:
        _github_client = GitHubClient(token=token)
    return _github_client
