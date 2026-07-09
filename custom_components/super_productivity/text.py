"""Text platform for Super Productivity."""

from __future__ import annotations

import logging

from homeassistant.components.text import TextEntity
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
    """Set up Super Productivity text entities."""
    coordinator = entry.runtime_data
    async_add_entities([QuickAddTaskText(coordinator, entry)])


class QuickAddTaskText(CoordinatorEntity[SuperProductivityCoordinator], TextEntity):
    """Text input for quickly adding a task.

    Type a task title and press enter - it gets created in SP.
    """

    _attr_has_entity_name = True
    _attr_name = "Quick Add Task"
    _attr_icon = "mdi:plus-circle-outline"
    _attr_native_max = 255
    _attr_native_min = 1
    _attr_mode = "text"
    _attr_pattern = None

    def __init__(
        self,
        coordinator: SuperProductivityCoordinator,
        entry: SuperProductivityConfigEntry,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_text_quick_add"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Super Productivity",
            "manufacturer": "Super Productivity",
            "model": "Local REST API",
            "entry_type": "service",
        }
        self._attr_native_value = ""

    @property
    def native_value(self) -> str:
        """Return empty string (resets after each task creation)."""
        return self._attr_native_value

    async def async_set_value(self, value: str) -> None:
        """Create a task with the given title."""
        if not value or not value.strip():
            return

        title = value.strip()

        # Determine target project from the project picker select entity
        project_id = None
        # Try to find the project picker's selected project
        hass = self.hass
        project_state = hass.states.get(
            f"select.super_productivity_active_project"
        )
        if project_state and project_state.attributes.get("project_id"):
            project_id = project_state.attributes["project_id"]

        task_data = {"title": title}
        if project_id:
            task_data["projectId"] = project_id

        try:
            await self.coordinator.api.async_create_task(task_data)
            _LOGGER.info("Created task: %s", title)
        except Exception as err:
            _LOGGER.error("Failed to create task '%s': %s", title, err)
            return

        # Clear the input
        self._attr_native_value = ""
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
