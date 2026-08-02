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
    
    # 1. Initialize the Bluetooth handler
    client = LichaserBluetooth(hass, mac, entry)

    client.load_effects()

    # 2. Verify device availability
    try:
        await client.async_update() 
    except Exception as err:
        raise ConfigEntryNotReady(
            f"Could not connect to Lichaser device at {mac}: {err}"
        ) from err

    # 3. Store the client for platform use
    entry.runtime_data = client

    # 4. Forward the setup to the light platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms (light, etc.) and return the status
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Handle configuration migrations if the data schema changes in the future."""
    return True