# Joystick2024.py
from mpos.board.fri3d_2024 import adc_up_down, adc_left_right

class Joystick:
    """Hardware-abstractie voor de analoge joystick van de Fri3d Badge 2024."""

    def read_raw(self):
        """Leest de ruwe ADC-waarden (x, y) direct uit."""
        raw_y = adc_up_down.read()
        raw_x = adc_left_right.read()
        return raw_x, raw_y

joystick = Joystick()