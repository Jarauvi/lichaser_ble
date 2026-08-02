import logging

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

    def generate_packet(self, sequence: int = 0x0c) -> bytes:
        packet = bytearray([0x00, sequence])
        packet.extend(bytearray.fromhex(self.header_prefix))
        
        # 1. Provide safe fallbacks for internal values
        r = self.r if self.r is not None else 255
        g = self.g if self.g is not None else 255
        b = self.b if self.b is not None else 255
        br = self.br if self.br is not None else 255
        
        if self.eff == "Dashed":
            # Assuming self.off and self.teal are already defined in __init__
            pattern = ([self.off]*4 + [self.teal]*4 + [self.off]*6 + [self.teal]*2 + [self.off]*2 + [self.teal]*2)
            for pr, pg, pb in pattern:
                packet.extend(bytearray([0xa1, pr, pg, pb]))
        else:
            # 2. Use the local safe R, G, B values for the HSV conversion
            h, s = self.rgb_to_custom_hsv(r, g, b)
            
            # 3. Use the local safe 'br' value for the brightness math
            # This prevents the: TypeError: '>' not supported between 'NoneType' and 'int'
            v = int((br / 255.0) * (100 - 12) + 12) if br > 0 else 0
            
            for _ in range(self.num_segments):
                packet.extend(bytearray([0xa1, h, s, v]))
                
        return bytes(packet)