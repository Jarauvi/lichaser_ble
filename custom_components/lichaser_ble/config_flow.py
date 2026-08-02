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

    def __init__(self) -> None:
        """Initialize the flow."""
        self._discovered_device: bt.BluetoothServiceInfoBleak | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> LichaserOptionsFlowHandler:
        """Return the options flow handler."""
        return LichaserOptionsFlowHandler()
    
    async def async_step_bluetooth(self, discovery_info: bt.BluetoothServiceInfoBleak) -> FlowResult:
        """Handle discovery via Bluetooth."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        self._discovered_device = discovery_info
        
        self.context["title_placeholders"] = {
            "name": discovery_info.name or "Lichaser Light"
        }
        
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Confirm discovery without asking for a name."""
        if user_input is not None:
            # Use the broadcast name (e.g. IOTBT6D7) as the default title
            return self.async_create_entry(
                title=self._discovered_device.name or "Lichaser Light",
                data={
                    CONF_MAC: self._discovered_device.address,
                },
            )

        # Show a simple "Do you want to add this device?" form with no fields
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={
                "name": self._discovered_device.name or "Lichaser Light"
            }
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the manual 'Add Integration' flow."""
        if user_input is not None:
            mac = user_input[CONF_MAC]
            await self.async_set_unique_id(mac)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input.get(CONF_NAME, DEFAULT_NAME),
                data={CONF_MAC: mac, CONF_NAME: user_input.get(CONF_NAME, DEFAULT_NAME)}
            )

        # Include Manufacturer ID 23042 (0x5a02)
        discovered_devices = []
        for info in bt.async_discovered_service_info(self.hass):
            # Match by UUID OR by the Manufacturer ID found in bluetoothctl
            has_uuid = any(u.lower() in SUPPORTED_DEVICES for u in info.service_uuids)
            has_manu = 23042 in info.manufacturer_data 
            
            if has_uuid or has_manu:
                discovered_devices.append(info)

        if not discovered_devices:
            # Fallback to manual MAC entry if scanning fails
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Required(CONF_MAC): str,
                    vol.Optional(CONF_NAME, default=DEFAULT_NAME): str
                }),
                errors={"base": "no_devices_found"}
            )

        # Show the dropdown list
        options = {info.address: f"{info.name or 'Lichaser'} ({info.address})" for info in discovered_devices}
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