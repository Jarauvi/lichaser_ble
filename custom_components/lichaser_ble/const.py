# General parameters
DOMAIN = "lichaser_ble"

SERVICE_UUID = ""

SUPPORTED_DEVICES = {
    "00005a02-0000-1000-8000-00805f9b34fb": "Lichaser led outdoor strip"
}

# Configuration entries
CONF_MAC = "mac"
CONF_NAME = "name"
DEFAULT_NAME = "Lichaser"
DEFAULT_NAME = "Lichaser LED"
CONF_KEEP_CONNECTED = "keep_device_connected"
DEFAULT_KEEP_CONNECTED = True
CONF_EFFECTS_FILE = "effects_file"
DEFAULT_EFFECTS_FILE = "lichaser_ble_effects.json"