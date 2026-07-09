"""Config flow for Super Productivity integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    SuperProductivityApi,
    SuperProductivityConnectionError,
)
from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    }
)


class SuperProductivityConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Super Productivity."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow handler."""
        return SuperProductivityOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            # Set unique ID based on host:port to prevent duplicates
            await self.async_set_unique_id(f"{host}:{port}")
            self._abort_if_unique_id_configured()

            # Try to validate connection, but don't block setup if it fails
            session = async_get_clientsession(self.hass)
            api = SuperProductivityApi(session, host, port)
            try:
                await api.async_health_check()
                _LOGGER.info("Successfully connected to Super Productivity at %s:%s", host, port)
            except SuperProductivityConnectionError:
                _LOGGER.warning(
                    "Could not connect to Super Productivity at %s:%s during setup. "
                    "The integration will retry when the app becomes available.",
                    host, port
                )
            except Exception:
                _LOGGER.warning(
                    "Unexpected error connecting to Super Productivity at %s:%s during setup. "
                    "The integration will retry when the app becomes available.",
                    host, port
                )

            # Always create the entry - coordinator will handle retries
            return self.async_create_entry(
                title=f"Super Productivity ({host}:{port})",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
        )


class SuperProductivityOptionsFlow(OptionsFlow):
    """Handle options for Super Productivity."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Update the config entry data with new host/port
            new_data = dict(self._config_entry.data)
            new_data[CONF_HOST] = user_input[CONF_HOST]
            new_data[CONF_PORT] = user_input[CONF_PORT]
            self.hass.config_entries.async_update_entry(
                self._config_entry,
                data=new_data,
                title=f"Super Productivity ({user_input[CONF_HOST]}:{user_input[CONF_PORT]})",
            )
            return self.async_create_entry(
                title="",
                data={CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL]},
            )

        # Show form with current values
        current_host = self._config_entry.data.get(CONF_HOST, DEFAULT_HOST)
        current_port = self._config_entry.data.get(CONF_PORT, DEFAULT_PORT)
        current_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=current_host): str,
                    vol.Required(CONF_PORT, default=current_port): int,
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=current_interval
                    ): vol.All(int, vol.Range(min=5, max=300)),
                }
            ),
        )
