import logging
from mpos import Activity
import lvgl as lv
from mpos import WifiService

# Fri3d badge 2024
from mpos.board.fri3d_2024 import adc_up_down, adc_left_right, btn_y, btn_b, btn_a

JOYSTICK_RECTANGLE_WIDTH=const(80)
JOYSTICK_RECTANGLE_HEIGHT=const(80)
JOYSTICK_CIRCLE_RADIUS=const(30)

class Main(Activity):

    refresh_joystick_timer = None
    refresh_wifi_timer = None
    refresh_button_timer = None
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
        
        self.slider1 = lv.slider(screen)
        self.slider1.set_range(-1000, 1000)
        self.slider1.set_value(0, False)
        self.slider1.align(lv.ALIGN.TOP_LEFT, 30, 80)
        self.slider1.add_event_cb(self.compensate_joystick_cb, lv.EVENT.KEY, None)
        self.slider1.add_event_cb(self.on_slider_change, lv.EVENT.VALUE_CHANGED, None)
        
        # Label om de slider waarde te tonen
        self.slider1_label = lv.label(screen)
        self.slider1_label.set_text("Waarde: 0")
        self.slider1_label.align(lv.ALIGN.TOP_LEFT, 30, 120)

        
        self.setContentView(screen)

    def onStart(self, screen):
        print("starting joystick refresh_timer")
        self.refresh_joystick_timer = lv.timer_create(self.refresh_joystick, 80, None)
        self.refresh_wifi_timer = lv.timer_create(self.refresh_wifi, 10000, None)
        self.refresh_button_timer = lv.timer_create(self.refresh_buttons, 80, None)
        
        # Silence the MPOS focus_direction logger while this screen is active (joystick events)
        logging.getLogger("mpos.ui.focus_direction").setLevel(logging.ERROR)

    def onStop(self, screen):
        if self.refresh_joystick_timer:
            print("stopping joystick refresh_timer")
            self.refresh_joystick_timer.delete()

        if self.refresh_wifi_timer:
            print("stopping wifi refresh_timer")
            self.refresh_wifi_timer.delete()

        if self.refresh_button_timer:
            print("stopping button refresh_timer")
            self.refresh_button_timer.delete()

        # Restore default logging level when leaving
        logging.getLogger("mpos.ui.focus_direction").setLevel(logging.WARNING)

    def refresh_buttons(self, timer):
        if btn_y.value() == 0:
            #print("Knop Y is ingedrukt!")
            current_value = self.slider1.get_value()
            new_value = min(1000, current_value + 10)
            self.slider1.set_value(new_value, False)
            self.on_slider_change(None)
        if btn_b.value() == 0:
            #print("Knop B is ingedrukt!")
            current_value = self.slider1.get_value()
            new_value = max(-1000, current_value - 10)
            self.slider1.set_value(new_value, False)
            self.on_slider_change(None)
        if btn_a.value() == 0:
            #print("Knop A is ingedrukt!")
            self.slider1.set_value(0, False)
            self.on_slider_change(None)

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
            
    def on_slider_change(self, event):
        if self.slider1_label:
            self.slider1_label.set_text(f"Waarde: {self.slider1.get_value()}")

    def compensate_joystick_cb(self, e):
        if e.get_code() == lv.EVENT.KEY:
            key = e.get_key()
            slider_obj = self.slider1
            current_val = slider_obj.get_value()
            
            # Als de joystick RIGHT/UP/LEFT/DOWN key event geeft, wordt de waarde aangepast +/- 1, dan
            # doen we net omgekeerde om waarde weer goed te krijgen
            if key in (lv.KEY.RIGHT, lv.KEY.UP):
                slider_obj.set_value(current_val - 1, None)
                self.on_slider_change(None)
                
            elif key in (lv.KEY.LEFT, lv.KEY.DOWN):
                slider_obj.set_value(current_val + 1, None)
                self.on_slider_change(None)
