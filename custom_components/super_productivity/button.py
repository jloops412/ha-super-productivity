"""Button platform for Super Productivity."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
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
    """Set up Super Productivity buttons."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            StopTrackingButton(coordinator, entry),
            ArchiveCurrentTaskButton(coordinator, entry),
            CompleteCurrentTaskButton(coordinator, entry),
        ]
    )


class SPButtonBase(CoordinatorEntity[SuperProductivityCoordinator], ButtonEntity):
    """Base class for SP buttons."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SuperProductivityCoordinator,
        entry: SuperProductivityConfigEntry,
        key: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Super Productivity",
            "manufacturer": "Super Productivity",
            "model": "Local REST API",
            "entry_type": "service",
        }


class StopTrackingButton(SPButtonBase):
    """Button to stop tracking the current task."""

    _attr_name = "Stop Tracking"
    _attr_icon = "mdi:stop-circle-outline"

    def __init__(self, coordinator, entry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, "btn_stop_tracking")

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.api.async_stop_current_task()
        await self.coordinator.async_request_refresh()


class CompleteCurrentTaskButton(SPButtonBase):
    """Button to mark the current task as done."""

    _attr_name = "Complete Current Task"
    _attr_icon = "mdi:check-circle-outline"

    def __init__(self, coordinator, entry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, "btn_complete_current")

    async def async_press(self) -> None:
        """Handle the button press."""
        if self.coordinator.data and self.coordinator.data.current_task_id:
            task_id = self.coordinator.data.current_task_id
            await self.coordinator.api.async_stop_current_task()
            await self.coordinator.api.async_update_task(task_id, {"isDone": True})
            await self.coordinator.async_request_refresh()


class ArchiveCurrentTaskButton(SPButtonBase):
    """Button to archive the current task (stops tracking first)."""

    _attr_name = "Archive Current Task"
    _attr_icon = "mdi:archive-arrow-down-outline"

    def __init__(self, coordinator, entry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, "btn_archive_current")

    async def async_press(self) -> None:
        """Handle the button press."""
        if self.coordinator.data and self.coordinator.data.current_task_id:
            task_id = self.coordinator.data.current_task_id
            await self.coordinator.api.async_stop_current_task()
            await self.coordinator.api.async_archive_task(task_id)
            await self.coordinator.async_request_refresh()
