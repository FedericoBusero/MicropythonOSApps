import logging
from mpos import Activity
import lvgl as lv

# Fri3d badge 2024
from machine import ADC, Pin
adcJoyX = ADC(Pin(1))
adcJoyY = ADC(Pin(3))

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
        raw_value = adcJoyX.read_u16()
        x = raw_value
        raw_value = adcJoyY.read_u16()
        y = raw_value
        print(f"x: {x} y:{y}")
