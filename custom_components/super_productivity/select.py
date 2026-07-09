"""Select platform for Super Productivity."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

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
    """Set up Super Productivity select entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            TaskPickerSelect(coordinator, entry),
            ProjectPickerSelect(coordinator, entry),
        ]
    )


class TaskPickerSelect(CoordinatorEntity[SuperProductivityCoordinator], SelectEntity):
    """Select entity to pick and start tracking a task from today's list."""

    _attr_has_entity_name = True
    _attr_name = "Start Task"
    _attr_icon = "mdi:play-circle-outline"

    def __init__(
        self,
        coordinator: SuperProductivityCoordinator,
        entry: SuperProductivityConfigEntry,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_select_task"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Super Productivity",
            "manufacturer": "Super Productivity",
            "model": "Local REST API",
            "entry_type": "service",
        }
        self._task_map: dict[str, str] = {}  # title -> id

    @property
    def options(self) -> list[str]:
        """Return list of today's task titles as options."""
        if not self.coordinator.data:
            return []

        self._task_map = {}
        options = []
        for task in self.coordinator.data.today_tasks:
            if task.get("isDone"):
                continue
            if task.get("parentId"):
                continue
            title = task.get("title", "Untitled")
            task_id = task.get("id", "")
            # Handle duplicate titles by appending a suffix
            display = title
            count = 1
            while display in self._task_map:
                count += 1
                display = f"{title} ({count})"
            self._task_map[display] = task_id
            options.append(display)

        return options if options else ["No tasks for today"]

    @property
    def current_option(self) -> str | None:
        """Return the currently tracked task title."""
        if self.coordinator.data and self.coordinator.data.current_task:
            title = self.coordinator.data.current_task.get("title", "")
            # Find it in our map
            for display, task_id in self._task_map.items():
                if task_id == self.coordinator.data.current_task_id:
                    return display
            return title
        return None

    async def async_select_option(self, option: str) -> None:
        """Start tracking the selected task."""
        if option == "No tasks for today":
            return

        task_id = self._task_map.get(option)
        if task_id:
            await self.coordinator.api.async_start_task(task_id)
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.warning("Could not find task ID for: %s", option)


class ProjectPickerSelect(CoordinatorEntity[SuperProductivityCoordinator], SelectEntity):
    """Select entity to pick active project context."""

    _attr_has_entity_name = True
    _attr_name = "Active Project"
    _attr_icon = "mdi:folder-outline"

    def __init__(
        self,
        coordinator: SuperProductivityCoordinator,
        entry: SuperProductivityConfigEntry,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_select_project"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Super Productivity",
            "manufacturer": "Super Productivity",
            "model": "Local REST API",
            "entry_type": "service",
        }
        self._project_map: dict[str, str] = {}  # title -> id
        self._selected_project_id: str | None = None

    @property
    def options(self) -> list[str]:
        """Return list of project titles."""
        if not self.coordinator.data:
            return []

        self._project_map = {}
        options = []
        for project in self.coordinator.data.projects:
            if project.get("isArchived"):
                continue
            title = project.get("title", "Untitled")
            self._project_map[title] = project.get("id", "")
            options.append(title)

        return options if options else ["No projects"]

    @property
    def current_option(self) -> str | None:
        """Return the current project (from the tracked task)."""
        if self.coordinator.data and self.coordinator.data.current_task:
            project_id = self.coordinator.data.current_task.get("projectId")
            for title, pid in self._project_map.items():
                if pid == project_id:
                    return title
        # Fall back to manually selected
        if self._selected_project_id:
            for title, pid in self._project_map.items():
                if pid == self._selected_project_id:
                    return title
        return None

    async def async_select_option(self, option: str) -> None:
        """Set the active project context (for task creation)."""
        self._selected_project_id = self._project_map.get(option)
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict | None:
        """Expose the project ID for use in automations."""
        if self._selected_project_id:
            return {"project_id": self._selected_project_id}
        return None
