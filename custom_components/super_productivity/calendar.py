"""Calendar platform for Super Productivity."""

from __future__ import annotations

import datetime
import logging
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
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
    """Set up the Super Productivity calendar."""
    coordinator = entry.runtime_data
    async_add_entities([SuperProductivityCalendar(coordinator, entry)])


class SuperProductivityCalendar(
    CoordinatorEntity[SuperProductivityCoordinator], CalendarEntity
):
    """Calendar entity showing scheduled SP tasks as events."""

    _attr_has_entity_name = True
    _attr_name = "SP Schedule"
    _attr_icon = "mdi:calendar-check"

    def __init__(
        self,
        coordinator: SuperProductivityCoordinator,
        entry: SuperProductivityConfigEntry,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_calendar"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Super Productivity",
            "manufacturer": "Super Productivity",
            "model": "Local REST API",
            "entry_type": "service",
        }

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current/next event (the current tracked task)."""
        if not self.coordinator.data or not self.coordinator.data.current_task:
            return None

        task = self.coordinator.data.current_task
        now = datetime.datetime.now(tz=datetime.timezone.utc)

        return CalendarEvent(
            summary=task.get("title", ""),
            start=now,
            end=now + datetime.timedelta(hours=1),
            description=task.get("notes") or "",
        )

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Return scheduled tasks as calendar events."""
        if not self.coordinator.data:
            return []

        events = []
        for task in self.coordinator.data.tasks:
            if task.get("parentId"):
                continue

            # Get the scheduled time/date
            event_start = None
            event_end = None

            planned_at = task.get("plannedAt")
            due_with_time = task.get("dueWithTime")
            due_day = task.get("dueDay")

            if planned_at:
                event_start = datetime.datetime.fromtimestamp(
                    planned_at / 1000, tz=datetime.timezone.utc
                )
            elif due_with_time:
                event_start = datetime.datetime.fromtimestamp(
                    due_with_time / 1000, tz=datetime.timezone.utc
                )
            elif due_day:
                try:
                    d = datetime.date.fromisoformat(due_day)
                    event_start = datetime.datetime.combine(
                        d, datetime.time.min, tzinfo=datetime.timezone.utc
                    )
                except (ValueError, TypeError):
                    continue
            else:
                continue  # No date = no calendar event

            # Filter to requested range
            if event_start < start_date or event_start > end_date:
                continue

            # Duration based on time estimate or default 1 hour
            estimate_ms = task.get("timeEstimate", 0)
            if estimate_ms > 0:
                duration = datetime.timedelta(milliseconds=estimate_ms)
            else:
                duration = datetime.timedelta(hours=1)

            event_end = event_start + duration

            # Build description
            desc_parts = []
            if task.get("notes"):
                desc_parts.append(task["notes"])
            spent_ms = task.get("timeSpent", 0)
            if spent_ms > 0:
                desc_parts.append(f"Time spent: {round(spent_ms / 60_000)}m")
            if task.get("isDone"):
                desc_parts.append("Status: DONE")

            events.append(CalendarEvent(
                summary=task.get("title", "Untitled"),
                start=event_start,
                end=event_end,
                description="\n".join(desc_parts) if desc_parts else None,
            ))

        return events
