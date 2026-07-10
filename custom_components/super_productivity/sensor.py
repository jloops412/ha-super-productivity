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

    entities = [
        CurrentTaskSensor(coordinator, entry),
        ActiveTaskCountSensor(coordinator, entry),
        TodayTaskCountSensor(coordinator, entry),
        TodayTasksPendingSensor(coordinator, entry),
        TodayTasksDoneSensor(coordinator, entry),
        TimeWorkedTodaySensor(coordinator, entry),
        CurrentTaskTimeSensor(coordinator, entry),
        TaskDetailMarkdownSensor(coordinator, entry),
    ]

    # Per-project task count sensors
    if coordinator.data and coordinator.data.projects:
        for project in coordinator.data.projects:
            if project.get("isArchived"):
                continue
            entities.append(
                ProjectTaskCountSensor(
                    coordinator, entry,
                    project_id=project["id"],
                    project_name=project.get("title", "Unknown"),
                )
            )

    async_add_entities(entities)


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


class CurrentTaskTimeSensor(SuperProductivitySensorBase):
    """Sensor showing time spent on the current task."""

    _attr_name = "Current Task Time"
    _attr_icon = "mdi:timer-cog-outline"
    _attr_native_unit_of_measurement = "min"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, "current_task_time")

    @property
    def native_value(self) -> float | None:
        """Return time spent on current task in minutes."""
        if self._data and self._data.current_task:
            ms = self._data.current_task.get("timeSpent", 0)
            return round(ms / 60_000, 1)
        return None

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return time details and progress."""
        if self._data and self._data.current_task:
            task = self._data.current_task
            spent_ms = task.get("timeSpent", 0)
            estimate_ms = task.get("timeEstimate", 0)
            attrs = {
                "hours": round(spent_ms / 3_600_000, 2),
                "minutes": round(spent_ms / 60_000, 1),
                "milliseconds": spent_ms,
                "estimate_minutes": round(estimate_ms / 60_000, 1) if estimate_ms else None,
            }
            if estimate_ms > 0:
                attrs["progress_percent"] = min(round((spent_ms / estimate_ms) * 100, 1), 999)
                attrs["remaining_minutes"] = max(round((estimate_ms - spent_ms) / 60_000, 1), 0)
            return attrs
        return None

    @property
    def available(self) -> bool:
        """Only available when tracking."""
        if self._data:
            return self._data.is_tracking
        return False


class ProjectTaskCountSensor(SuperProductivitySensorBase):
    """Sensor showing task count for a specific project."""

    _attr_icon = "mdi:folder-outline"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry, project_id: str, project_name: str) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, f"project_{project_id}_tasks")
        self._project_id = project_id
        self._attr_name = f"{project_name} Tasks"

    @property
    def native_value(self) -> int | None:
        """Return pending task count for this project."""
        if self._data:
            count = sum(
                1 for t in self._data.tasks
                if t.get("projectId") == self._project_id
                and not t.get("isDone")
                and not t.get("parentId")
            )
            return count
        return None

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return detailed counts."""
        if self._data:
            project_tasks = [
                t for t in self._data.tasks
                if t.get("projectId") == self._project_id
                and not t.get("parentId")
            ]
            return {
                "total": len(project_tasks),
                "pending": sum(1 for t in project_tasks if not t.get("isDone")),
                "done": sum(1 for t in project_tasks if t.get("isDone")),
                "project_id": self._project_id,
            }
        return None


class TaskDetailMarkdownSensor(SuperProductivitySensorBase):
    """Sensor that outputs markdown-formatted details of the current task.

    Use with a Markdown card:
      type: markdown
      content: "{{ state_attr('sensor.super_productivity_task_details', 'markdown') }}"
    """

    _attr_name = "Task Details"
    _attr_icon = "mdi:text-box-outline"

    def __init__(self, coordinator, entry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, "task_details_md")

    @property
    def native_value(self) -> str | None:
        """Return a short summary as the state."""
        if self._data and self._data.current_task:
            return self._data.current_task.get("title", "")[:255]
        return "No active task"

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return markdown-rendered task details."""
        if not self._data or not self._data.current_task:
            return {"markdown": "*No task being tracked*"}

        task = self._data.current_task
        lines = []

        # Title
        title = task.get("title", "Untitled")
        lines.append(f"## {title}")
        lines.append("")

        # Project & Tags
        project_name = None
        project_id = task.get("projectId")
        if project_id and self._data.projects:
            for p in self._data.projects:
                if p.get("id") == project_id:
                    project_name = p.get("title")
                    break

        tag_names = []
        tag_ids = task.get("tagIds", [])
        if tag_ids and self._data.tags:
            tag_map = {t.get("id"): t.get("title") for t in self._data.tags}
            tag_names = [tag_map.get(tid, tid) for tid in tag_ids if tid in tag_map]

        meta_parts = []
        if project_name:
            meta_parts.append(f"**Project:** {project_name}")
        if tag_names:
            meta_parts.append(f"**Tags:** {', '.join(tag_names)}")
        if meta_parts:
            lines.append(" | ".join(meta_parts))
            lines.append("")

        # Time tracking
        spent_ms = task.get("timeSpent", 0)
        estimate_ms = task.get("timeEstimate", 0)
        if spent_ms > 0 or estimate_ms > 0:
            spent_min = round(spent_ms / 60_000)
            spent_h = spent_min // 60
            spent_m = spent_min % 60
            time_str = f"{spent_h}h {spent_m}m" if spent_h > 0 else f"{spent_m}m"

            if estimate_ms > 0:
                est_min = round(estimate_ms / 60_000)
                est_h = est_min // 60
                est_m = est_min % 60
                est_str = f"{est_h}h {est_m}m" if est_h > 0 else f"{est_m}m"
                pct = min(round((spent_ms / estimate_ms) * 100), 999)
                lines.append(f"**Time:** {time_str} / {est_str} ({pct}%)")
            else:
                lines.append(f"**Time:** {time_str}")
            lines.append("")

        # Due date
        due_day = task.get("dueDay")
        due_time = task.get("dueWithTime")
        if due_time:
            import datetime
            dt = datetime.datetime.fromtimestamp(due_time / 1000)
            lines.append(f"**Due:** {dt.strftime('%b %d, %Y %I:%M %p')}")
            lines.append("")
        elif due_day:
            lines.append(f"**Due:** {due_day}")
            lines.append("")

        # Subtasks
        sub_task_ids = task.get("subTaskIds", [])
        if sub_task_ids and self._data.tasks:
            lines.append("### Subtasks")
            for sub_id in sub_task_ids:
                sub = next((t for t in self._data.tasks if t.get("id") == sub_id), None)
                if sub:
                    check = "- [x]" if sub.get("isDone") else "- [ ]"
                    lines.append(f"{check} {sub.get('title', '?')}")
            lines.append("")

        # Notes
        notes = task.get("notes")
        if notes:
            lines.append("### Notes")
            lines.append(notes.strip())
            lines.append("")

        return {"markdown": "\n".join(lines)}
