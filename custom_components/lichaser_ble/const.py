# General parameters
DOMAIN = "lichaser_ble"

# Supported BLE UUIDs
SUPPORTED_UUIDS = {
    "00005a02-0000-1000-8000-00805f9b34fb",
}

# Manufacturer ID (for BLE discovery)
LICHASER_MANUFACTURER_ID = 23042

# Configuration entries
CONF_MAC = "mac"
CONF_NAME = "name"

DEFAULT_NAME = "Lichaser LED"

CONF_KEEP_CONNECTED = "keep_device_connected"
DEFAULT_KEEP_CONNECTED = True