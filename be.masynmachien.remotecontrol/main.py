import logging
from mpos import Activity
import lvgl as lv

# Fri3d badge 2024
from mpos.board.fri3d_2024 import adc_up_down, adc_left_right

class Main(Activity):

    refresh_timer = None

    #fri3d badge 2024
    
    def onCreate(self):
        print("onCreate RemoteControl")
        screen = lv.obj()
        label = lv.label(screen)
        label.set_text("Hello from RemoteControl!")
        label.center()
        self.setContentView(screen)

    def onStart(self, screen):
        print("starting joystick refresh_timer")
        self.refresh_timer = lv.timer_create(self.refresh, 1000, None)
        
        # Silence the MPOS focus_direction logger while this screen is active (joystick events)
        logging.getLogger("mpos.ui.focus_direction").setLevel(logging.ERROR)

    def onStop(self, screen):
        if self.refresh_timer:
            print("stopping joystick refresh_timer")
            self.refresh_timer.delete()

        # Restore default logging level when leaving
        logging.getLogger("mpos.ui.focus_direction").setLevel(logging.WARNING)

    def refresh(self, timer):
        y = adc_up_down.read()
        x = adc_left_right.read()
        print(f"x: {x} y:{y}")
