# Joystick2026.py
import mpos

class Joystick:
    """Hardware-abstractie voor de I2C joystick via de CH32 coprocessor op de Fri3d Badge 2026."""

    def read_raw(self):
        """Leest de ruwe X, Y-waarden uit via de I2C I/O expander.
        
        Retourneert (raw_x, raw_y).
        """
        # Kanaal 0 en 1 van de expander.analog bevatten de joystick ADC waarden
        raw_x = mpos.io_expander.analog[0]
        raw_y = mpos.io_expander.analog[1]
        return raw_x, raw_y


joystick = Joystick()