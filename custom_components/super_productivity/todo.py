"""Todo platform for Super Productivity."""

from __future__ import annotations

import datetime
import logging
from typing import Any, cast

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import SuperProductivityApi
from .coordinator import (
    SuperProductivityConfigEntry,
    SuperProductivityCoordinator,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SuperProductivityConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Super Productivity todo platform."""
    coordinator = entry.runtime_data

    entities: list[TodoListEntity] = []

    # Create a todo list for each project
    if coordinator.data and coordinator.data.projects:
        for project in coordinator.data.projects:
            if project.get("isArchived"):
                continue
            entities.append(
                SuperProductivityTodoList(
                    coordinator,
                    entry,
                    project_id=project["id"],
                    project_name=project.get("title", "Unnamed Project"),
                )
            )

    # Create a "Today" todo list
    entities.append(
        SuperProductivityTodayTodoList(coordinator, entry)
    )

    async_add_entities(entities)


def _parse_due_date(task: dict[str, Any]) -> datetime.date | datetime.datetime | None:
    """Parse due date from a task."""
    # dueWithTime takes priority (unix ms timestamp)
    due_with_time = task.get("dueWithTime")
    if due_with_time:
        try:
            return datetime.datetime.fromtimestamp(
                due_with_time / 1000, tz=datetime.timezone.utc
            )
        except (ValueError, TypeError, OSError):
            pass

    # Fall back to dueDay (YYYY-MM-DD string)
    due_day = task.get("dueDay")
    if due_day:
        try:
            return datetime.date.fromisoformat(due_day)
        except (ValueError, TypeError):
            pass

    return None


def _task_to_todo_item(task: dict[str, Any], all_tasks: list[dict[str, Any]] | None = None) -> TodoItem:
    """Convert a Super Productivity task to a HA TodoItem."""
    status = (
        TodoItemStatus.COMPLETED if task.get("isDone") else TodoItemStatus.NEEDS_ACTION
    )

    # Build rich description with subtasks, time, and metadata
    desc_parts = []

    # Notes
    notes = task.get("notes")
    if notes:
        desc_parts.append(notes.strip())

    # Subtasks
    sub_task_ids = task.get("subTaskIds", [])
    if sub_task_ids and all_tasks:
        subtask_lines = []
        for sub_id in sub_task_ids:
            sub = next((t for t in all_tasks if t.get("id") == sub_id), None)
            if sub:
                check = "[x]" if sub.get("isDone") else "[ ]"
                subtask_lines.append(f"  {check} {sub.get('title', '?')}")
        if subtask_lines:
            desc_parts.append("Subtasks:\n" + "\n".join(subtask_lines))

    # Time tracking info
    time_spent = task.get("timeSpent", 0)
    time_estimate = task.get("timeEstimate", 0)
    if time_spent > 0 or time_estimate > 0:
        time_info = []
        if time_spent > 0:
            mins = round(time_spent / 60_000)
            time_info.append(f"Spent: {mins}m")
        if time_estimate > 0:
            est_mins = round(time_estimate / 60_000)
            time_info.append(f"Estimate: {est_mins}m")
        if time_spent > 0 and time_estimate > 0:
            pct = min(round((time_spent / time_estimate) * 100), 999)
            time_info.append(f"Progress: {pct}%")
        desc_parts.append(" | ".join(time_info))

    description = "\n\n".join(desc_parts) if desc_parts else None

    return TodoItem(
        uid=task["id"],
        summary=task.get("title", ""),
        status=status,
        due=_parse_due_date(task),
        description=description,
    )


class SuperProductivityTodoList(
    CoordinatorEntity[SuperProductivityCoordinator], TodoListEntity
):
    """A Super Productivity project as a HA todo list."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.SET_DUE_DATE_ON_ITEM
        | TodoListEntityFeature.SET_DUE_DATETIME_ON_ITEM
        | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
    )

    def __init__(
        self,
        coordinator: SuperProductivityCoordinator,
        entry: SuperProductivityConfigEntry,
        project_id: str,
        project_name: str,
    ) -> None:
        """Initialize the todo list."""
        super().__init__(coordinator)
        self._project_id = project_id
        self._attr_unique_id = f"{entry.entry_id}_todo_{project_id}"
        self._attr_name = f"SP: {project_name}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Super Productivity",
            "manufacturer": "Super Productivity",
            "model": "Local REST API",
            "entry_type": "service",
        }

    @property
    def _api(self) -> SuperProductivityApi:
        """Get the API client."""
        return self.coordinator.api

    @property
    def todo_items(self) -> list[TodoItem] | None:
        """Return the list of todo items for this project."""
        if self.coordinator.data is None:
            return None

        all_tasks = self.coordinator.data.tasks
        items = []
        for task in all_tasks:
            if task.get("projectId") != self._project_id:
                continue
            # Skip subtasks (show only top-level tasks)
            if task.get("parentId"):
                continue
            items.append(_task_to_todo_item(task, all_tasks))
        return items

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Create a new task in this project."""
        task_data: dict[str, Any] = {
            "title": item.summary or "Untitled",
            "projectId": self._project_id,
        }

        if item.description:
            task_data["notes"] = item.description

        if item.due:
            if isinstance(item.due, datetime.datetime):
                task_data["dueWithTime"] = int(item.due.timestamp() * 1000)
            elif isinstance(item.due, datetime.date):
                task_data["dueDay"] = item.due.isoformat()

        if item.status == TodoItemStatus.COMPLETED:
            task_data["isDone"] = True

        await self._api.async_create_task(task_data)
        await self.coordinator.async_request_refresh()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update an existing task."""
        uid = cast(str, item.uid)
        updates: dict[str, Any] = {}

        if item.summary is not None:
            updates["title"] = item.summary

        if item.description is not None:
            updates["notes"] = item.description

        if item.status is not None:
            updates["isDone"] = item.status == TodoItemStatus.COMPLETED

        if item.due is not None:
            if isinstance(item.due, datetime.datetime):
                updates["dueWithTime"] = int(item.due.timestamp() * 1000)
                updates["dueDay"] = None
            elif isinstance(item.due, datetime.date):
                updates["dueDay"] = item.due.isoformat()
                updates["dueWithTime"] = None
        # If due is explicitly cleared (None is passed but it was previously set)
        # the HA todo platform doesn't distinguish this well, so we skip clearing

        if updates:
            await self._api.async_update_task(uid, updates)
            await self.coordinator.async_request_refresh()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete tasks."""
        for uid in uids:
            await self._api.async_delete_task(uid)
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle data update."""
        super()._handle_coordinator_update()

    async def async_added_to_hass(self) -> None:
        """Populate initial state."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()


class SuperProductivityTodayTodoList(
    CoordinatorEntity[SuperProductivityCoordinator], TodoListEntity
):
    """A virtual 'Today' todo list showing all tasks scheduled for today."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.SET_DUE_DATE_ON_ITEM
        | TodoListEntityFeature.SET_DUE_DATETIME_ON_ITEM
        | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
    )

    def __init__(
        self,
        coordinator: SuperProductivityCoordinator,
        entry: SuperProductivityConfigEntry,
    ) -> None:
        """Initialize the Today todo list."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_todo_today"
        self._attr_name = "SP: Today"
        self._attr_icon = "mdi:calendar-today"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Super Productivity",
            "manufacturer": "Super Productivity",
            "model": "Local REST API",
            "entry_type": "service",
        }

    @property
    def _api(self) -> SuperProductivityApi:
        """Get the API client."""
        return self.coordinator.api

    @property
    def todo_items(self) -> list[TodoItem] | None:
        """Return today's tasks as todo items."""
        if self.coordinator.data is None:
            return None

        all_tasks = self.coordinator.data.today_tasks
        items = []
        for task in all_tasks:
            # Skip subtasks
            if task.get("parentId"):
                continue
            items.append(_task_to_todo_item(task, all_tasks))
        return items

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update a task (mainly for marking as done)."""
        uid = cast(str, item.uid)
        updates: dict[str, Any] = {}

        if item.summary is not None:
            updates["title"] = item.summary

        if item.description is not None:
            updates["notes"] = item.description

        if item.status is not None:
            updates["isDone"] = item.status == TodoItemStatus.COMPLETED

        if item.due is not None:
            if isinstance(item.due, datetime.datetime):
                updates["dueWithTime"] = int(item.due.timestamp() * 1000)
                updates["dueDay"] = None
            elif isinstance(item.due, datetime.date):
                updates["dueDay"] = item.due.isoformat()
                updates["dueWithTime"] = None

        if updates:
            await self._api.async_update_task(uid, updates)
            await self.coordinator.async_request_refresh()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Not supported for today view - tasks aren't deleted, just unscheduled."""
        _LOGGER.warning("Delete not supported on the Today list")

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle data update."""
        super()._handle_coordinator_update()

    async def async_added_to_hass(self) -> None:
        """Populate initial state."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()
