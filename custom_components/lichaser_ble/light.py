"""Light platform for Lichaser BLE."""
from __future__ import annotations
import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util.color import color_hs_to_RGB, color_RGB_to_hs

from .const import DOMAIN, CONF_NAME

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    client = config_entry.runtime_data
    async_add_entities([LichaserLight(client)])

class LichaserLight(LightEntity, RestoreEntity):
    _attr_has_entity_name = True
    _attr_color_mode = ColorMode.HS
    _attr_supported_color_modes = {ColorMode.HS, ColorMode.RGB}
    _attr_supported_features = LightEntityFeature.EFFECT

    def __init__(self, bt):
        self._bt = bt
        self._attr_unique_id = f"{bt.mac}_light"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._bt.mac)},
            name=self._bt.entry.data.get(CONF_NAME, "Lichaser Light"),
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        # Check both the internal attribute and the bluetooth state
        return self._bt.is_on
    
    @property
    def brightness(self) -> int: return self._bt.strip.br

    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return the current color as Home Assistant HS values."""
        return color_RGB_to_hs(*self.rgb_color)

    @property
    def rgb_color(self) -> tuple[int, int, int]:
        return (self._bt.strip.r, self._bt.strip.g, self._bt.strip.b)

    async def async_added_to_hass(self) -> None:
        """Handle entity restoration with safety defaults."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()

        # 1. Default fallback values
        br = 255
        rgb = (255, 255, 255)
        eff = "None"
        is_on = False

        if last_state:
            _LOGGER.debug("Restoring state for %s", self.unique_id)

            br = last_state.attributes.get(ATTR_BRIGHTNESS, 255)
            eff = last_state.attributes.get(ATTR_EFFECT, "None")
            is_on = last_state.state == "on"

            restored_hs = last_state.attributes.get(ATTR_HS_COLOR)
            if isinstance(restored_hs, (list, tuple)) and len(restored_hs) == 2:
                rgb = color_hs_to_RGB(*restored_hs)
            else:
                restored_rgb = last_state.attributes.get(ATTR_RGB_COLOR)
                if isinstance(restored_rgb, (list, tuple)) and len(restored_rgb) == 3:
                    rgb = restored_rgb

        # 2. Seed the Bluetooth coordinator
        self._bt.is_on = is_on
        self._bt.strip.br = br
        self._bt.strip.r, self._bt.strip.g, self._bt.strip.b = rgb
        self._bt.strip.eff = eff

        # 3. Set the local entity attributes for the UI
        self._attr_is_on = is_on
        self._attr_brightness = br
        self._attr_rgb_color = rgb
        self._attr_hs_color = color_RGB_to_hs(*rgb)
        self._attr_effect = eff

        # Update HA internal state so the UI reflects restored values immediately
        self.async_write_ha_state()

        # 4. If the light was ON, trigger a background sync to the hardware
        if is_on:
            self.hass.async_create_task(
                self._bt.update_state(
                    r=rgb[0],
                    g=rgb[1],
                    b=rgb[2],
                    br=br,
                    eff=eff,
                    turn_on=True,
                )
            )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        rgb = kwargs.get(ATTR_RGB_COLOR)
        hs_color = kwargs.get(ATTR_HS_COLOR)
        br = kwargs.get(ATTR_BRIGHTNESS)
        eff = kwargs.get(ATTR_EFFECT)

        if hs_color is not None:
            rgb = color_hs_to_RGB(*hs_color)

        # If color wasn't picked, None is passed to update_state
        # so it keeps the current memory values.
        r, g, b = rgb if rgb is not None else (None, None, None)

        await self._bt.update_state(r=r, g=g, b=b, br=br, eff=eff, turn_on=True)

        # Sync attributes
        self._attr_is_on = True
        if br is not None:
            self._attr_brightness = br
        if rgb is not None:
            self._attr_rgb_color = rgb
            self._attr_hs_color = color_RGB_to_hs(*rgb)
        if eff is not None:
            self._attr_effect = eff

        _LOGGER.info("Sending values: %s, %s, %s", r, g, b)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the light off."""
        # 1. Tell bluetooth to go to 'Off' state (which sends brightness 0)
        await self._bt.update_state(turn_on=False)
        
        # 2. Update local state
        self._attr_is_on = False
        
        self.async_write_ha_state()