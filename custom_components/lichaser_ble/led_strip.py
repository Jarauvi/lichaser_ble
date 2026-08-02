import json
import logging
import math
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

class LedStrip:
    def __init__(self, r=255, g=255, b=255, br=255, eff="None"):
        self.r, self.g, self.b = r, g, b
        self.br = br
        self.eff = eff
        self.num_segments = 20
        self.header_prefix = "80000057580ae1030014000014"
        self.teal = (0x0e, 0xe4, 0x0c)
        self.off = (0x00, 0x00, 0x00)
        self.custom_effects: dict[str, object] = {}
        self._effect_step = 0
        
    def rgb_to_custom_hsv(self, r, g, b):
        """Convert RGB to the custom hue/saturation values used by the device."""
        r_f, g_f, b_f = r / 255.0, g / 255.0, b / 255.0
        max_c, min_c = max(r_f, g_f, b_f), min(r_f, g_f, b_f)
        diff = max_c - min_c

        if diff == 0:
            h = 0
            s = 0
        else:
            if max_c == r_f:
                h = (60 * ((g_f - b_f) / diff) + 360) % 360
            elif max_c == g_f:
                h = (60 * ((b_f - r_f) / diff) + 120)
            else:
                h = (60 * ((r_f - g_f) / diff) + 240)

            s = int(round((diff / max_c) * 100)) if max_c > 0 else 0

        # The device expects the hue in the 0-180 range used by this protocol.
        return int(h / 2), s

    def _coerce_color(self, value: object) -> tuple[int, int, int] | None:
        """Convert a JSON color entry into a normalized RGB tuple."""
        if isinstance(value, (list, tuple)) and len(value) == 3:
            try:
                return tuple(int(item) for item in value)
            except (TypeError, ValueError):
                return None
        return None

    def _normalize_effect(self, name: str, raw_effect: object) -> dict[str, object] | None:
        """Normalize a custom effect definition into a dict with a supported type."""
        if isinstance(raw_effect, list):
            colors = [color for entry in raw_effect if (color := self._coerce_color(entry)) is not None]
            if colors:
                return {
                    "type": "sequence",
                    "colors": colors,
                    "speed": 1,
                    "direction": "forward",
                    "steps": self.num_segments,
                    "offset": 0,
                }
            return None

        if not isinstance(raw_effect, dict):
            return None

        effect_type = raw_effect.get("type", "sequence")
        if not isinstance(effect_type, str):
            effect_type = "sequence"

        colors = []
        for entry in raw_effect.get("colors", []):
            color = self._coerce_color(entry)
            if color is not None:
                colors.append(color)

        if not colors:
            if effect_type == "rainbow":
                colors = [(255, 0, 0)]
            else:
                return None

        return {
            "type": effect_type.lower(),
            "colors": colors,
            "speed": int(raw_effect.get("speed", 1)) if isinstance(raw_effect.get("speed"), (int, float)) else 1,
            "direction": raw_effect.get("direction", "forward"),
            "steps": int(raw_effect.get("steps", self.num_segments)) if isinstance(raw_effect.get("steps"), (int, float)) else self.num_segments,
            "offset": int(raw_effect.get("offset", 0)) if isinstance(raw_effect.get("offset"), (int, float)) else 0,
        }

    def load_effects_from_file(self, path: str | Path | None) -> None:
        """Load user-defined effect patterns from a JSON file."""
        if not path:
            return

        effect_path = Path(path)
        if not effect_path.exists():
            self.custom_effects = {}
            return

        try:
            with effect_path.open("r", encoding="utf-8") as handle:
                raw_effects = json.load(handle)
        except (OSError, json.JSONDecodeError) as err:
            _LOGGER.warning("Unable to load custom effects from %s: %s", effect_path, err)
            self.custom_effects = {}
            return

        if not isinstance(raw_effects, dict):
            self.custom_effects = {}
            return

        parsed_effects: dict[str, object] = {}
        for name, pattern in raw_effects.items():
            if not isinstance(name, str):
                continue

            normalized = self._normalize_effect(name, pattern)
            if normalized:
                parsed_effects[name] = normalized

        self.custom_effects = parsed_effects

    def _build_effect_colors(self, effect: dict[str, object]) -> list[tuple[int, int, int]]:
        """Generate the per-segment colors for a custom effect definition."""
        effect_type = str(effect.get("type", "sequence")).lower()
        colors = effect.get("colors", [])
        if not isinstance(colors, list):
            colors = []

        normalized_colors = [color for color in colors if isinstance(color, tuple)]
        if not normalized_colors:
            normalized_colors = [self.off]

        speed = max(1, int(effect.get("speed", 1)))
        direction = str(effect.get("direction", "forward")).lower()
        steps = max(1, int(effect.get("steps", self.num_segments)))
        offset = int(effect.get("offset", 0))
        frame = self._effect_step // speed

        if effect_type in {"static", "sequence", "pattern", "simple"}:
            return [
                normalized_colors[
                    (
                        (index if direction != "backward" else -index) + offset + frame
                    ) % steps % len(normalized_colors)
                ]
                for index in range(self.num_segments)
            ]

        if effect_type == "blink":
            base = normalized_colors[frame % len(normalized_colors)]
            return [base if ((frame + index) % 2) == 0 else self.off for index in range(self.num_segments)]

        if effect_type == "chase":
            if direction == "backward":
                return [
                    normalized_colors[(index - frame + offset) % len(normalized_colors)]
                    for index in range(self.num_segments)
                ]
            return [
                normalized_colors[(index + frame + offset) % len(normalized_colors)]
                for index in range(self.num_segments)
            ]

        if effect_type == "gradient":
            gradient: list[tuple[int, int, int]] = []
            if len(normalized_colors) == 1:
                normalized_colors = normalized_colors * 2

            for index in range(self.num_segments):
                position = index / max(1, self.num_segments - 1)
                scaled = position * (len(normalized_colors) - 1)
                lower = min(int(scaled), len(normalized_colors) - 2)
                upper = min(lower + 1, len(normalized_colors) - 1)
                weight = scaled - lower
                c0 = normalized_colors[lower]
                c1 = normalized_colors[upper]
                gradient.append(
                    (
                        int(c0[0] + (c1[0] - c0[0]) * weight),
                        int(c0[1] + (c1[1] - c0[1]) * weight),
                        int(c0[2] + (c1[2] - c0[2]) * weight),
                    )
                )
            return gradient

        if effect_type == "pulse":
            intensity = 0.5 + 0.5 * math.sin((frame / max(1, steps)) * math.pi + (math.pi / 2))
            return [
                (
                    int(color[0] * intensity),
                    int(color[1] * intensity),
                    int(color[2] * intensity),
                )
                for index in range(self.num_segments)
                for color in [normalized_colors[index % len(normalized_colors)]]
            ]

        if effect_type == "rainbow":
            colors_out: list[tuple[int, int, int]] = []
            for index in range(self.num_segments):
                hue = (index * 360 / max(1, self.num_segments) + frame * 10) % 360
                if hue < 60:
                    rgb = (255, int(hue / 60 * 255), 0)
                elif hue < 120:
                    rgb = (255 - int((hue - 60) / 60 * 255), 255, 0)
                elif hue < 180:
                    rgb = (0, 255, int((hue - 120) / 60 * 255))
                elif hue < 240:
                    rgb = (0, 255 - int((hue - 180) / 60 * 255), 255)
                elif hue < 300:
                    rgb = (int((hue - 240) / 60 * 255), 0, 255)
                else:
                    rgb = (255, 0, 255 - int((hue - 300) / 60 * 255))
                colors_out.append(rgb)
            return colors_out

        if effect_type == "twinkle":
            return [
                normalized_colors[(index + frame + offset) % len(normalized_colors)] if (index + frame) % 3 != 0 else self.off
                for index in range(self.num_segments)
            ]

        return [
            normalized_colors[(index + offset) % len(normalized_colors)]
            for index in range(self.num_segments)
        ]

    def generate_packet(self, sequence: int = 0x0c) -> bytes:
        packet = bytearray([0x00, sequence])
        packet.extend(bytearray.fromhex(self.header_prefix))

        # 1. Provide safe fallbacks for internal values
        r = self.r if self.r is not None else 255
        g = self.g if self.g is not None else 255
        b = self.b if self.b is not None else 255
        br = self.br if self.br is not None else 255
        v = int((br / 255.0) * (100 - 12) + 12) if br > 0 else 0

        custom_effect = self.custom_effects.get(self.eff)
        if isinstance(custom_effect, dict):
            for pr, pg, pb in self._build_effect_colors(custom_effect):
                if pr == 0 and pg == 0 and pb == 0:
                    packet.extend(bytearray([0xa1, 0, 0, 0]))
                    continue

                h, s = self.rgb_to_custom_hsv(pr, pg, pb)
                packet.extend(bytearray([0xa1, h, s, v]))
        else:
            # 2. Use the local safe R, G, B values for the HSV conversion
            h, s = self.rgb_to_custom_hsv(r, g, b)

            # 3. Use the local safe 'br' value for the brightness math
            # This prevents the: TypeError: '>' not supported between 'NoneType' and 'int'
            v = int((br / 255.0) * (100 - 12) + 12) if br > 0 else 0

            for _ in range(self.num_segments):
                packet.extend(bytearray([0xa1, h, s, v]))

        self._effect_step += 1
        return bytes(packet)