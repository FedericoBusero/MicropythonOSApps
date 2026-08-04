# Software developed for Fri3d badge 2024 and 2026
# You can control external devices with a joystick & 2 sliders using websockets on wifi. So the device should run a SoftAP and Websocket server
# It works with devices used in MasynMachien workshops such as hovercrafts and blimps. 
# Author: FedericoBusero

# Source of the app: https://github.com/FedericoBusero/MicropythonOSApps/tree/main/be.masynmachien.remotecontrol2
#   Blimp source: https://github.com/FedericoBusero/Wifi-Blimp-Browser
#   Hovercraft source: https://github.com/FedericoBusero/Wifi-Hovercraft-Browser/

# How to use: 
# - Connect to the Wifi network of the SoftAP using the Wifi app
# - Move the joystick circle by using the physical joystick
# - Move the first slider by holding the start button and simultaniously using the buttons Y and B
# - Move the second slider using the buttons Y and B, reset to default bij pressing button A

# This application-level protocol runs over a standard WebSocket connection (ws://192.168.4.1:82/). 
# It enables real-time, bi-directional communication between the controller device (badge) and the WebSocket server.
# Messages it sends:
# - every second it sends ping message "0"
# - every 80 ms, when the joystick has moved, it sends the joystick coordinates in the range -180 .. 180 in the format "1:x,y" e.g. "1:180,45"
# - every 80 ms, when the first slider has moved, it sends the slider position in the range -180 .. 180 where 0 is the default center position in the format "3:v" e.g. "2:17"
# - every 80 ms, when the second slider has moved, it sends the slider position in the range 0 .. 360 where 180 is the default center position in the format "2:v" e.g. "2:180"
# Text messages it receives are displayed on the status bar

import logging
from mpos import Activity
import lvgl as lv
from mpos import WifiService, DeviceInfo

import asyncio
import aiohttp
import network
import time


