"""Initial setup and integration management for Lichaser BLE."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .bluetooth import LichaserBluetooth
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Using the Platform enum is the standard for modern integrations
PLATFORMS: list[Platform] = [Platform.LIGHT]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Lichaser BLE from a config entry."""
    mac = entry.data["mac"]
    
    # 1. Initialize the Bluetooth handler
    # We use 'client' to avoid shadowing the 'bluetooth' component imports elsewhere
    client = LichaserBluetooth(hass, mac)

    # 2. Verify device availability
    # This prevents 'Unavailable' entities if the device is out of range during boot
    try:
        await client.async_update() 
    except Exception as err:
        raise ConfigEntryNotReady(
            f"Could not connect to Lichaser device at {mac}: {err}"
        ) from err

    # 3. Store the client for platform use
    # Using runtime_data automatically handles cleanup during unloading
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