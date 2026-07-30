# buttons2026.py
import mpos

class Buttons:
    """Hardware-abstractie voor de digitale knoppen via de CH32 coprocessor op de Fri3d Badge 2026.
    
    Retourneert 0 bij INGEDRUKT en 1 bij NIET-INGEDRUKT (gelijk aan GPIO PULL_UP gedrag).
    """

    def get_button_a_value(self):
        return 0 if mpos.io_expander.button_a else 1

    def get_button_b_value(self):
        return 0 if mpos.io_expander.button_b else 1

    def get_button_x_value(self):
        return 0 if mpos.io_expander.button_x else 1

    def get_button_y_value(self):
        return 0 if mpos.io_expander.button_y else 1

    def get_button_menu_value(self):
        return 0 if mpos.io_expander.button_menu else 1


buttons = Buttons()
