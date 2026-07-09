"""Binary sensor platform for Super Productivity."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
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
    """Set up Super Productivity binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities([TrackingBinarySensor(coordinator, entry)])


class TrackingBinarySensor(
    CoordinatorEntity[SuperProductivityCoordinator], BinarySensorEntity
):
    """Binary sensor indicating whether time tracking is active."""

    _attr_has_entity_name = True
    _attr_name = "Tracking Active"
    _attr_icon = "mdi:timer"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(
        self,
        coordinator: SuperProductivityCoordinator,
        entry: SuperProductivityConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_tracking_active"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Super Productivity",
            "manufacturer": "Super Productivity",
            "model": "Local REST API",
            "entry_type": "service",
        }

    @property
    def is_on(self) -> bool | None:
        """Return True if tracking is active."""
        if self.coordinator.data:
            return self.coordinator.data.is_tracking
        return None

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return the current task ID if tracking."""
        if self.coordinator.data and self.coordinator.data.is_tracking:
            task = self.coordinator.data.current_task
            if task:
                return {
                    "task_id": task.get("id"),
                    "task_title": task.get("title"),
                }
        return None
