import asyncio
import logging
from bleak import BleakClient
from bleak_retry_connector import establish_connection
from bleak.exc import BleakError

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_KEEP_CONNECTED

_LOGGER = logging.getLogger(__name__)


class LichaserBluetooth:
    def __init__(self, hass: HomeAssistant, mac: str, entry):
        self.hass = hass
        self.mac = mac
        self.entry = entry

        self._lock = asyncio.Lock()
        self._client: BleakClient | None = None
        self._write_char: str | None = None
        self._write_with_response: bool = False
        self._disconnect_timer: asyncio.TimerHandle | None = None
        self._initialized: bool = False  # handshake tracking

    @property
    def keep_connected(self) -> bool:
        return self.entry.options.get(CONF_KEEP_CONNECTED, False)

    async def disconnect(self):
        """Safely disconnect from device."""
        async with self._lock:
            if self._client and self._client.is_connected:
                try:
                    await self._client.disconnect()
                except Exception as err:
                    _LOGGER.debug("Error during disconnect: %s", err)

            self._client = None
            self._write_char = None
            self._initialized = False

    async def _setup_device(self, client: BleakClient):
        """Run initialization handshake."""
        _LOGGER.debug("Running initialization handshake")

        await client.write_gatt_char(
            self._write_char, bytearray([0x01, 0x00]), response=True
        )

        handshake_packets = [
            "00018000000c0d0a1014190c1d140c3301000fc9",
            "000280000005060aea818a8b59",
            "000380000002030aea81",
        ]

        for p_hex in handshake_packets:
            await client.write_gatt_char(
                self._write_char, bytearray.fromhex(p_hex), response=True
            )

    async def _ensure_characteristics(self, client: BleakClient):
        """Find writable characteristic."""
        if self._write_char is not None:
            return

        await client.get_services()  # ensure services resolved

        for service in client.services:
            for char in service.characteristics:
                uuid = char.uuid.lower()

                if "write" in char.properties or "write-without-response" in char.properties:
                    if any(x in uuid for x in ["ff01", "5a02", "ae01"]):
                        self._write_char = char.uuid
                        self._write_with_response = "write" in char.properties

                        _LOGGER.info(
                            "Found write char: %s (response=%s)",
                            self._write_char,
                            self._write_with_response,
                        )
                        return

        raise BleakError("No writable characteristic found")

    async def _get_client(self) -> BleakClient:
        """Ensure connected client."""
        if self._client and self._client.is_connected:
            return self._client

        device = bluetooth.async_ble_device_from_address(
            self.hass, self.mac, connectable=True
        )
        if not device:
            raise HomeAssistantError(f"Device {self.mac} not found")

        self._client = await establish_connection(
            BleakClient,
            device,
            self.mac,
            disconnected_callback=self._on_disconnect,
        )

        await self._ensure_characteristics(self._client)

        # Run handshake only once per connection lifecycle
        if not self._initialized:
            await self._setup_device(self._client)
            self._initialized = True

        return self._client

    def _on_disconnect(self, client: BleakClient):
        _LOGGER.debug("Device %s disconnected", self.mac)
        self._client = None
        self._write_char = None
        self._initialized = False

    async def send_command(self, packet: bytes):
        """Send raw packet to device."""
        async with self._lock:
            # Cancel pending disconnect
            if self._disconnect_timer:
                self._disconnect_timer.cancel()
                self._disconnect_timer = None

            try:
                client = await self._get_client()

                await client.write_gatt_char(
                    self._write_char,
                    packet,
                    response=self._write_with_response,
                )

            except Exception as err:
                _LOGGER.error("Send failed for %s: %s", self.mac, err)
                raise

            finally:
                if not self.keep_connected:
                    self._disconnect_timer = self.hass.loop.call_later(
                        10,
                        lambda: asyncio.create_task(self.disconnect()),
                    )