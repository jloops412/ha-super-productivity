"""The Super Productivity integration."""

from __future__ import annotations

import logging

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SuperProductivityApi
from .const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import SuperProductivityConfigEntry, SuperProductivityCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.TODO,
    Platform.BUTTON,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.TEXT,
    Platform.CALENDAR,
]


async def async_setup_entry(
    hass: HomeAssistant, entry: SuperProductivityConfigEntry
) -> bool:
    """Set up Super Productivity from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]

    session = async_get_clientsession(hass)
    api = SuperProductivityApi(session, host, port)

    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    coordinator = SuperProductivityCoordinator(
        hass,
        config_entry=entry,
        api=api,
        scan_interval=scan_interval,
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload integration when options change
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    # Register webhook for instant updates from SP plugin
    await async_setup_webhook(hass, entry, coordinator)

    # Register services
    await async_setup_services(hass)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: SuperProductivityConfigEntry
) -> bool:
    """Unload a config entry."""
    # Remove webhook
    from homeassistant.components.webhook import async_unregister
    webhook_id = f"{DOMAIN}_{entry.entry_id}"
    async_unregister(hass, webhook_id)

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(
    hass: HomeAssistant, entry: SuperProductivityConfigEntry
) -> None:
    """Handle options update - reload the integration."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_webhook(
    hass: HomeAssistant,
    entry: SuperProductivityConfigEntry,
    coordinator: SuperProductivityCoordinator,
) -> None:
    """Register a webhook for instant updates from SP plugin."""
    from homeassistant.components.webhook import async_register

    webhook_id = f"{DOMAIN}_{entry.entry_id}"

    async def handle_webhook(hass, webhook_id, request):
        """Handle incoming webhook from SP plugin."""
        _LOGGER.debug("Webhook received - triggering immediate refresh")
        await coordinator.async_request_refresh()

    async_register(
        hass,
        DOMAIN,
        "Super Productivity Update",
        webhook_id,
        handle_webhook,
        local_only=True,
    )
    _LOGGER.info(
        "Webhook registered at /api/webhook/%s", webhook_id
    )


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up Super Productivity services."""
    from homeassistant.core import ServiceCall
    import voluptuous as vol

    from .const import (
        ATTR_DUE_DAY,
        ATTR_IS_DONE,
        ATTR_NOTES,
        ATTR_PARENT_ID,
        ATTR_PROJECT_ID,
        ATTR_TAG_IDS,
        ATTR_TASK_ID,
        ATTR_TIME_ESTIMATE,
        ATTR_TITLE,
    )

    def _get_api(hass: HomeAssistant) -> SuperProductivityApi | None:
        """Get the API client from any loaded config entry."""
        entries = hass.config_entries.async_entries(DOMAIN)
        for entry in entries:
            if hasattr(entry, "runtime_data") and entry.runtime_data:
                return entry.runtime_data.api
        return None

    async def handle_create_task(call: ServiceCall) -> None:
        """Handle create_task service call."""
        api = _get_api(hass)
        if api is None:
            _LOGGER.error("No Super Productivity connection available")
            return

        task_data: dict = {"title": call.data[ATTR_TITLE]}
        if ATTR_PROJECT_ID in call.data:
            task_data["projectId"] = call.data[ATTR_PROJECT_ID]
        if ATTR_TAG_IDS in call.data:
            task_data["tagIds"] = call.data[ATTR_TAG_IDS]
        if ATTR_NOTES in call.data:
            task_data["notes"] = call.data[ATTR_NOTES]
        if ATTR_TIME_ESTIMATE in call.data:
            task_data["timeEstimate"] = call.data[ATTR_TIME_ESTIMATE]
        if ATTR_DUE_DAY in call.data:
            task_data["dueDay"] = call.data[ATTR_DUE_DAY]
        if ATTR_PARENT_ID in call.data:
            task_data["parentId"] = call.data[ATTR_PARENT_ID]

        await api.async_create_task(task_data)

        # Refresh coordinator data
        for entry in hass.config_entries.async_entries(DOMAIN):
            if hasattr(entry, "runtime_data") and entry.runtime_data:
                await entry.runtime_data.async_request_refresh()

    async def handle_start_task(call: ServiceCall) -> None:
        """Handle start_task service call."""
        api = _get_api(hass)
        if api is None:
            _LOGGER.error("No Super Productivity connection available")
            return

        await api.async_start_task(call.data[ATTR_TASK_ID])

        for entry in hass.config_entries.async_entries(DOMAIN):
            if hasattr(entry, "runtime_data") and entry.runtime_data:
                await entry.runtime_data.async_request_refresh()

    async def handle_stop_task(call: ServiceCall) -> None:
        """Handle stop_task service call."""
        api = _get_api(hass)
        if api is None:
            _LOGGER.error("No Super Productivity connection available")
            return

        await api.async_stop_current_task()

        for entry in hass.config_entries.async_entries(DOMAIN):
            if hasattr(entry, "runtime_data") and entry.runtime_data:
                await entry.runtime_data.async_request_refresh()

    async def handle_complete_task(call: ServiceCall) -> None:
        """Handle complete_task service call."""
        api = _get_api(hass)
        if api is None:
            _LOGGER.error("No Super Productivity connection available")
            return

        await api.async_update_task(call.data[ATTR_TASK_ID], {"isDone": True})

        for entry in hass.config_entries.async_entries(DOMAIN):
            if hasattr(entry, "runtime_data") and entry.runtime_data:
                await entry.runtime_data.async_request_refresh()

    async def handle_archive_task(call: ServiceCall) -> None:
        """Handle archive_task service call."""
        api = _get_api(hass)
        if api is None:
            _LOGGER.error("No Super Productivity connection available")
            return

        await api.async_archive_task(call.data[ATTR_TASK_ID])

        for entry in hass.config_entries.async_entries(DOMAIN):
            if hasattr(entry, "runtime_data") and entry.runtime_data:
                await entry.runtime_data.async_request_refresh()

    # Only register services once
    if hass.services.has_service(DOMAIN, "create_task"):
        return

    hass.services.async_register(
        DOMAIN,
        "create_task",
        handle_create_task,
        schema=vol.Schema(
            {
                vol.Required(ATTR_TITLE): str,
                vol.Optional(ATTR_PROJECT_ID): str,
                vol.Optional(ATTR_TAG_IDS): vol.All(
                    vol.Coerce(list), [str]
                ),
                vol.Optional(ATTR_NOTES): str,
                vol.Optional(ATTR_TIME_ESTIMATE): int,
                vol.Optional(ATTR_DUE_DAY): str,
                vol.Optional(ATTR_PARENT_ID): str,
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        "start_task",
        handle_start_task,
        schema=vol.Schema({vol.Required(ATTR_TASK_ID): str}),
    )

    hass.services.async_register(
        DOMAIN,
        "stop_task",
        handle_stop_task,
        schema=vol.Schema({}),
    )

    hass.services.async_register(
        DOMAIN,
        "complete_task",
        handle_complete_task,
        schema=vol.Schema({vol.Required(ATTR_TASK_ID): str}),
    )

    hass.services.async_register(
        DOMAIN,
        "archive_task",
        handle_archive_task,
        schema=vol.Schema({vol.Required(ATTR_TASK_ID): str}),
    )
