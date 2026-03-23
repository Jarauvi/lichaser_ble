import asyncio
import logging
from bleak import BleakClient
from bleak_retry_connector import establish_connection

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import SERVICE_UUID, CONF_KEEP_CONNECTED

_LOGGER = logging.getLogger(__name__)

class LichaserBluetooth:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.entry = entry
        self.mac = entry.data["mac"]
        self._lock = asyncio.Lock()
        self._client: BleakClient | None = None
        self._disconnect_timer: asyncio.TimerHandle | None = None

    @property
    def keep_connected(self) -> bool:
        """Check if the user wants a persistent connection."""
        return self.entry.options.get(CONF_KEEP_CONNECTED, True)

    async def _get_client(self) -> BleakClient:
        """Get a connected client or create one."""
        if self._client and self._client.is_connected:
            return self._client

        device = bluetooth.async_ble_device_from_address(self.hass, self.mac, connectable=True)
        if not device:
            raise Exception(f"Device {self.mac} not found")

        self._client = await establish_connection(
            BleakClient, device, self.mac, disconnected_callback=self._on_disconnect
        )
        
        await self._setup_device(self._client)
        return self._client

    def _on_disconnect(self, client: BleakClient):
        _LOGGER.debug("Lichaser %s disconnected", self.mac)
        self._client = None

    async def _setup_device(self, client: BleakClient):
        """Handshake logic."""
        await client.write_gatt_char(SERVICE_UUID, bytearray([0x01, 0x00]), response=True)
        # ... (your init_packets here)

    async def send(self, packet: bytes):
        """Send command and handle connection lifecycle."""
        async with self._lock:
            # Cancel any pending disconnect since we are active
            if self._disconnect_timer:
                self._disconnect_timer.cancel()
                self._disconnect_timer = None

            try:
                client = await self._get_client()
                await client.write_gatt_char(SERVICE_UUID, packet)
            finally:
                # If persistent connection is OFF, schedule a disconnect
                if not self.keep_connected:
                    # We wait 5s before closing in case another command (like brightness) follows
                    self._disconnect_timer = self.hass.loop.call_later(
                        5, lambda: asyncio.create_task(self.disconnect())
                    )

    async def disconnect(self):
        """Force close the connection."""
        async with self._lock:
            if self._client and self._client.is_connected:
                await self._client.disconnect()
            self._client = None

    async def async_update(self):
        """Initial check for __init__.py."""
        async with self._lock:
            client = await self._get_client()
            if not self.keep_connected:
                await client.disconnect()
                self._client = None