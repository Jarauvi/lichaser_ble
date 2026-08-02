<div align="center">
  <img src="https://github.com/Jarauvi/lichaser_ble/raw/main/images/logo_ble.png" alt="Lichaser BLE Logo" width="500">

  # WIP: Lichaser BLE integration for Home Assistant
  
  [![Home Assistant](https://img.shields.io/badge/home%20assistant-%2341BDF5.svg?style=for-the-badge&logo=home-assistant&logoColor=white)](https://www.home-assistant.io/)
  [![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://hacs.xyz/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

  [![Version](https://img.shields.io/github/manifest-json/v/Jarauvi/lichaser_ble?filename=custom_components%2Flichaser_ble%2Fmanifest.json&label=Version)](https://github.com/Jarauvi/lichaser_ble)
  [![Tests](https://github.com/Jarauvi/lichaser_ble/actions/workflows/tests.yaml/badge.svg)](https://github.com/Jarauvi/lichaser_ble/actions)
  ![Cloud Polling](https://img.shields.io/badge/IOT_class-Local_push-blue)

  **Lichaser BLE** is a Home Assistant integration for local control of Lichaser branded Bluetooth LED strips.
  This integration is based on my previous reverse engineering of Lichaser lights. If you need remote mqtt bridge for controlling lights, [check out this repo](https://github.com/Jarauvi/lichaser_led_ble_control)

</div>

---

> [!IMPORTANT]
> **This is a work-in-progress integration.** There is no stable release yet, but maybe soon.

## ✨ Features

* **Zero-Config Discovery:** Automatically detects lights in range using the Home Assistant Bluetooth stack.
* **Local Push:** 100% local control. No internet or external hubs required.
* **Persistent Connection Toggle:** Choose between "Instant Response" (Keep-Alive) or "Resource Friendly" (Disconnect after use) modes.

## To Do
- state is not persistent and it resets when Home Assistant is restarted
- missing tests

## 🚀 Installation

### Option 1: HACS (Recommended)
1.  Open **HACS** in Home Assistant.
2.  Click the three dots in the top right and select **Custom Repositories**.
3.  Paste `https://github.com/Jarauvi/lichaser_ble` and select **Integration** as the category.
4.  Click **Install**.
5.  Restart Home Assistant.

### Option 2: Manual
1.  Download the `lichaser_ble` folder from this repository.
2.  Copy it to your `config/custom_components/` directory.
3.  Restart Home Assistant.

## ⚙️ Configuration

1.  Ensure the core **Bluetooth** integration is enabled in Home Assistant.
2.  Power on your Lichaser LED strip.
3.  Navigate to **Settings > Devices & Services**.
4.  The device should appear automatically as a discovered integration. Click **Configure**.
5.  If not discovered, click **Add Integration** and search for "Lichaser BLE".

---

## 🎨 Custom Effects


> [!IMPORTANT]
> **Currently only static effects are functional.** Dynamic moving effects will be added if possible to reverse engineer them.

The integration supports user-defined effects defined in a JSON file. By default, the file is named `lichaser_ble_effects.json` and is placed in the Home Assistant configuration directory (e.g. `/config/lichaser_ble_effects.json`). The file path can be changed later in the integration options.

### JSON Format

The file contains a JSON object where each **key** is the effect name (as shown in the Home Assistant effect list) and each **value** is the effect definition:

| Property | Type | Default | Description |
| --- | --- | --- | --- |
| `type` | string | `sequence` | Effect type. One of: `sequence`, `static`, `pattern`, `simple`, `blink`, `chase`, `gradient`, `pulse`, `rainbow`, `twinkle` |
| `colors` | array of `[r, g, b]` | — | List of RGB colors (each value `0`–`255`) used by the effect |
| `speed` | number | `1` | Animation speed. Higher values slow the effect down |
| `direction` | string | `forward` | `forward` or `backward` |
| `steps` | number | `20` | Number of steps in the animation cycle |
| `offset` | number | `0` | Start offset for the animation |

As a shorthand, a plain array of colors is also accepted and is treated as a `sequence` effect.

### Example

Place a file named `lichaser_ble_effects.json` in your Home Assistant configuration directory with content like this:

```json
{
  "Dashed Red": {
    "type": "sequence",
    "colors": [
      [255, 0, 0],
      [0, 0, 0]
    ],
    "speed": 1,
    "direction": "forward",
    "steps": 20,
    "offset": 0
  },
  "Sunset Gradient": {
    "type": "gradient",
    "colors": [
      [255, 0, 0],
      [255, 128, 0],
      [255, 255, 0]
    ],
    "speed": 2
  },
  "Ocean Pulse": {
    "type": "pulse",
    "colors": [
      [0, 128, 255]
    ],
    "speed": 3,
    "steps": 30
  },
  "Rainbow": {
    "type": "rainbow",
    "speed": 2
  },
  "Strobe": {
    "type": "blink",
    "colors": [
      [255, 255, 255]
    ],
    "speed": 1
  },
  "Red Chase": {
    "type": "chase",
    "colors": [
      [255, 0, 0],
      [255, 128, 0],
      [255, 255, 0]
    ],
    "speed": 4,
    "direction": "backward"
  },
  "Simple Twinkle": {
    "type": "twinkle",
    "colors": [
      [255, 255, 255],
      [128, 128, 128]
    ],
    "speed": 2,
    "offset": 1
  }
}
```

After adding or changing the file, restart Home Assistant and the new effects will appear in the light's effect list.

---

## ⚠️ Disclaimer
This integration is a community project and is **not** affiliated with, endorsed by, or supported by Lichaser. Use at your own risk. 
