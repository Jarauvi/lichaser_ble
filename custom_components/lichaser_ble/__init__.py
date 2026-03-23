"""Initial setup and integration management for Lichaser BLE."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .bluetooth import LichaserBluetooth
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.LIGHT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Lichaser BLE from a config entry."""
    mac = entry.data["mac"]

    client = LichaserBluetooth(hass, mac, entry)

    # Test connection during setup
    try:
        await client.async_test_connection()
    except Exception as err:
        _LOGGER.warning(
            "Failed to connect to Lichaser device %s: %s", mac, err
        )
        raise ConfigEntryNotReady(
            f"Could not connect to device at {mac}"
        ) from err

    entry.runtime_data = client

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    client: LichaserBluetooth = entry.runtime_data

    await client.disconnect()

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> bool:
    """Handle configuration migrations."""
    return True