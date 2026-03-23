import logging

_LOGGER = logging.getLogger(__name__)

EFFECT_NONE = "None"
EFFECT_DASHED = "Dashed"

MIN_V = 12
MAX_V = 100


class LedStrip:
    def __init__(self, r=255, g=255, b=255, br=255, eff=EFFECT_NONE):
        self.r = r
        self.g = g
        self.b = b
        self.br = br
        self.eff = eff

        self.num_segments = 20  # number of LED segments
        self.header_prefix = "80000057580ae1030014000014"

        self.teal = (0x0e, 0xe4, 0x0c)
        self.off = (0x00, 0x00, 0x00)

    def rgb_to_custom_hsv(self, r, g, b):
        """Convert RGB to device-specific HSV."""
        r_f, g_f, b_f = r / 255.0, g / 255.0, b / 255.0
        max_c, min_c = max(r_f, g_f, b_f), min(r_f, g_f, b_f)
        diff = max_c - min_c

        if diff == 0:
            h = 0
        elif max_c == r_f:
            h = (60 * ((g_f - b_f) / diff) + 360) % 360
        elif max_c == g_f:
            h = (60 * ((b_f - r_f) / diff) + 120)
        else:
            h = (60 * ((r_f - g_f) / diff) + 240)

        # Device-specific scaling
        return int(h / 2), int(max_c * 100)

    def _dashed_pattern(self):
        """Generate dashed effect pattern."""
        return (
            [self.off] * 4
            + [self.teal] * 4
            + [self.off] * 6
            + [self.teal] * 2
            + [self.off] * 2
            + [self.teal] * 2
        )

    def generate_packet(self, sequence: int = 0x0C) -> bytes:
        packet = bytearray([0x00, sequence])
        packet.extend(bytearray.fromhex(self.header_prefix))

        r, g, b = self.r, self.g, self.b
        br = self.br or 0

        if self.eff == EFFECT_DASHED:
            for pr, pg, pb in self._dashed_pattern():
                packet.extend(bytearray([0xA1, pr, pg, pb]))

        else:
            h, v_raw = self.rgb_to_custom_hsv(r, g, b)

            if br > 0:
                v = int((br / 255.0) * (MAX_V - MIN_V) + MIN_V)
            else:
                v = 0

            for _ in range(self.num_segments):
                packet.extend(bytearray([0xA1, h, v_raw, v]))

        return bytes(packet)