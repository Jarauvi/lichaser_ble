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
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import CONF_NAME
from .led_strip import LedStrip

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Lichaser light platform."""
    # Retrieve the client we stored in runtime_data during __init__.py
    client = config_entry.runtime_data
    name = config_entry.data.get(CONF_NAME, "Lichaser Light")

    async_add_entities([LichaserLight(client, name, config_entry.entry_id)])


class LichaserLight(LightEntity, RestoreEntity):
    """Representation of a Lichaser BLE Light Strip."""

    # Define what this light can actually do
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_color_mode = ColorMode.RGB
    _attr_has_entity_name = True

    def __init__(self, bt, name: str, entry_id: str) -> None:
        """Initialize the light."""
        self._bt = bt
        self._attr_name = name
        self._attr_unique_id = f"{entry_id}_light"
        self.strip = LedStrip()
        
        # Initial state setup
        self._attr_is_on = False
        self._attr_brightness = 255
        self._attr_rgb_color = (255, 255, 255)
        self._attr_effect = "None"

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added to hass."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        
        if last_state:
            # Restore Brightness (0-255)
            if (br := last_state.attributes.get(ATTR_BRIGHTNESS)) is not None:
                self.strip.br = br
                self._attr_brightness = br

            # Restore RGB
            if (rgb := last_state.attributes.get(ATTR_RGB_COLOR)) is not None:
                self.strip.r, self.strip.g, self.strip.b = rgb
                self._attr_rgb_color = rgb

            # Restore Effect
            if (eff := last_state.attributes.get(ATTR_EFFECT)) is not None:
                self.strip.eff = eff
                self._attr_effect = eff

            self._attr_is_on = last_state.state == "on"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on or change settings."""
        if ATTR_BRIGHTNESS in kwargs:
            self._attr_brightness = kwargs[ATTR_BRIGHTNESS]
            self.strip.br = self._attr_brightness

        if ATTR_RGB_COLOR in kwargs:
            self._attr_rgb_color = kwargs[ATTR_RGB_COLOR]
            self.strip.r, self.strip.g, self.strip.b = self._attr_rgb_color
            self.strip.eff = "None"

        if ATTR_EFFECT in kwargs:
            self._attr_effect = kwargs[ATTR_EFFECT]
            self.strip.eff = self._attr_effect

        self._attr_is_on = True
        await self._apply_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        self._attr_is_on = False
        temp_br = self.strip.br
        self.strip.br = 0
        await self._apply_state()
        self.strip.br = temp_br

    async def _apply_state(self) -> None:
        """Transmit state to hardware and update HA."""
        packet = self.strip.generate_packet(0x0C)
        await self._bt.send(packet)
        self.async_write_ha_state()