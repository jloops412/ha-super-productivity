"""Switch platform for Super Productivity."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
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
    """Set up Super Productivity switches."""
    coordinator = entry.runtime_data
    async_add_entities([TrackingSwitch(coordinator, entry)])


class TrackingSwitch(CoordinatorEntity[SuperProductivityCoordinator], SwitchEntity):
    """Switch to start/stop tracking the current task.

    ON = tracking is active (turn off to stop)
    OFF = not tracking (turn on to resume last task)
    """

    _attr_has_entity_name = True
    _attr_name = "Time Tracking"
    _attr_icon = "mdi:timer-play-outline"

    def __init__(
        self,
        coordinator: SuperProductivityCoordinator,
        entry: SuperProductivityConfigEntry,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_switch_tracking"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Super Productivity",
            "manufacturer": "Super Productivity",
            "model": "Local REST API",
            "entry_type": "service",
        }
        self._last_task_id: str | None = None

    @property
    def is_on(self) -> bool | None:
        """Return True if tracking is active."""
        if self.coordinator.data:
            is_tracking = self.coordinator.data.is_tracking
            # Remember the last tracked task so we can resume
            if is_tracking and self.coordinator.data.current_task_id:
                self._last_task_id = self.coordinator.data.current_task_id
            return is_tracking
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start tracking. Resumes the last task if available."""
        if self._last_task_id:
            await self.coordinator.api.async_start_task(self._last_task_id)
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.warning("No previous task to resume tracking")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop tracking."""
        await self.coordinator.api.async_stop_current_task()
        await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict | None:
        """Show what task would be resumed."""
        attrs = {}
        if self._last_task_id:
            attrs["last_task_id"] = self._last_task_id
        if self.coordinator.data and self.coordinator.data.current_task:
            attrs["current_task_title"] = self.coordinator.data.current_task.get("title")
        return attrs if attrs else None
