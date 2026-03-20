import asyncio
import logging
from bleak import BleakClient

from homeassistant.components import bluetooth

_LOGGER = logging.getLogger(__name__)

CHAR_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"

class LichaserBluetooth:
    def __init__(self, hass, mac):
        self.hass = hass
        self.mac = mac
        self._lock = asyncio.Lock()

    async def send(self, packet: bytes):
        async with self._lock:
            device = bluetooth.async_ble_device_from_address(
                self.hass, self.mac, connectable=True
            )

            if not device:
                _LOGGER.error("Device not found via HA Bluetooth")
                return

            try:
                async with BleakClient(device) as client:
                    await client.write_gatt_char(
                        CHAR_UUID, bytearray([0x01, 0x00]), response=True
                    )

                    init_packets = [
                        "00018000000c0d0a1014190c1d140c3301000fc9",
                        "000280000005060aea818a8b59",
                        "000380000002030aea81",
                    ]

                    for p in init_packets:
                        await client.write_gatt_char(
                            CHAR_UUID, bytearray.fromhex(p)
                        )

                    await client.write_gatt_char(CHAR_UUID, packet)

            except Exception as e:
                _LOGGER.error("BLE send failed: %s", e)