from homeassistant.components.light import LightEntity
from homeassistant.helpers.restore_state import RestoreEntity
from .bluetooth import LichaserBluetooth
from .led_strip import LedStrip  # your existing packet generator

class LichaserLight(LightEntity, RestoreEntity):
    """Home Assistant light entity for Lichaser LED strip."""

    def __init__(self, bt: LichaserBluetooth, name: str):
        self._bt = bt
        self._attr_name = name
        self.strip = LedStrip()
        self._attr_is_on = self.strip.br > 0

    async def async_added_to_hass(self):
        """Restore previous state when entity is added to HA."""
        last_state = await self.async_get_last_state()
        if last_state is None:
            return
        
        # Restore brightness
        if last_state.attributes.get("brightness") is not None:
            self.strip.br = last_state.attributes["brightness"]

        # Restore color
        rgb = last_state.attributes.get("rgb_color")
        if rgb:
            self.strip.r, self.strip.g, self.strip.b = rgb

        # Restore effect
        effect = last_state.attributes.get("effect")
        if effect:
            self.strip.eff = effect

        self._attr_is_on = self.strip.br > 0
        await self._apply_state()

    async def async_turn_on(self, **kwargs):
        self.strip.br = kwargs.get("brightness", self.strip.br or 255)
        rgb = kwargs.get("rgb_color")
        if rgb:
            self.strip.r, self.strip.g, self.strip.b = rgb
            self.strip.eff = "None"
        effect = kwargs.get("effect")
        if effect:
            self.strip.eff = effect

        await self._apply_state()

    async def async_turn_off(self, **kwargs):
        self.strip.br = 0
        await self._apply_state()

    async def _apply_state(self):
        packet = self.strip.generate_packet(0x0C)
        await self._bt.send_packet(packet)
        self._attr_is_on = self.strip.br > 0
        self._attr_brightness = self.strip.br
        self._attr_rgb_color = (self.strip.r, self.strip.g, self.strip.b)
        self._attr_effect = self.strip.eff
        self.async_write_ha_state()