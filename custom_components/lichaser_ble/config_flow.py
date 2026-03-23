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
    SUPPORTED_DEVICES,
)

_LOGGER = logging.getLogger(__name__)

LICHASER_MANUFACTURER_ID = 23042
DEFAULT_TITLE = "Lichaser Light"


class LichaserFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lichaser BLE."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered_device: bt.BluetoothServiceInfoBleak | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return LichaserOptionsFlowHandler()

    async def async_step_bluetooth(
        self, discovery_info: bt.BluetoothServiceInfoBleak
    ) -> FlowResult:
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        self._discovered_device = discovery_info

        name = discovery_info.name or DEFAULT_TITLE

        self.context["title_placeholders"] = {"name": name}

        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            name = (
                self._discovered_device.name
                if self._discovered_device and self._discovered_device.name
                else DEFAULT_TITLE
            )

            return self.async_create_entry(
                title=name,
                data={
                    CONF_MAC: self._discovered_device.address,
                    CONF_NAME: name,
                },
            )

        name = (
            self._discovered_device.name
            if self._discovered_device and self._discovered_device.name
            else DEFAULT_TITLE
        )

        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": name},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            mac = user_input[CONF_MAC]

            await self.async_set_unique_id(mac)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input.get(CONF_NAME, DEFAULT_NAME),
                data={
                    CONF_MAC: mac,
                    CONF_NAME: user_input.get(CONF_NAME, DEFAULT_NAME),
                },
            )

        discovered_devices = []

        for info in bt.async_discovered_service_info(self.hass):
            uuids = info.service_uuids or []

            has_uuid = any(u.lower() in SUPPORTED_DEVICES for u in uuids)
            has_manu = LICHASER_MANUFACTURER_ID in info.manufacturer_data

            if has_uuid or has_manu:
                discovered_devices.append(info)

        if not discovered_devices:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_MAC): str,
                        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                    }
                ),
                errors={"base": "no_devices_found"},
            )

        # Sort for better UX
        discovered_devices.sort(key=lambda d: d.name or "")

        options = {
            info.address: f"{info.name or DEFAULT_TITLE} ({info.address})"
            for info in discovered_devices
        }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MAC): vol.In(options),
                    vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                }
            ),
        )


class LichaserOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle integration options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        keep_connected = self.config_entry.options.get(
            CONF_KEEP_CONNECTED, DEFAULT_KEEP_CONNECTED
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_KEEP_CONNECTED,
                        default=keep_connected,
                    ): bool,
                }
            ),
        )