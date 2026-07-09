"""API client for Super Productivity Local REST API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import (
    ENDPOINT_HEALTH,
    ENDPOINT_PROJECTS,
    ENDPOINT_STATUS,
    ENDPOINT_TAGS,
    ENDPOINT_TASK_CONTROL_CURRENT,
    ENDPOINT_TASK_CONTROL_STOP,
    ENDPOINT_TASKS,
)

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10


class SuperProductivityApiError(Exception):
    """Base exception for API errors."""


class SuperProductivityConnectionError(SuperProductivityApiError):
    """Exception for connection errors."""


class SuperProductivityNotFoundError(SuperProductivityApiError):
    """Exception for 404 errors."""


class SuperProductivityValidationError(SuperProductivityApiError):
    """Exception for 400 validation errors."""


class SuperProductivityApi:
    """Client for the Super Productivity Local REST API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._base_url = f"http://{host}:{port}"
        self._port = port
        # SP validates Host header - must be 127.0.0.1:<port> or localhost:<port>
        # even when connecting via a port proxy from another machine
        self._headers = {"Host": f"127.0.0.1:{port}"}

    @property
    def base_url(self) -> str:
        """Return the base URL."""
        return self._base_url

    async def _request(
        self,
        method: str,
        path: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make a request to the API."""
        url = f"{self._base_url}{path}"
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                resp = await self._session.request(
                    method,
                    url,
                    json=json_data,
                    params=params,
                    headers=self._headers,
                )
        except asyncio.TimeoutError as err:
            raise SuperProductivityConnectionError(
                f"Timeout connecting to Super Productivity at {url}"
            ) from err
        except aiohttp.ClientError as err:
            raise SuperProductivityConnectionError(
                f"Error connecting to Super Productivity at {url}: {err}"
            ) from err

        if resp.status == 404:
            data = await resp.json()
            msg = data.get("error", {}).get("message", "Not found")
            raise SuperProductivityNotFoundError(msg)

        if resp.status == 400:
            data = await resp.json()
            msg = data.get("error", {}).get("message", "Validation error")
            raise SuperProductivityValidationError(msg)

        if resp.status >= 400:
            text = await resp.text()
            raise SuperProductivityApiError(
                f"API error {resp.status}: {text}"
            )

        data = await resp.json()
        if not data.get("ok"):
            error = data.get("error", {})
            raise SuperProductivityApiError(
                f"API returned error: {error.get('message', 'Unknown error')}"
            )
        return data.get("data", {})

    # --- Health ---

    async def async_health_check(self) -> dict[str, Any]:
        """Check if the API is healthy."""
        return await self._request("GET", ENDPOINT_HEALTH)

    # --- Status ---

    async def async_get_status(self) -> dict[str, Any]:
        """Get current status (current task + task count)."""
        return await self._request("GET", ENDPOINT_STATUS)

    # --- Tasks ---

    async def async_get_tasks(
        self,
        query: str | None = None,
        project_id: str | None = None,
        tag_id: str | None = None,
        include_done: bool = False,
        source: str = "active",
    ) -> list[dict[str, Any]]:
        """Get tasks with optional filters."""
        params: dict[str, str] = {}
        if query:
            params["query"] = query
        if project_id:
            params["projectId"] = project_id
        if tag_id:
            params["tagId"] = tag_id
        if include_done:
            params["includeDone"] = "true"
        if source != "active":
            params["source"] = source

        result = await self._request("GET", ENDPOINT_TASKS, params=params)
        # The API returns the task list directly as the data field
        if isinstance(result, list):
            return result
        return result.get("tasks", result) if isinstance(result, dict) else []

    async def async_get_task(self, task_id: str) -> dict[str, Any]:
        """Get a single task by ID."""
        return await self._request("GET", f"{ENDPOINT_TASKS}/{task_id}")

    async def async_create_task(self, task_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new task."""
        return await self._request("POST", ENDPOINT_TASKS, json_data=task_data)

    async def async_update_task(
        self, task_id: str, updates: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a task."""
        return await self._request(
            "PATCH", f"{ENDPOINT_TASKS}/{task_id}", json_data=updates
        )

    async def async_delete_task(self, task_id: str) -> dict[str, Any]:
        """Delete a task."""
        return await self._request("DELETE", f"{ENDPOINT_TASKS}/{task_id}")

    async def async_start_task(self, task_id: str) -> dict[str, Any]:
        """Start tracking a task."""
        return await self._request("POST", f"{ENDPOINT_TASKS}/{task_id}/start")

    async def async_archive_task(self, task_id: str) -> dict[str, Any]:
        """Archive a task."""
        return await self._request("POST", f"{ENDPOINT_TASKS}/{task_id}/archive")

    async def async_restore_task(self, task_id: str) -> dict[str, Any]:
        """Restore an archived task."""
        return await self._request("POST", f"{ENDPOINT_TASKS}/{task_id}/restore")

    # --- Task Control ---

    async def async_get_current_task(self) -> dict[str, Any] | None:
        """Get the currently tracked task."""
        return await self._request("GET", ENDPOINT_TASK_CONTROL_CURRENT)

    async def async_set_current_task(self, task_id: str | None) -> dict[str, Any]:
        """Set or clear the current task."""
        return await self._request(
            "POST", ENDPOINT_TASK_CONTROL_CURRENT, json_data={"taskId": task_id}
        )

    async def async_stop_current_task(self) -> dict[str, Any]:
        """Stop tracking the current task."""
        return await self._request("POST", ENDPOINT_TASK_CONTROL_STOP)

    # --- Projects ---

    async def async_get_projects(
        self, query: str | None = None
    ) -> list[dict[str, Any]]:
        """Get all projects."""
        params: dict[str, str] = {}
        if query:
            params["query"] = query
        result = await self._request("GET", ENDPOINT_PROJECTS, params=params)
        if isinstance(result, list):
            return result
        return result.get("projects", result) if isinstance(result, dict) else []

    # --- Tags ---

    async def async_get_tags(self, query: str | None = None) -> list[dict[str, Any]]:
        """Get all tags."""
        params: dict[str, str] = {}
        if query:
            params["query"] = query
        result = await self._request("GET", ENDPOINT_TAGS, params=params)
        if isinstance(result, list):
            return result
        return result.get("tags", result) if isinstance(result, dict) else []
