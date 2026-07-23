import logging
from mpos import Activity
import lvgl as lv
from mpos import WifiService

# Fri3d badge 2024
from mpos.board.fri3d_2024 import adc_up_down, adc_left_right

JOYSTICK_RECTANGLE_WIDTH=const(80)
JOYSTICK_RECTANGLE_HEIGHT=const(80)
JOYSTICK_CIRCLE_RADIUS=const(30)

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
        self.status_label = lv.label(screen)
        self.status_label.set_text("Start status")
        self.status_label.align(lv.ALIGN.TOP_LEFT, 30, 30)

        # SSID Label bovenaan het scherm
        self.wifi_label = lv.label(screen)
        self.wifi_label.set_text(self.get_wifi_ssid())
        self.wifi_label.align(lv.ALIGN.TOP_MID, 0, 10)
        
        # Create a black rectangle with a green border
        self.rect = lv.obj(screen)
        self.rect.set_size(JOYSTICK_RECTANGLE_WIDTH, JOYSTICK_RECTANGLE_HEIGHT)
        self.rect.set_style_radius(0,lv.PART.MAIN)
        self.rect.set_style_bg_color(lv.color_black(), lv.PART.MAIN)
        self.rect.set_style_border_color(lv.color_hex(0x00FF00), lv.PART.MAIN)
        self.rect.set_style_border_width(1, lv.PART.MAIN)
        self.rect.remove_flag(lv.obj.FLAG.SCROLLABLE)
        self.rect.align(lv.ALIGN.TOP_LEFT, 30, 150)

        self.circ_area = lv.obj(self.rect)
        self.circ_area.set_size(JOYSTICK_CIRCLE_RADIUS, JOYSTICK_CIRCLE_RADIUS)
        self.circ_area.set_style_radius(lv.RADIUS_CIRCLE,lv.PART.MAIN)
        self.circ_area.set_style_bg_color(lv.color_hex(0x00FF00), lv.PART.MAIN)
        self.circ_area.set_style_border_width(0, lv.PART.MAIN)
        
        self.setContentView(screen)

    def onStart(self, screen):
        print("starting joystick refresh_timer")
        self.refresh_joystick_timer = lv.timer_create(self.refresh_joystick, 80, None)
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
        #print(f"x: {x} y:{y}")
        
        # Map the analog values to the rectangle's coordinates
        x_pos = lv.map(x, 0, 4095, -int(JOYSTICK_RECTANGLE_WIDTH/2), int(JOYSTICK_RECTANGLE_WIDTH/2))
        y_pos = lv.map(y, 4095, 0, -int(JOYSTICK_RECTANGLE_HEIGHT/2), int(JOYSTICK_RECTANGLE_HEIGHT/2))
        self.circ_area.set_pos(x_pos+int(JOYSTICK_CIRCLE_RADIUS/2),y_pos+int(JOYSTICK_CIRCLE_RADIUS/2))


    def refresh_wifi(self, timer):
        if self.wifi_label:
            self.wifi_label.set_text(self.get_wifi_ssid())
