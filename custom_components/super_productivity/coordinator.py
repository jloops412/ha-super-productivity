"""DataUpdateCoordinator for Super Productivity."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    SuperProductivityApi,
    SuperProductivityConnectionError,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, TAG_TODAY

_LOGGER = logging.getLogger(__name__)

type SuperProductivityConfigEntry = ConfigEntry["SuperProductivityCoordinator"]


class SuperProductivityData:
    """Container for all data fetched from Super Productivity."""

    def __init__(
        self,
        status: dict[str, Any],
        tasks: list[dict[str, Any]],
        today_tasks: list[dict[str, Any]],
        projects: list[dict[str, Any]],
        tags: list[dict[str, Any]],
    ) -> None:
        """Initialize the data container."""
        self.status = status
        self.tasks = tasks
        self.today_tasks = today_tasks
        self.projects = projects
        self.tags = tags

    @property
    def current_task(self) -> dict[str, Any] | None:
        """Get the current task from status."""
        return self.status.get("currentTask")

    @property
    def current_task_id(self) -> str | None:
        """Get the current task ID."""
        return self.status.get("currentTaskId")

    @property
    def task_count(self) -> int:
        """Get total active task count."""
        return self.status.get("taskCount", 0)

    @property
    def today_task_count(self) -> int:
        """Get count of today's tasks."""
        return len(self.today_tasks)

    @property
    def today_tasks_done(self) -> int:
        """Get count of completed today's tasks."""
        return sum(1 for t in self.today_tasks if t.get("isDone"))

    @property
    def today_tasks_pending(self) -> int:
        """Get count of pending today's tasks."""
        return self.today_task_count - self.today_tasks_done

    @property
    def is_tracking(self) -> bool:
        """Return True if a task is currently being tracked."""
        return self.current_task_id is not None

    @property
    def time_worked_today(self) -> int:
        """Calculate total time worked today in ms (sum of timeSpent on today's tasks)."""
        total = 0
        for task in self.today_tasks:
            total += task.get("timeSpent", 0)
        return total


class SuperProductivityCoordinator(DataUpdateCoordinator[SuperProductivityData]):
    """Coordinator for fetching data from Super Productivity."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api: SuperProductivityApi,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api

    async def _async_update_data(self) -> SuperProductivityData:
        """Fetch data from the Super Productivity API."""
        try:
            async with asyncio.timeout(15):
                # Fetch all data concurrently
                status, tasks, today_tasks, projects, tags = await asyncio.gather(
                    self.api.async_get_status(),
                    self.api.async_get_tasks(),
                    self.api.async_get_tasks(tag_id=TAG_TODAY, include_done=True),
                    self.api.async_get_projects(),
                    self.api.async_get_tags(),
                )
        except asyncio.CancelledError:
            raise
        except SuperProductivityConnectionError as err:
            raise UpdateFailed(
                f"Cannot connect to Super Productivity: {err}"
            ) from err
        except Exception as err:
            raise UpdateFailed(
                f"Error fetching Super Productivity data: {err}"
            ) from err

        return SuperProductivityData(
            status=status,
            tasks=tasks,
            today_tasks=today_tasks,
            projects=projects,
            tags=tags,
        )
