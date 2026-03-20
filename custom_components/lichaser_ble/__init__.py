import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .bluetooth import LichaserBluetooth

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["light"]

hass.data[DOMAIN][entry.entry_id] = {
    "bt": bt,
    "name": entry.data.get("name"),
}

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Lichaser BLE from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    mac = entry.data["mac"]

    # Create Bluetooth handler
    bt = LichaserBluetooth(hass, mac)

    # Store runtime data
    hass.data[DOMAIN][entry.entry_id] = {
        "bt": bt,
    }

    # Forward setup to light platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

# Placeholder for migrations
async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    return True