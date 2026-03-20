import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.components import bluetooth

from .const import (
    DOMAIN,
    CONF_MAC,
    CONF_NAME,
    DEFAULT_NAME,
    SERVICE_UUID
)

_LOGGER = logging.getLogger(__name__)

class LichaserFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Lichaser BLE integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Show list of discovered Lichaser devices to user."""

        # Step 1: get all discovered BLE devices
        discovered_devices = []
        for service_info in bluetooth.async_discovered_service_info(self.hass):
            # Check if this service_info advertises our Lichaser service UUID
            if SERVICE_UUID.lower() in [uuid.lower() for uuid in service_info.service_uuids]:
                discovered_devices.append(service_info.device)

        # Step 2: filter out already configured devices
        configured_macs = [entry.data[CONF_MAC] for entry in self._async_current_entries()]
        available_devices = [
            (dev.address, dev.name or DEFAULT_NAME)
            for dev in discovered_devices
            if dev.address not in configured_macs
        ]

        # Step 3: fallback if nothing found
        if not available_devices:
            return self.async_show_form(
                step_id="manual",
                data_schema=vol.Schema({
                    vol.Required(CONF_MAC): str,
                    vol.Optional(CONF_NAME, default=DEFAULT_NAME): str
                }),
                description_placeholders={"hint": self.hass.config.translation_string("config.user.step.manual.description.hint")}
            )

        # Step 4: show dropdown of available devices
        options = {mac: name for mac, name in available_devices}
        data_schema = vol.Schema({
            vol.Required(CONF_MAC): vol.In(options),
            vol.Optional(CONF_NAME, default=DEFAULT_NAME): str
        })

        if user_input is not None:
            # User selected a MAC from dropdown
            return self.async_create_entry(
                title=user_input.get(CONF_NAME, DEFAULT_NAME),
                data={
                    CONF_MAC: user_input[CONF_MAC],
                    CONF_NAME: user_input.get(CONF_NAME, DEFAULT_NAME)
                }
            )

        return self.async_show_form(step_id="user", data_schema=data_schema)

class LichaserOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow for Lichaser LED integration."""
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage optional settings (future expansion: e.g., effects)."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional("default_effect", default="None"): str
            })
        )