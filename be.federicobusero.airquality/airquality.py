import lvgl as lv
import time
from mpos import Activity, DeviceManager


class SCD4x:
    """Driver for Sensirion SCD40/SCD41 (CO2, Temp, Humidity) - Non-Blocking I2C Addr: 0x62"""
    I2C_ADDR = 0x62

    def __init__(self, i2c):
        self.i2c = i2c
        self.state = "INIT"
        self.target_time = 0

    @staticmethod
    def _check_crc(b1, b2, crc_val):
        crc = 0xFF
        for b in (b1, b2):
            crc ^= b
            for _ in range(8):
                if crc & 0x80:
                    crc = ((crc << 1) ^ 0x31) & 0xFF
                else:
                    crc = (crc << 1) & 0xFF
        return crc == crc_val

    def start(self):
        try:
            self.i2c.writeto(self.I2C_ADDR, b'\x3f\x86')
            self.state = "WAIT_START"
            self.target_time = time.ticks_add(time.ticks_ms(), 500)
        except Exception as e:
            print("SCD4x start error:", e)

    def _process(self):
        now = time.ticks_ms()
        if self.state == "WAIT_START":
            if time.ticks_diff(now, self.target_time) >= 0:
                try:
                    self.i2c.writeto(self.I2C_ADDR, b'\x21\xb1')
                    self.state = "RUNNING"
                except Exception as e:
                    print("SCD4x start error:", e)
                    self.state = "ERROR"

    def is_data_ready(self):
        if self.state != "RUNNING":
            return False
        try:
            self.i2c.writeto(self.I2C_ADDR, b'\xe4\xb8')
            data = self.i2c.readfrom(self.I2C_ADDR, 3)
            if self._check_crc(data[0], data[1], data[2]):
                status = (data[0] << 8) | data[1]
                return (status & 0x07FF) != 0
        except Exception:
            pass
        return False

    def read_measurement(self):
        self._process()

        if not self.is_data_ready():
            return None, None, None

        try:
            self.i2c.writeto(self.I2C_ADDR, b'\xec\x05')
            data = self.i2c.readfrom(self.I2C_ADDR, 9)

            if not (self._check_crc(data[0], data[1], data[2]) and
                    self._check_crc(data[3], data[4], data[5]) and
                    self._check_crc(data[6], data[7], data[8])):
                print("SCD4x CRC error")
                return None, None, None

            co2 = (data[0] << 8) | data[1]
            raw_temp = (data[3] << 8) | data[4]
            temp = -45.0 + (175.0 * float(raw_temp) / 65535.0)
            raw_humi = (data[6] << 8) | data[7]
            humi = 100.0 * float(raw_humi) / 65535.0

            return co2, temp, humi
        except Exception as e:
            print("SCD4x read error:", e)
            return None, None, None


class SHT3x:
    """Driver for Sensirion SHT30 / SHT31 - Non-Blocking I2C Addr: 0x44 / 0x45"""
    def __init__(self, i2c, addr=0x44):
        self.i2c = i2c
        self.addr = addr
        self.state = "IDLE"
        self.target_time = 0

    @staticmethod
    def _check_crc(b1, b2, crc_val):
        crc = 0xFF
        for b in (b1, b2):
            crc ^= b
            for _ in range(8):
                if crc & 0x80:
                    crc = ((crc << 1) ^ 0x31) & 0xFF
                else:
                    crc = (crc << 1) & 0xFF
        return crc == crc_val

    def start(self):
        pass

    def read_measurement(self):
        now = time.ticks_ms()

        if self.state == "IDLE":
            try:
                self.i2c.writeto(self.addr, b'\x2c\x06')
                self.state = "WAIT_MEASURE"
                self.target_time = time.ticks_add(now, 20)
            except Exception as e:
                print("SHT3x trigger error:", e)
            return None, None, None

        elif self.state == "WAIT_MEASURE":
            if time.ticks_diff(now, self.target_time) >= 0:
                self.state = "IDLE"
                try:
                    data = self.i2c.readfrom(self.addr, 6)
                    
                    if not (self._check_crc(data[0], data[1], data[2]) and 
                            self._check_crc(data[3], data[4], data[5])):
                        print("SHT3x CRC error")
                        return None, None, None

                    raw_temp = (data[0] << 8) | data[1]
                    temp = -45.0 + (175.0 * raw_temp / 65535.0)

                    raw_humi = (data[3] << 8) | data[4]
                    humi = 100.0 * raw_humi / 65535.0

                    return None, temp, humi
                except Exception as e:
                    print("SHT3x read error:", e)

        return None, None, None


