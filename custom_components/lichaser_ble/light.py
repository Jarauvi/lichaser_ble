"""Light platform for Lichaser BLE."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, CONF_NAME
from .led_strip import LedStrip

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    client = config_entry.runtime_data
    name = config_entry.data.get(CONF_NAME, "Lichaser Light")

    async_add_entities([LichaserLight(client, name)])


class LichaserLight(LightEntity, RestoreEntity):
    """Representation of a Lichaser BLE Light Strip."""

    _attr_has_entity_name = True
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_assumed_state = True  # 🔥 critical for BLE devices

    def __init__(self, bt, name: str) -> None:
        self._bt = bt
        self._attr_unique_id = f"{bt.mac}_light"
        self._attr_name = name

        # 🔥 SINGLE SOURCE OF TRUTH
        self._attr_is_on = False
        self._attr_brightness = 255
        self._attr_rgb_color = (255, 255, 255)
        self._attr_effect = "None"

        # Packet builder helper
        self._strip = LedStrip()

    @property
    def available(self) -> bool:
        return True

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._bt.mac)},
            name=self._attr_name,
            manufacturer="Lichaser",
            model="BLE LED Strip Controller",
            connections={("bluetooth", self._bt.mac)},
        )

    async def async_added_to_hass(self) -> None:
        """Restore state after restart."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()

        if last_state:
            _LOGGER.debug("Restoring state: %s", last_state)

            self._attr_is_on = last_state.state == "on"

            self._attr_brightness = last_state.attributes.get(
                ATTR_BRIGHTNESS, 255
            )

            rgb = last_state.attributes.get(ATTR_RGB_COLOR)
            if rgb:
                self._attr_rgb_color = tuple(rgb)

            self._attr_effect = last_state.attributes.get(
                ATTR_EFFECT, "None"
            )

        # Sync internal strip helper
        self._sync_strip()

        # If light should be ON → push state to device
        if self._attr_is_on:
            self.hass.async_create_task(self._apply_state())

        self.async_write_ha_state()

    def _sync_strip(self):
        """Copy entity state → packet builder."""
        r, g, b = self._attr_rgb_color

        self._strip.r = r
        self._strip.g = g
        self._strip.b = b
        self._strip.br = self._attr_brightness or 0
        self._strip.eff = self._attr_effect or "None"

    async def _apply_state(self):
        """Send current state to device."""
        self._sync_strip()

        # Handle OFF by forcing brightness to 0
        real_br = self._strip.br
        if not self._attr_is_on:
            self._strip.br = 0

        try:
            packet = self._strip.generate_packet(0x0C)
            await self._bt.send_command(packet)
        except Exception as err:
            _LOGGER.error("Failed to send command: %s", err)
        finally:
            self._strip.br = real_br

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on or change settings."""
        if ATTR_BRIGHTNESS in kwargs:
            self._attr_brightness = kwargs[ATTR_BRIGHTNESS]

        if ATTR_RGB_COLOR in kwargs:
            self._attr_rgb_color = kwargs[ATTR_RGB_COLOR]
            self._attr_effect = "None"

        if ATTR_EFFECT in kwargs:
            self._attr_effect = kwargs[ATTR_EFFECT]

        self._attr_is_on = True

        await self._apply_state()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        self._attr_is_on = False

        await self._apply_state()
        self.async_write_ha_state()