import asyncio
import logging
from bleak import BleakClient
from bleak_retry_connector import establish_connection
from bleak.exc import BleakError

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from pathlib import Path

from .const import CONF_EFFECTS_FILE, CONF_KEEP_CONNECTED, DEFAULT_EFFECTS_FILE, DEFAULT_KEEP_CONNECTED
from .led_strip import LedStrip  # Import your helper here

_LOGGER = logging.getLogger(__name__)

class LichaserBluetooth:
    def __init__(self, hass: HomeAssistant, mac: str, entry):
        self.hass = hass
        self.mac = mac
        self.entry = entry
        self._lock = asyncio.Lock()
        self._client: BleakClient | None = None
        self._write_char: str | None = None
        self._disconnect_timer: asyncio.TimerHandle | None = None
        self._effect_task: asyncio.Task | None = None

        self.strip = LedStrip()
        self.is_on = False

    @property
    def keep_connected(self) -> bool:
        return self.entry.options.get(CONF_KEEP_CONNECTED, DEFAULT_KEEP_CONNECTED)

    def load_effects(self) -> None:
        """Load custom effect patterns from a JSON file in the Home Assistant config dir."""
        effect_file = self.entry.options.get(CONF_EFFECTS_FILE, DEFAULT_EFFECTS_FILE)
        if not effect_file:
            return

        effect_path = Path(effect_file)
        if not effect_path.is_absolute():
            effect_path = Path(self.hass.config.path(effect_file))

        self.strip.load_effects_from_file(effect_path)

    async def _ensure_characteristics(self, client: BleakClient):
        if self._write_char is not None:
            return

        for service in client.services:
            for char in service.characteristics:
                uuid = char.uuid.lower()
                if "write" in char.properties or "write-without-response" in char.properties:
                    if any(x in uuid for x in ["ff01", "5a02", "ae01"]):
                        self._write_char = char.uuid
                        _LOGGER.info("Found Lichaser write char: %s", self._write_char)
                        return

        if not self._write_char:
            raise BleakError("No writable characteristic found")

    async def _get_client(self) -> BleakClient:
        if self._client and self._client.is_connected:
            return self._client

        device = bluetooth.async_ble_device_from_address(self.hass, self.mac, connectable=True)
        if not device:
            raise Exception(f"Device {self.mac} not found in range")

        self._client = await establish_connection(
            BleakClient, device, self.mac, disconnected_callback=self._on_disconnect
        )
        
        await self._ensure_characteristics(self._client)
        return self._client

    def _on_disconnect(self, client: BleakClient):
        _LOGGER.debug("Lichaser %s disconnected", self.mac)
        self._client = None
        self._write_char = None


    async def _send_packet(self) -> None:
        """Generate and send the current packet to the device."""
        packet = self.strip.generate_packet(0x0c)
        await self.send_command(packet)

    async def send_command(self, packet: bytes):
        """Send a raw packet to the hardware."""
        async with self._lock:
            if self._disconnect_timer:
                self._disconnect_timer.cancel()
                self._disconnect_timer = None

            try:
                client = await self._get_client()
                # Use write_without_response if supported for better speed
                await client.write_gatt_char(self._write_char, packet, response=False)
            except Exception as err:
                _LOGGER.error("Error sending to Lichaser %s: %s", self.mac, err)
                raise
            finally:
                if not self.keep_connected:
                    self._disconnect_timer = self.hass.loop.call_later(
                        10, lambda: asyncio.create_task(self.disconnect())
                    )

    async def async_update(self):
        """Kirjautumistesti laitteelle asennuksen tai käynnistyksen yhteydessä."""
        async with self._lock:
            await self._get_client()
            if not self.keep_connected:
                await self.disconnect()

    async def update_state(self, r=None, g=None, b=None, br=None, eff=None, turn_on=None):
        # Update memory
        if r is not None: self.strip.r = r
        if g is not None: self.strip.g = g
        if b is not None: self.strip.b = b
        if br is not None: self.strip.br = br
        if eff is not None: self.strip.eff = eff
        if turn_on is not None: self.is_on = turn_on

        # Capture the 'real' brightness
        display_br = self.strip.br
        
        packet_br = display_br if self.is_on else 0
        
        # Temporarily swap for packet generation
        self.strip.br = packet_br
        await self._send_packet()
        
        # Swap back so memory stays correct
        self.strip.br = display_br

    async def disconnect(self):
        if self._client and self._client.is_connected:
            await self._client.disconnect()
        self._client = None