class AHT20:
    """Driver for ASAIR AHT20 / AHT21 - Non-Blocking I2C Addr: 0x38"""
    I2C_ADDR = 0x38

    def __init__(self, i2c):
        self.i2c = i2c
        self.state = "IDLE"
        self.target_time = 0

    def start(self):
        try:
            self.i2c.writeto(self.I2C_ADDR, b'\xbe\x08\x00')
            time.sleep_ms(10)
        except Exception:
            pass

    def read_measurement(self):
        now = time.ticks_ms()

        if self.state == "IDLE":
            try:
                self.i2c.writeto(self.I2C_ADDR, b'\xac\x33\x00')
                self.state = "WAIT_MEASURE"
                self.target_time = time.ticks_add(now, 80)
            except Exception as e:
                print("AHT20 trigger error:", e)
            return None, None, None

        elif self.state == "WAIT_MEASURE":
            if time.ticks_diff(now, self.target_time) >= 0:
                self.state = "IDLE"
                try:
                    data = self.i2c.readfrom(self.I2C_ADDR, 7)

                    # Bit 7: Busy (1 = bezig, 0 = gereed)
                    if (data[0] & 0x80) != 0:
                        return None, None, None

                    raw_humi = ((data[1] << 12) | (data[2] << 4) | (data[3] >> 4))
                    humi = (raw_humi * 100.0) / 1048576.0

                    raw_temp = (((data[3] & 0x0F) << 16) | (data[4] << 8) | data[5])
                    temp = ((raw_temp * 200.0) / 1048576.0) - 50.0

                    return None, temp, humi
                except Exception as e:
                    print("AHT20 read error:", e)

        return None, None, None


class AM2320_DHT12:
    """Driver for AM2320 & DHT12 - Non-Blocking I2C Addr: 0x5C"""
    I2C_ADDR = 0x5C

    def __init__(self, i2c):
        self.i2c = i2c
        self.state = "IDLE"
        self.target_time = 0

    @staticmethod
    def _crc16(buf):
        crc = 0xFFFF
        for pos in buf:
            crc ^= pos
            for _ in range(8):
                if (crc & 0x0001) != 0:
                    crc >>= 1
                    crc ^= 0xA001
                else:
                    crc >>= 1
        return crc

    def start(self):
        pass

    def read_measurement(self):
        now = time.ticks_ms()

        if self.state == "IDLE":
            try:
                self.i2c.writeto(self.I2C_ADDR, b'')
            except Exception:
                pass  # AM2320 reageert met NACK op wake-up puls
            self.state = "WOKEN"
            self.target_time = time.ticks_add(now, 3)
            return None, None, None

        elif self.state == "WOKEN":
            if time.ticks_diff(now, self.target_time) >= 0:
                try:
                    self.i2c.writeto(self.I2C_ADDR, b'\x03\x00\x04')
                    self.state = "WAIT_READ"
                    self.target_time = time.ticks_add(now, 3)
                except Exception:
                    self.state = "DHT12_READ"
            return None, None, None

        elif self.state == "WAIT_READ":
            if time.ticks_diff(now, self.target_time) >= 0:
                self.state = "IDLE"
                try:
                    data = self.i2c.readfrom(self.I2C_ADDR, 8)
                    if data[0] == 0x03 and data[1] == 0x04:
                        crc_val = data[6] | (data[7] << 8)
                        if self._crc16(data[:6]) != crc_val:
                            print("AM2320 CRC error")
                            return None, None, None

                        humi = ((data[2] << 8) | data[3]) / 10.0
                        raw_temp = ((data[4] & 0x7F) << 8) | data[5]
                        temp = -raw_temp / 10.0 if (data[4] & 0x80) else raw_temp / 10.0
                        return None, temp, humi
                except Exception:
                    pass

        elif self.state == "DHT12_READ":
            self.state = "IDLE"
            try:
                self.i2c.writeto(self.I2C_ADDR, b'\x00')
                data = self.i2c.readfrom(self.I2C_ADDR, 5)

                if (data[0] + data[1] + data[2] + data[3]) & 0xFF == data[4]:
                    humi = data[0] + data[1] * 0.1
                    temp = data[2] + (data[3] & 0x7F) * 0.1
                    if data[3] & 0x80:
                        temp = -temp
                    return None, temp, humi
            except Exception as e:
                print("AM2320/DHT12 read error:", e)

        return None, None, None


