"""Diagnostics support for Super Productivity."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data

    data = coordinator.data
    if not data:
        return {"error": "No data available - integration may not be connected"}

    return {
        "config": {
            "host": entry.data.get("host"),
            "port": entry.data.get("port"),
            "scan_interval": entry.options.get("scan_interval", 30),
        },
        "status": {
            "connected": data is not None,
            "is_tracking": data.is_tracking,
            "current_task_id": data.current_task_id,
            "task_count": data.task_count,
            "today_task_count": data.today_task_count,
            "today_pending": data.today_tasks_pending,
            "today_done": data.today_tasks_done,
            "time_worked_today_ms": data.time_worked_today,
            "project_count": len(data.projects),
            "tag_count": len(data.tags),
        },
        "projects": [
            {"id": p.get("id"), "title": p.get("title"), "archived": p.get("isArchived", False)}
            for p in data.projects
        ],
        "tags": [
            {"id": t.get("id"), "title": t.get("title")}
            for t in data.tags
        ],
    }
