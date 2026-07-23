import logging
from mpos import Activity
import lvgl as lv
from mpos import WifiService

# Fri3d badge 2024
from mpos.board.fri3d_2024 import adc_up_down, adc_left_right

class Main(Activity):

    refresh_joystick_timer = None
    refresh_wifi_timer = None
    wifi_label = None

    def get_wifi_ssid(self):
        ssid = WifiService.get_current_ssid()
        if ssid:
            return f"Wi-Fi: {ssid}"
        return "No Wifi"
    
    def onCreate(self):
        print("onCreate RemoteControl")
        screen = lv.obj()
        label = lv.label(screen)
        label.set_text("Hello from RemoteControl!")
        label.center()
        
        # SSID Label bovenaan het scherm
        self.wifi_label = lv.label(screen)
        self.wifi_label.set_text(self.get_wifi_ssid())
        self.wifi_label.align(lv.ALIGN.TOP_MID, 0, 10)
        
        self.setContentView(screen)

    def onStart(self, screen):
        print("starting joystick refresh_timer")
        self.refresh_joystick_timer = lv.timer_create(self.refresh_joystick, 1000, None)
        self.refresh_wifi_timer = lv.timer_create(self.refresh_wifi, 10000, None)
        
        # Silence the MPOS focus_direction logger while this screen is active (joystick events)
        logging.getLogger("mpos.ui.focus_direction").setLevel(logging.ERROR)

    def onStop(self, screen):
        if self.refresh_joystick_timer:
            print("stopping joystick refresh_timer")
            self.refresh_joystick_timer.delete()

        if self.refresh_wifi_timer:
            print("stopping wifi refresh_timer")
            self.refresh_wifi_timer.delete()

        # Restore default logging level when leaving
        logging.getLogger("mpos.ui.focus_direction").setLevel(logging.WARNING)

    def refresh_joystick(self, timer):
        # Fri3d badge 2024
        y = adc_up_down.read()
        x = adc_left_right.read()
        print(f"x: {x} y:{y}")

    def refresh_wifi(self, timer):
        if self.wifi_label:
            self.wifi_label.set_text(self.get_wifi_ssid())
