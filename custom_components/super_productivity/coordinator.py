"""DataUpdateCoordinator for Super Productivity."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any, TypeAlias

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    SuperProductivityApi,
    SuperProductivityConnectionError,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, TAG_TODAY

_LOGGER = logging.getLogger(__name__)

SuperProductivityConfigEntry: TypeAlias = ConfigEntry

# Event types
EVENT_TASK_STARTED = f"{DOMAIN}_task_started"
EVENT_TASK_STOPPED = f"{DOMAIN}_task_stopped"
EVENT_TASK_COMPLETED = f"{DOMAIN}_task_completed"
EVENT_ALL_TASKS_DONE = f"{DOMAIN}_all_today_tasks_done"


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

    @property
    def done_task_ids(self) -> set[str]:
        """Get set of completed task IDs from today's tasks."""
        return {t.get("id") for t in self.today_tasks if t.get("isDone") and t.get("id")}


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
        self._previous_task_id: str | None = None
        self._previous_done_ids: set[str] = set()
        self._previous_pending_count: int | None = None

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

        new_data = SuperProductivityData(
            status=status,
            tasks=tasks,
            today_tasks=today_tasks,
            projects=projects,
            tags=tags,
        )

        # Fire events based on state changes
        self._detect_and_fire_events(new_data)

        return new_data

    def _detect_and_fire_events(self, new_data: SuperProductivityData) -> None:
        """Compare old vs new data and fire events."""
        new_task_id = new_data.current_task_id
        old_task_id = self._previous_task_id

        # Task started (was not tracking, now tracking)
        if new_task_id and new_task_id != old_task_id:
            task = new_data.current_task or {}
            self.hass.bus.async_fire(EVENT_TASK_STARTED, {
                "task_id": new_task_id,
                "title": task.get("title", ""),
                "project_id": task.get("projectId"),
                "time_estimate_ms": task.get("timeEstimate", 0),
            })
            _LOGGER.debug("Fired event: %s for task %s", EVENT_TASK_STARTED, new_task_id)

        # Task stopped (was tracking, now not)
        if old_task_id and not new_task_id:
            self.hass.bus.async_fire(EVENT_TASK_STOPPED, {
                "task_id": old_task_id,
            })
            _LOGGER.debug("Fired event: %s for task %s", EVENT_TASK_STOPPED, old_task_id)

        # Task completed (new done IDs that weren't done before)
        new_done_ids = new_data.done_task_ids
        newly_completed = new_done_ids - self._previous_done_ids
        for task_id in newly_completed:
            # Find the task data
            task = next((t for t in new_data.today_tasks if t.get("id") == task_id), {})
            self.hass.bus.async_fire(EVENT_TASK_COMPLETED, {
                "task_id": task_id,
                "title": task.get("title", ""),
                "project_id": task.get("projectId"),
                "time_spent_ms": task.get("timeSpent", 0),
            })
            _LOGGER.debug("Fired event: %s for task %s", EVENT_TASK_COMPLETED, task_id)

        # All today's tasks done (transition from >0 pending to 0 pending)
        new_pending = new_data.today_tasks_pending
        if (self._previous_pending_count is not None
                and self._previous_pending_count > 0
                and new_pending == 0
                and new_data.today_task_count > 0):
            self.hass.bus.async_fire(EVENT_ALL_TASKS_DONE, {
                "completed_count": new_data.today_tasks_done,
                "total_count": new_data.today_task_count,
                "time_worked_ms": new_data.time_worked_today,
            })
            _LOGGER.debug("Fired event: %s", EVENT_ALL_TASKS_DONE)

        # Update previous state for next comparison
        self._previous_task_id = new_task_id
        self._previous_done_ids = new_done_ids
        self._previous_pending_count = new_pending
