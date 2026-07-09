"""Sensor platform for Super Productivity."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import (
    SuperProductivityConfigEntry,
    SuperProductivityCoordinator,
    SuperProductivityData,
)
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SuperProductivityConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Super Productivity sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            CurrentTaskSensor(coordinator, entry),
            ActiveTaskCountSensor(coordinator, entry),
            TodayTaskCountSensor(coordinator, entry),
            TodayTasksPendingSensor(coordinator, entry),
            TodayTasksDoneSensor(coordinator, entry),
            TimeWorkedTodaySensor(coordinator, entry),
        ]
    )


class SuperProductivitySensorBase(
    CoordinatorEntity[SuperProductivityCoordinator], SensorEntity
):
    """Base class for Super Productivity sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SuperProductivityCoordinator,
        entry: SuperProductivityConfigEntry,
        key: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Super Productivity",
            "manufacturer": "Super Productivity",
            "model": "Local REST API",
            "entry_type": "service",
        }

    @property
    def _data(self) -> SuperProductivityData | None:
        """Get the coordinator data."""
        return self.coordinator.data


class CurrentTaskSensor(SuperProductivitySensorBase):
    """Sensor showing the currently tracked task."""

    _attr_name = "Current Task"
    _attr_icon = "mdi:timer-outline"

    def __init__(self, coordinator, entry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, "current_task")

    @property
    def native_value(self) -> str | None:
        """Return the current task title."""
        if self._data and self._data.current_task:
            return self._data.current_task.get("title")
        return None

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return extra attributes about the current task."""
        if self._data and self._data.current_task:
            task = self._data.current_task
            # Calculate time spent in human-readable format
            time_spent_ms = task.get("timeSpent", 0)
            time_estimate_ms = task.get("timeEstimate", 0)
            hours_spent = round(time_spent_ms / 3_600_000, 2)
            mins_spent = round(time_spent_ms / 60_000, 1)
            hours_est = round(time_estimate_ms / 3_600_000, 2)

            # Progress percentage
            progress = None
            if time_estimate_ms > 0:
                progress = min(round((time_spent_ms / time_estimate_ms) * 100, 1), 999)

            # Find project name
            project_name = None
            project_id = task.get("projectId")
            if project_id and self._data.projects:
                for p in self._data.projects:
                    if p.get("id") == project_id:
                        project_name = p.get("title")
                        break

            # Find tag names
            tag_names = []
            tag_ids = task.get("tagIds", [])
            if tag_ids and self._data.tags:
                tag_map = {t.get("id"): t.get("title") for t in self._data.tags}
                tag_names = [tag_map.get(tid, tid) for tid in tag_ids]

            # Subtask info
            sub_task_ids = task.get("subTaskIds", [])

            return {
                "task_id": task.get("id"),
                "project_id": project_id,
                "project_name": project_name,
                "time_spent_hours": hours_spent,
                "time_spent_minutes": mins_spent,
                "time_spent_ms": time_spent_ms,
                "time_estimate_hours": hours_est,
                "time_estimate_ms": time_estimate_ms,
                "progress_percent": progress,
                "is_done": task.get("isDone", False),
                "notes": task.get("notes") or None,
                "tag_ids": tag_ids,
                "tag_names": tag_names,
                "subtask_count": len(sub_task_ids),
                "due_day": task.get("dueDay"),
                "due_with_time": task.get("dueWithTime"),
                "planned_at": task.get("plannedAt"),
                "created": task.get("created"),
            }
        return None


class ActiveTaskCountSensor(SuperProductivitySensorBase):
    """Sensor showing the total number of active tasks."""

    _attr_name = "Active Tasks"
    _attr_icon = "mdi:format-list-checks"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, "active_task_count")

    @property
    def native_value(self) -> int | None:
        """Return the active task count."""
        if self._data:
            return self._data.task_count
        return None


class TodayTaskCountSensor(SuperProductivitySensorBase):
    """Sensor showing the number of tasks scheduled for today."""

    _attr_name = "Today's Tasks"
    _attr_icon = "mdi:calendar-today"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, "today_task_count")

    @property
    def native_value(self) -> int | None:
        """Return today's task count."""
        if self._data:
            return self._data.today_task_count
        return None


class TodayTasksPendingSensor(SuperProductivitySensorBase):
    """Sensor showing the number of pending tasks for today."""

    _attr_name = "Today's Pending Tasks"
    _attr_icon = "mdi:clipboard-list-outline"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, "today_tasks_pending")

    @property
    def native_value(self) -> int | None:
        """Return today's pending task count."""
        if self._data:
            return self._data.today_tasks_pending
        return None


class TodayTasksDoneSensor(SuperProductivitySensorBase):
    """Sensor showing the number of completed tasks for today."""

    _attr_name = "Today's Completed Tasks"
    _attr_icon = "mdi:clipboard-check-outline"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, "today_tasks_done")

    @property
    def native_value(self) -> int | None:
        """Return today's completed task count."""
        if self._data:
            return self._data.today_tasks_done
        return None


class TimeWorkedTodaySensor(SuperProductivitySensorBase):
    """Sensor showing total time worked today."""

    _attr_name = "Time Worked Today"
    _attr_icon = "mdi:clock-outline"
    _attr_native_unit_of_measurement = "h"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, "time_worked_today")

    @property
    def native_value(self) -> float | None:
        """Return time worked today in hours."""
        if self._data:
            ms = self._data.time_worked_today
            return round(ms / 3_600_000, 2)
        return None

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return time in various units."""
        if self._data:
            ms = self._data.time_worked_today
            return {
                "minutes": round(ms / 60_000, 1),
                "seconds": round(ms / 1_000),
                "milliseconds": ms,
            }
        return None
