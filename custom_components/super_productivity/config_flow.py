"""Config flow for Super Productivity integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .api import (
    SuperProductivityApi,
    SuperProductivityConnectionError,
)
from .const import (
    CONF_HOST,
    CONF_PORT,
    DEFAULT_HOST,
    DEFAULT_PORT,
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

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            # Set unique ID based on host:port to prevent duplicates
            await self.async_set_unique_id(f"{host}:{port}")
            self._abort_if_unique_id_configured()

            # Validate connection
            from aiohttp import ClientSession

            session = ClientSession()
            api = SuperProductivityApi(session, host, port)
            try:
                health = await api.async_health_check()
                if not health.get("rendererReady"):
                    errors["base"] = "app_not_ready"
                else:
                    await session.close()
                    return self.async_create_entry(
                        title=f"Super Productivity ({host}:{port})",
                        data=user_input,
                    )
            except SuperProductivityConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception during config flow")
                errors["base"] = "unknown"
            finally:
                await session.close()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
