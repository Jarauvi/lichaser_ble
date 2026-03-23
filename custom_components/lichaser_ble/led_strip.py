"""Packet generator for Lichaser BLE hardware."""
import logging

_LOGGER = logging.getLogger(__name__)

class LedStrip:
    """Internal state tracker and packet builder for the LED hardware."""

    def __init__(self):
        self.r = 255
        self.g = 255
        self.b = 255
        self.br = 255
        self.eff = "None"

    def generate_packet(self, command_byte: int = 0x0C) -> bytes:
        """
        Construct the byte array for the hardware.
        """
        
        # Example logic based on common BLE strip protocols:
        # We scale the RGB values by the brightness percentage
        multiplier = self.br / 255.0
        red = int(self.r * multiplier)
        green = int(self.g * multiplier)
        blue = int(self.b * multiplier)

        # This is a placeholder structure. 
        # Replace this with the actual byte sequence your hardware expects.
        packet = bytearray([
            0x7E,           # Header
            0x07,           # Length
            0x05,           # Type
            0x03,           # RGB Control
            red,
            green,
            blue,
            0x00,           # White/Warm (if applicable)
            0xEF            # Footer
        ])

        _LOGGER.debug("Generated packet: %s", packet.hex())
        return bytes(packet)

    @property
    def effect_list(self) -> list[str]:
        """Return a list of supported effects."""
        return ["None", "Rainbow", "Pulse", "Strobe", "Jumping"]