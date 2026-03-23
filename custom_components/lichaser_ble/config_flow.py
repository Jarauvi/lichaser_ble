"""Config flow for Lichaser BLE integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import bluetooth as bt
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_KEEP_CONNECTED,
    CONF_MAC,
    CONF_NAME,
    DEFAULT_KEEP_CONNECTED,
    DEFAULT_NAME,
    DOMAIN,
    SUPPORTED_DEVICES
)

_LOGGER = logging.getLogger(__name__)

class LichaserFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lichaser BLE."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> LichaserOptionsFlowHandler:
        """Return the options flow handler."""
        return LichaserOptionsFlowHandler(config_entry)

async def async_step_user(self, user_input=None):
    """Handle the initial setup flow with autodiscovery."""
    if user_input is not None:
        mac = user_input[CONF_MAC]
        await self.async_set_unique_id(mac)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=user_input.get(CONF_NAME, DEFAULT_NAME),
            data={
                CONF_MAC: mac,
                CONF_NAME: user_input.get(CONF_NAME, DEFAULT_NAME)
            }
        )

    # Look for Lichaser devices currently in range
    discovered_devices = []
    for service_info in bt.async_discovered_service_info(self.hass):
        # Normalize all discovered UUIDs to lowercase for comparison
        advertised_uuids = [u.lower() for u in service_info.service_uuids]
        
        # Check if any of our supported UUIDs are present in the advertisement
        for supported_uuid in SUPPORTED_DEVICES:
            if supported_uuid.lower() in advertised_uuids:
                discovered_devices.append(service_info)
                break 

    # When creating the list for the user to see:
    available = [
        (info.address, f"{info.name or SUPPORTED_DEVICES.get(supported_uuid)} ({info.address})")
        for info in discovered_devices
    ]

    # Mo devices found: allow manual entry
    if not available:
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_MAC): str,
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str
            }),
            errors={"base": "no_devices_found"}
        )

    # Show the Combobox
    options = {mac: name for mac, name in available}
    return self.async_show_form(
        step_id="user",
        data_schema=vol.Schema({
            vol.Required(CONF_MAC): vol.In(options),
            vol.Optional(CONF_NAME, default=DEFAULT_NAME): str
        })
    )

class LichaserOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle changes to integration settings after installation."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the configuration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Current value from entry options or default if never set
        keep_connected = self.config_entry.options.get(
            CONF_KEEP_CONNECTED, DEFAULT_KEEP_CONNECTED
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_KEEP_CONNECTED, 
                    default=keep_connected
                ): bool,
            })
        )