class AirQuality(Activity):
    COLOR_GREEN = 0x00E676
    COLOR_ORANGE = 0xFF9800
    COLOR_RED = 0xFF1744
    COLOR_NEUTRAL = 0x757575

    def onCreate(self):
        screen = lv.obj()

        self.temp_val = 0.0
        self.humi_val = 0
        self.co2_val = None
        self.timer = None
        self.sensor = None

        try:
            self.i2c = DeviceManager.getBus(type="i2c")
            if self.i2c is None:
                raise RuntimeError("I2C bus unavailable")

            self.sensor = self._autodetect_sensor()
            if self.sensor:
                self.sensor.start()
        except Exception as e:
            self.i2c = None
            print("DeviceManager I2C error:", e)

        screen.set_style_bg_color(lv.color_hex(0x1E1E1E), 0)
        screen.set_style_bg_opa(lv.OPA.COVER, 0)

        container = lv.obj(screen)
        container.set_size(lv.pct(100), lv.pct(100))
        container.set_flex_flow(lv.FLEX_FLOW.COLUMN)
        container.set_flex_align(lv.FLEX_ALIGN.SPACE_EVENLY, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
        container.set_style_bg_opa(lv.OPA.TRANSP, 0)
        container.set_style_border_width(0, 0)
        container.set_style_pad_all(10, 0)

        self.lbl_temp, _ = self._create_row(container, "Temp", "--.- °C", show_bar=False)
        self.lbl_humi, self.bar_humi = self._create_row(container, "Humi", "-- %", show_bar=True)
        self.lbl_co2, self.bar_co2 = self._create_row(container, "CO2", "----", show_bar=True)

        self.setContentView(screen)

    def _autodetect_sensor(self):
        devices = self.i2c.scan()
        print("I2C devices detected:", [hex(d) for d in devices])

        if 0x62 in devices:
            print("Detected sensor: SCD40/SCD41")
            return SCD4x(self.i2c)
        elif 0x44 in devices or 0x45 in devices:
            addr = 0x44 if 0x44 in devices else 0x45
            print(f"Detected sensor: SHT30/SHT31 ({hex(addr)})")
            return SHT3x(self.i2c, addr=addr)
        elif 0x38 in devices:
            print("Detected sensor: AHT20/AHT21")
            return AHT20(self.i2c)
        elif 0x5C in devices:
            print("Detected sensor: AM2320 / DHT12")
            return AM2320_DHT12(self.i2c)
        else:
            print("No recognized environmental sensor found.")
            return None

    def onStart(self, screen):
        self.timer = lv.timer_create(self._timer_cb, 500, None)

    def _create_row(self, parent, icon_symbol, value_str, show_bar=True):
        row = lv.obj(parent)
        row.set_size(lv.pct(100), 65)
        row.set_flex_flow(lv.FLEX_FLOW.ROW)
        row.set_flex_align(lv.FLEX_ALIGN.SPACE_BETWEEN, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
        row.set_style_bg_opa(lv.OPA.TRANSP, 0)
        row.set_style_border_width(0, 0)
        row.set_style_pad_hor(12, 0)
        row.set_style_pad_ver(0, 0)  # Verwijder verticale padding die overflow veroorzaakt
    
        # LVGL 9.4: Schakel scrolling en de scrollbar op de RIJ ZELF uit
        row.remove_flag(lv.obj.FLAG.SCROLLABLE)
        row.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)
    
        icon_lbl = lv.label(row)
        icon_lbl.set_text(icon_symbol)
        icon_lbl.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
        if hasattr(lv, "font_montserrat_22"):
            icon_lbl.set_style_text_font(lv.font_montserrat_22, 0)
        icon_lbl.set_width(60)
    
        val_lbl = lv.label(row)
        val_lbl.set_text(value_str)
        val_lbl.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
        if hasattr(lv, "font_montserrat_28"):
            val_lbl.set_style_text_font(lv.font_montserrat_28, 0)
    
        bar = lv.obj(row)
        bar.set_size(12, 45)
        bar.set_style_radius(6, 0)
        bar.set_style_border_width(0, 0)
    
        # Schakel eventuele scrollbar op het bar-object zelf ook uit
        bar.remove_flag(lv.obj.FLAG.SCROLLABLE)
        bar.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)
    
        if show_bar:
            bar.set_style_bg_color(lv.color_hex(self.COLOR_NEUTRAL), 0)
            bar.set_style_bg_opa(lv.OPA.COVER, 0)
        else:
            bar.set_style_bg_opa(lv.OPA.TRANSP, 0)
    
        return val_lbl, bar

    def _get_humidity_color(self, humi):
        if 40 <= humi <= 60:
            return self.COLOR_GREEN
        elif 30 <= humi < 40 or 61 <= humi <= 70:
            return self.COLOR_ORANGE
        else:
            return self.COLOR_RED

    def _get_co2_color(self, co2):
        if co2 < 800:
            return self.COLOR_GREEN
        elif 800 <= co2 <= 1200:
            return self.COLOR_ORANGE
        else:
            return self.COLOR_RED

    def _timer_cb(self, timer):
        self._update_sensor_data()

    def _update_sensor_data(self):
        if not self.sensor or not hasattr(self, "lbl_temp"):
            return

        co2, temp, humi = self.sensor.read_measurement()

        try:
            if temp is not None:
                self.lbl_temp.set_text(f"{temp:.1f} °C")

            if humi is not None:
                humi_int = int(humi)
                self.lbl_humi.set_text(f"{humi_int} %")
                humi_color = self._get_humidity_color(humi_int)
                self.bar_humi.set_style_bg_color(lv.color_hex(humi_color), 0)

            if co2 is not None:
                self.lbl_co2.set_text(f"{co2:04d} ppm")
                co2_color = self._get_co2_color(co2)
                self.bar_co2.set_style_bg_color(lv.color_hex(co2_color), 0)
        except RuntimeError:
            pass

    def onStop(self, screen):
        if self.timer:
            try:
                self.timer.delete()
            except AttributeError:
                try:
                    self.timer._del()
                except Exception:
                    pass
            self.timer = None