hardware_id = DeviceInfo.get_hardware_id()
if hardware_id == "fri3d_2024":
    from mpos.board.fri3d_2024 import (
        btn_a,
        btn_b,
        btn_menu,
        btn_start,
        btn_x,
        btn_y,
        adc_up_down, 
        adc_left_right
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

        def get_button_start_value(self):
            return btn_start.value()
  
    class Joystick:
        """Hardware-abstractie voor de analoge joystick van de Fri3d Badge 2024."""
    
        def read_raw(self):
            """Leest de ruwe ADC-waarden (x, y) direct uit."""
            raw_y = adc_up_down.read()
            raw_x = adc_left_right.read()
            return raw_x, raw_y
    
else:
    # Fri3d badge 2026
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
        
        def get_button_start_value(self):
            return 0 if mpos.io_expander.button_start else 1
    
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
    
    
buttons = Buttons()
    
joystick = Joystick()
JOYSTICK_RECTANGLE_WIDTH = 100
JOYSTICK_RECTANGLE_HEIGHT = 100
JOYSTICK_CIRCLE_RADIUS = 30

def map_joystick(x, in_min, in_max, out_min, out_max, center=50, border=50):
    """
    Mapt een joystickwaarde met deadzones voor het midden en de randen.
    Ondersteunt ook omgekeerde bereiken (in_min > in_max of out_min > out_max).
    Returnt altijd een integer.
    """
    in_center = (in_min + in_max) / 2.0
    out_center = (out_min + out_max) / 2.0
    
    # 1. Begrens x netjes tussen de laagste en hoogste invoerwaarde
    x_min = min(in_min, in_max)
    x_max = max(in_min, in_max)
    x = max(x_min, min(x, x_max))
    
    # Check richting van de invoer
    is_in_inverted = in_min > in_max
    
    # 2. Border check (uiterste waarden vastpinnen)
    if not is_in_inverted:
        if x <= (in_min + border):
            return int(out_min)
        if x >= (in_max - border):
            return int(out_max)
    else:
        if x >= (in_min - border):
            return int(out_min)
        if x <= (in_max + border):
            return int(out_max)
        
    # 3. Center check (middenzone vastpinnen op het gemiddelde)
    if abs(x - in_center) <= center:
        return int(round(out_center))
        
    # 4. Schalen buiten de center zone
    if (not is_in_inverted and x < in_center) or (is_in_inverted and x > in_center):
        # Onderste helft van de beweging
        src_min = in_min + border if not is_in_inverted else in_min - border
        src_max = in_center - center if not is_in_inverted else in_center + center
        dst_min = out_min
        dst_max = out_center
    else:
        # Bovenste helft van de beweging
        src_min = in_center + center if not is_in_inverted else in_center - center
        src_max = in_max - border if not is_in_inverted else in_max + border
        dst_min = out_center
        dst_max = out_max
        
    # Lineaire schaling en afronden naar integer
    result = dst_min + (x - src_min) * (dst_max - dst_min) / (src_max - src_min)
    return int(round(result))

class RemoteControl(Activity):

    refresh_joystick_timer = None
    refresh_slider_timer = None
    refresh_wifi_timer = None
    refresh_button_timer = None
    wifi_label = None
    ws_task = None
    
    # Joystick waarden (-180 tot 180)
    joy_x = 0
    joy_y = 0

    slider1_val = 0
    slider2_val = 180

    def get_wifi_ssid2(self):
        ssid = WifiService.get_current_ssid()
        if ssid:
            return f"Wi-Fi: {ssid}"
        return "No Wifi"

    def get_wifi_ssid(self):
        try:
            wlan = network.WLAN(network.STA_IF)
            if wlan.isconnected():
                # In MicroPython geeft config('essid') de verbonden SSID terug
                ssid = WifiService.get_current_ssid()
                ip = WifiService.get_ipv4_gateway()
                if ssid and ip:
                    return f"{ssid} {ip}"
        except Exception as e:
            print("Fout bij ophalen SSID via network module:", e)
            
        return "No Wifi"
    
    def onCreate(self):
        # print("onCreate RemoteControl")
        screen = lv.obj()
        self.status_label = lv.label(screen)
        self.status_label.set_style_text_font(lv.font_montserrat_16, lv.PART.MAIN)
        self.status_label.set_text("Startup")
        self.status_label.align(lv.ALIGN.TOP_LEFT, 30, 40)

        # SSID Label bovenaan het scherm
        self.wifi_label = lv.label(screen)
        self.wifi_label.set_style_text_font(lv.font_montserrat_16, lv.PART.MAIN)
        self.wifi_label.set_text(self.get_wifi_ssid())
        self.wifi_label.align(lv.ALIGN.TOP_MID, 0, 10)
        
        # Create a black rectangle with a green border
        self.rect = lv.obj(screen)
        self.rect.set_size(JOYSTICK_RECTANGLE_WIDTH, JOYSTICK_RECTANGLE_HEIGHT)
        self.rect.set_style_radius(0, lv.PART.MAIN)
        self.rect.set_style_bg_color(lv.color_black(), lv.PART.MAIN)
        self.rect.set_style_border_color(lv.color_hex(0x00FF00), lv.PART.MAIN)
        self.rect.set_style_border_width(1, lv.PART.MAIN)
        self.rect.remove_flag(lv.obj.FLAG.SCROLLABLE)
        self.rect.align(lv.ALIGN.TOP_MID, 0, 130)

        self.circ_area = lv.obj(self.rect)
        self.circ_area.set_size(JOYSTICK_CIRCLE_RADIUS, JOYSTICK_CIRCLE_RADIUS)
        self.circ_area.set_style_radius(lv.RADIUS_CIRCLE, lv.PART.MAIN)
        self.circ_area.set_style_bg_color(lv.color_hex(0x00FF00), lv.PART.MAIN)
        self.circ_area.set_style_border_width(0, lv.PART.MAIN)
        
        self.slider1 = lv.slider(screen)
        self.slider1.set_range(-180, 180)
        self.slider1.set_value(0, False)
        self.slider1.align(lv.ALIGN.TOP_LEFT, 30, 65)
        # self.slider1.set_size(160, 20)  
        self.slider1.set_style_pad_all(10, lv.PART.KNOB)        
        self.slider1.set_style_bg_color(lv.color_hex(0x00FF00), lv.PART.KNOB)
        self.slider1.add_event_cb(self.compensate_joystick_cb_slider1, lv.EVENT.KEY, None)
        
        self.slider2 = lv.slider(screen)
        self.slider2.set_range(0, 360)
        self.slider2.set_value(180, False)
        self.slider2.align(lv.ALIGN.TOP_LEFT, 30, 100)
        # self.slider2.set_size(160, 20)  
        self.slider2.set_style_pad_all(10, lv.PART.KNOB)        
        self.slider2.set_style_bg_color(lv.color_hex(0x00FF00), lv.PART.KNOB)
        self.slider2.add_event_cb(self.compensate_joystick_cb_slider2, lv.EVENT.KEY, None)
        
        self.setContentView(screen)

    def onStart(self, screen):
        # print("starting joystick refresh_timer")
        self.refresh_joystick_timer = lv.timer_create(self.refresh_joystick, 20, None)
        self.refresh_slider_timer = lv.timer_create(self.refresh_slider, 10, None)
        self.refresh_wifi_timer = lv.timer_create(self.refresh_wifi, 10000, None)
        self.refresh_button_timer = lv.timer_create(self.refresh_buttons, 80, None)
        
        # Silence the MPOS focus_direction logger while this screen is active (joystick events)
        logging.getLogger("mpos.ui.focus_direction").setLevel(logging.ERROR)
        
        # print("start websocket program started")
        # Maak een achtergrondtaak aan op de reeds draaiende asyncio loop
        loop = asyncio.get_event_loop()
        self.ws_task = loop.create_task(self.main_websocket())

    def onStop(self, screen):
        if self.refresh_joystick_timer:
            # print("stopping joystick refresh_timer")
            self.refresh_joystick_timer.delete()
            
        if self.refresh_slider_timer:
            # print("stopping slider refresh_timer")
            self.refresh_slider_timer.delete()
        if self.refresh_wifi_timer:
            # print("stopping wifi refresh_timer")
            self.refresh_wifi_timer.delete()

        if self.refresh_button_timer:
            # print("stopping button refresh_timer")
            self.refresh_button_timer.delete()

        # Stop de websocket taak als deze nog draait
        if self.ws_task:
            # print("stopping websocket task")
            self.ws_task.cancel()
            self.ws_task = None
            
        # Restore default logging level when leaving
        logging.getLogger("mpos.ui.focus_direction").setLevel(logging.WARNING)

    def refresh_buttons(self, timer):
        if buttons.get_button_y_value() == 0:
            if buttons.get_button_start_value() == 0:
                current_value = self.slider1.get_value()
                new_value = min(1000, current_value + 10)
                self.slider1.set_value(new_value, False)
            else:
                current_value = self.slider2.get_value()
                new_value = min(1000, current_value + 10)
                self.slider2.set_value(new_value, False)
        if buttons.get_button_b_value() == 0:
            if buttons.get_button_start_value() == 0:
                current_value = self.slider1.get_value()
                new_value = max(-1000, current_value - 10)
                self.slider1.set_value(new_value, False)
            else:
                current_value = self.slider2.get_value()
                new_value = max(-1000, current_value - 10)
                self.slider2.set_value(new_value, False)
        if buttons.get_button_a_value() == 0:
            self.slider2.set_value(180, False)

    def refresh_joystick(self, timer):
        raw_x, raw_y = joystick.read_raw()
        dead_center = 400
        dead_border = 200
        
        # Map de analoge waarden naar schermcoördinaten voor het bolletje
        if self.circ_area:
            # x_pos = lv.map(raw_x, 0, 4095, -int(JOYSTICK_RECTANGLE_WIDTH/2), int(JOYSTICK_RECTANGLE_WIDTH/2))
            # y_pos = lv.map(raw_y, 4095, 0, -int(JOYSTICK_RECTANGLE_HEIGHT/2), int(JOYSTICK_RECTANGLE_HEIGHT/2))
            x_pos = map_joystick(raw_x, 0, 4095, -int(JOYSTICK_RECTANGLE_WIDTH/2), int(JOYSTICK_RECTANGLE_WIDTH/2), dead_center, dead_border)
            y_pos = map_joystick(raw_y, 4095, 0, -int(JOYSTICK_RECTANGLE_HEIGHT/2), int(JOYSTICK_RECTANGLE_HEIGHT/2), dead_center, dead_border)
            self.circ_area.set_pos(x_pos + int(JOYSTICK_CIRCLE_RADIUS/2), y_pos + int(JOYSTICK_CIRCLE_RADIUS/2))

        # Map de ADC waarden naar het bereik -180 tot 180 voor de WebSocket
        # self.joy_x = lv.map(raw_x, 0, 4095, -180, 180)
        # self.joy_y = lv.map(raw_y, 4095, 0, -180, 180)
        self.joy_x = map_joystick(raw_x, 0, 4095, -180, 180, dead_center, dead_border)
        self.joy_y = map_joystick(raw_y, 4095, 0, -180, 180, dead_center, dead_border)

#    def refresh_wifi(self, timer):
#        if self.wifi_label:
#            self.wifi_label.set_text(self.get_wifi_ssid())


    def refresh_slider(self, timer):
        if self.slider1:
            self.slider1_val = int(self.slider1.get_value())
        if self.slider2:
            self.slider2_val = int(self.slider2.get_value())
            
    def refresh_wifi(self, timer):
        try:
            wlan = network.WLAN(network.STA_IF)
            if wlan.isconnected():
                gateway_ip = WifiService.get_ipv4_gateway()
                
                ssid = WifiService.get_current_ssid()
                if self.wifi_label:
                    self.wifi_label.set_text(f"{ssid} {gateway_ip}")
            else:
                if self.wifi_label:
                    self.wifi_label.set_text("No Wifi")
                    
        except Exception as e:
            print("Fout in refresh_wifi:", e)
            if self.wifi_label:
                self.wifi_label.set_text("Wifi Error")
    
    def compensate_joystick_cb_slider1(self, e):
        if e.get_code() == lv.EVENT.KEY:
            key = e.get_key()
            slider_obj = self.slider1
            current_val = slider_obj.get_value()
            
            # Als de joystick RIGHT/UP/LEFT/DOWN key event geeft, wordt de waarde aangepast +/- 1, dan
            # doen we net omgekeerde om waarde weer goed te krijgen
            if key in (lv.KEY.RIGHT, lv.KEY.UP):
                slider_obj.set_value(current_val - 1, None)
            elif key in (lv.KEY.LEFT, lv.KEY.DOWN):
                slider_obj.set_value(current_val + 1, None)

    def compensate_joystick_cb_slider2(self, e):
        if e.get_code() == lv.EVENT.KEY:
            key = e.get_key()
            slider_obj = self.slider2
            current_val = slider_obj.get_value()
            
            # Als de joystick RIGHT/UP/LEFT/DOWN key event geeft, wordt de waarde aangepast +/- 1, dan
            # doen we net omgekeerde om waarde weer goed te krijgen
            if key in (lv.KEY.RIGHT, lv.KEY.UP):
                slider_obj.set_value(current_val - 1, None)
            elif key in (lv.KEY.LEFT, lv.KEY.DOWN):
                slider_obj.set_value(current_val + 1, None)

    
    async def send_ping_loop(self, ws):
        """Sends periodic ping data to the WebSocket server."""
        try:
            while True:
                msg = "0"
                # print(f"--> Sending ping: {msg}")
                await ws.send_str(msg)
                await asyncio.sleep(1)  # Send every second
        except (asyncio.CancelledError, OSError):
            raise
        except Exception as e:
            print(f"Ping loop error: {e}", flush=True)
            await ws.close()

    async def send_joystick_loop(self, ws):
        """Sends live joystick coordinates to the WebSocket server if they have changed."""
        last_sent = None
        try:
            while True:
                current_coords = (self.joy_x, self.joy_y)
                if current_coords != last_sent:
                    msg = f"1:{self.joy_x},{self.joy_y}"
                    # print(f"--> Sending joystick: {msg}")
                    await ws.send_str(msg)
                    last_sent = current_coords
                await asyncio.sleep(0.080)  # Check every 80ms
        except (asyncio.CancelledError, OSError):
            raise
        except Exception as e:
            print(f"Joystick loop error: {e}", flush=True)
            await ws.close()
            
    async def send_slider1_loop(self, ws):
        """Sends live slider values to the WebSocket server if they have changed."""
        last_sent = None
        try:
            while True:
                current_val = self.slider1_val
                if current_val != last_sent:
                    msg = f"3:{current_val}"
                    # print(f"--> Sending slider: {msg}")
                    await ws.send_str(msg)
                    last_sent = current_val
                await asyncio.sleep(0.080)  # Check elke 80ms
        except (asyncio.CancelledError, OSError):
            raise
        except Exception as e:
            print(f"Slider loop error: {e}", flush=True)
            await ws.close()

    async def send_slider2_loop(self, ws):
        """Sends live slider values to the WebSocket server if they have changed."""
        last_sent = None
        try:
            while True:
                current_val = self.slider2_val
                if current_val != last_sent:
                    msg = f"2:{current_val}"
                    # print(f"--> Sending slider: {msg}")
                    await ws.send_str(msg)
                    last_sent = current_val
                await asyncio.sleep(0.080)  # Check elke 80ms
        except (asyncio.CancelledError, OSError):
            raise
        except Exception as e:
            print(f"Slider loop error: {e}", flush=True)
            await ws.close()
            
    async def receive_loop(self, ws):
        """Listens for incoming messages from the server."""
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    # print(f"<-- Received: {msg.data}")
                    if self.status_label:
                        self.status_label.set_text(msg.data)
                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    print("WebSocket connection closed or encountered an error.")
                    break
        except (asyncio.CancelledError, OSError):
            raise
        except Exception as e:
            print("Error in receive loop:", e)

    async def main_websocket(self):
        SERVER_IP = "192.168.4.1"
        PORT = 82
        url = f"ws://{SERVER_IP}:{PORT}/"
        
        while True:
            ping_sender = None
            joy_sender = None
            slider1_sender = None
            slider2_sender = None
            receiver = None
            
            try:
                # print(f"Connecting to {url}...")
                if self.status_label:
                    self.status_label.set_text("Connecting...")

                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(url) as ws:
                        # print("Connected to 192.168.4.1:82!")
                        if self.status_label:
                            self.status_label.set_text("Connected")
                        
                        ping_sender = asyncio.create_task(self.send_ping_loop(ws))
                        joy_sender = asyncio.create_task(self.send_joystick_loop(ws))
                        slider1_sender = asyncio.create_task(self.send_slider1_loop(ws))
                        slider2_sender = asyncio.create_task(self.send_slider2_loop(ws))
                        receiver = asyncio.create_task(self.receive_loop(ws))
                        
                        await asyncio.gather(ping_sender, joy_sender, slider1_sender, slider2_sender, receiver)
                        #done, pending = await asyncio.wait(
                        #    [ping_sender, joy_sender, slider1_sender, slider2_sender, receiver],
                        #    return_when=asyncio.FIRST_COMPLETED
                        #)
                        # Annuleer de resterende taken direct
                        #for task in pending:
                        #    task.cancel()

            except asyncio.CancelledError:
                # print("WebSocket main task gracefully cancelled.")
                break  # Stop de loop definitief wanneer de activiteit stopt (onStop)

            except (OSError, Exception) as e:
                print(f"WebSocket connection lost or failed: {e}")
                if self.status_label:
                    self.status_label.set_text("Reconnecting ...")

            finally:
                # Zorg dat de subtaken altijd worden gestopt voordat we opnieuw verbinden
                if ping_sender:
                    ping_sender.cancel()
                if joy_sender:
                    joy_sender.cancel()
                if slider1_sender:
                    slider1_sender.cancel()
                if slider2_sender:
                    slider2_sender.cancel()
                if receiver:
                    receiver.cancel()

            # Wacht 5 seconden alvorens opnieuw te proberen
            print("Retrying connection in 5 seconds...")
            if self.status_label:
                self.status_label.set_text("Retrying in 5 seconds ...")
            await asyncio.sleep(5)
