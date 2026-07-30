# buttons2024.py
from mpos.board.fri3d_2024 import (
    btn_a,
    btn_b,
    btn_menu,
    btn_x,
    btn_y,
)

class Buttons:
    """Hardware-abstractie voor de digitale knoppen van de Fri3d Badge 2024."""

    def get_button_a_value(self):
        return btn_a.value()

    def get_button_b_value(self):
        return btn_b.value()

    def get_button_x_value(self):
        return btn_x.value()

    def get_button_y_value(self):
        return btn_y.value()

    def get_button_menu_value(self):
        return btn_menu.value()


buttons = Buttons()
