import lvgl as lv
import time
from mpos import Activity, DeviceManager

class SCD4x:
    """Driver for Sensirion SCD40/SCD41 (CO2, Temp, Humidity) - I2C Addr: 0x62"""
    I2C_ADDR = 0x62

    def __init__(self, i2c):
        self.i2c = i2c

    def start(self):
        try:
            self.i2c.writeto(self.I2C_ADDR, b'\x21\xb1')
        except Exception as e:
            print("SCD40/SCD41 start error:", e)

    def read_measurement(self):
        try:
            self.i2c.writeto(self.I2C_ADDR, b'\xec\x05')
            time.sleep_ms(5)
            data = self.i2c.readfrom(self.I2C_ADDR, 9)

            co2 = (data[0] << 8) | data[1]
            raw_temp = (data[3] << 8) | data[4]
            temp = -45.0 + (175.0 * raw_temp / 65535.0)
            raw_humi = (data[6] << 8) | data[7]
            humi = 100.0 * raw_humi / 65535.0

            return co2, temp, humi
        except Exception as e:
            print("SCD40/SCD41 read error:", e)
            return None, None, None


class SHT3x:
    """Driver for Sensirion SHT30 / SHT31 (Temp, Humidity) - I2C Addr: 0x44 / 0x45"""
    def __init__(self, i2c, addr=0x44):
        self.i2c = i2c
        self.addr = addr

    def start(self):
        pass

    def read_measurement(self):
        try:
            self.i2c.writeto(self.addr, b'\x2c\x06')
            time.sleep_ms(15)
            data = self.i2c.readfrom(self.addr, 6)

            raw_temp = (data[0] << 8) | data[1]
            temp = -45.0 + (175.0 * raw_temp / 65535.0)

            raw_humi = (data[3] << 8) | data[4]
            humi = 100.0 * raw_humi / 65535.0

            return None, temp, humi
        except Exception as e:
            print("SHT3x read error:", e)
            return None, None, None


class AHT20:
    """Driver for ASAIR AHT20 / AHT21 (Temp, Humidity) - I2C Addr: 0x38"""
    I2C_ADDR = 0x38

    def __init__(self, i2c):
        self.i2c = i2c

    def start(self):
        try:
            self.i2c.writeto(self.I2C_ADDR, b'\xbe\x08\x00')
            time.sleep_ms(10)
        except Exception:
            pass

    def read_measurement(self):
        try:
            self.i2c.writeto(self.I2C_ADDR, b'\xac\x33\x00')
            time.sleep_ms(80)
            data = self.i2c.readfrom(self.I2C_ADDR, 7)

            raw_humi = ((data[1] << 12) | (data[2] << 4) | (data[3] >> 4))
            humi = (raw_humi * 100.0) / 1048576.0

            raw_temp = (((data[3] & 0x0F) << 16) | (data[4] << 8) | data[5])
            temp = ((raw_temp * 200.0) / 1048576.0) - 50.0

            return None, temp, humi
        except Exception as e:
            print("AHT20 read error:", e)
            return None, None, None


class AM2320_DHT12:
    """Driver for AM2320 & DHT12 (Temp, Humidity) - I2C Addr: 0x5C"""
    I2C_ADDR = 0x5C

    def __init__(self, i2c):
        self.i2c = i2c

    def start(self):
        pass

    def read_measurement(self):
        try:
            try:
                self.i2c.writeto(self.I2C_ADDR, b'')
            except Exception:
                pass
            time.sleep_ms(2)

            self.i2c.writeto(self.I2C_ADDR, b'\x03\x00\x04')
            time.sleep_ms(2)
            data = self.i2c.readfrom(self.I2C_ADDR, 8)

            if data[0] == 0x03 and data[1] == 0x04:
                humi = ((data[2] << 8) | data[3]) / 10.0
                raw_temp = ((data[4] & 0x7F) << 8) | data[5]
                temp = -raw_temp / 10.0 if (data[4] & 0x80) else raw_temp / 10.0
                return None, temp, humi
        except Exception:
            pass

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
    # Color Constants
    COLOR_GREEN = 0x00E676
    COLOR_ORANGE = 0xFF9800
    COLOR_RED = 0xFF1744
    COLOR_NEUTRAL = 0x757575

    def onCreate(self):
        """Initialize variables and perform automatic sensor detection on the I2C bus."""
        screen = lv.obj()

        self.temp_val = 0.0
        self.humi_val = 0
        self.co2_val = None
        self.timer = None
        self.sensor = None
        print("onCreate")

        try:
            self.i2c = DeviceManager.getBus(type="i2c")
            if self.i2c is None:
                raise RuntimeError("I2C bus unavailable")
                
            if self.i2c:
                self.sensor = self._autodetect_sensor()
                if self.sensor:
                    self.sensor.start()
        except Exception as e:
            self.i2c = None
            print("DeviceManager I2C error:", e)

            """Build screen elements and launch the update timer."""
        screen.set_style_bg_color(lv.color_hex(0x1E1E1E), 0)
        screen.set_style_bg_opa(lv.OPA.COVER, 0)

        container = lv.obj(screen)
        container.set_size(lv.pct(100), lv.pct(100))
        container.set_flex_flow(lv.FLEX_FLOW.COLUMN)
        container.set_flex_align(lv.FLEX_ALIGN.SPACE_EVENLY, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
        container.set_style_bg_opa(lv.OPA.TRANSP, 0)
        container.set_style_border_width(0, 0)
        container.set_style_pad_all(10, 0)

        # Row 1: Temperature (Icon only, NO color strip)
        self.lbl_temp, _ = self._create_row(
            parent=container,
            # icon_symbol=lv.SYMBOL.TEMPERATURE if hasattr(lv.SYMBOL, "TEMPERATURE") else "🌡",
            icon_symbol = "Temperature",
            value_str="--.- °C",
            show_bar=False
        )

        # Row 2: Humidity (Icon only, dynamic strip)
        self.lbl_humi, self.bar_humi = self._create_row(
            parent=container,
            # icon_symbol="💧",
            icon_symbol="Humidity",
            value_str="-- %",
            show_bar=True
        )

        # Row 3: CO₂ (Text 'CO₂', dynamic strip)
        self.lbl_co2, self.bar_co2 = self._create_row(
            parent=container,
            #icon_symbol="CO₂",
            icon_symbol="CO2",
            value_str="----",
            show_bar=True
        )

        self.setContentView(screen)


    def _autodetect_sensor(self):
        """Scans the I2C bus and instantiates the first detected sensor."""
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
        self._update_sensor_data()
        self.timer = lv.timer_create(self._timer_cb, 3000, None)

    def _create_row(self, parent, icon_symbol, value_str, show_bar=True):
        """Helper method to construct a UI row. If show_bar is False, adds an invisible spacer."""
        row = lv.obj(parent)
        row.set_size(lv.pct(100), 65)
        row.set_flex_flow(lv.FLEX_FLOW.ROW)
        row.set_flex_align(lv.FLEX_ALIGN.SPACE_BETWEEN, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
        row.set_style_bg_opa(lv.OPA.TRANSP, 0)
        row.set_style_border_width(0, 0)
        row.set_style_pad_hor(12, 0)

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

        if show_bar:
            bar.set_style_bg_color(lv.color_hex(self.COLOR_NEUTRAL), 0)
            bar.set_style_bg_opa(lv.OPA.COVER, 0)
        else:
            # Invisible spacer maintaining alignment layout
            bar.set_style_bg_opa(lv.OPA.TRANSP, 0)

        return val_lbl, bar

    def _get_humidity_color(self, humi):
        """Evaluates humidity quality: Optimal (40-60%), Fair (30-39% or 61-70%), Poor (<30% or >70%)."""
        if 40 <= humi <= 60:
            return self.COLOR_GREEN
        elif 30 <= humi < 40 or 61 <= humi <= 70:
            return self.COLOR_ORANGE
        else:
            return self.COLOR_RED

    def _get_co2_color(self, co2):
        """Evaluates CO2 ppm quality: Good (<800 ppm), Moderate (800-1200 ppm), Poor (>1200 ppm)."""
        if co2 < 800:
            return self.COLOR_GREEN
        elif 800 <= co2 <= 1200:
            return self.COLOR_ORANGE
        else:
            return self.COLOR_RED

    def _timer_cb(self, timer):
        """Periodic timer callback to read data and refresh UI."""
        self._update_sensor_data()

    def _update_sensor_data(self):
        """Fetch values from auto-detected sensor and update display values + dynamic strip colors."""
        if not self.sensor:
            return

        co2, temp, humi = self.sensor.read_measurement()

        if temp is not None:
            self.lbl_temp.set_text(f"{temp:.1f} °C")

        if humi is not None:
            humi_int = int(humi)
            self.lbl_humi.set_text(f"{humi_int} %")
            humi_color = self._get_humidity_color(humi_int)
            self.bar_humi.set_style_bg_color(lv.color_hex(humi_color), 0)

        if co2 is not None:
            self.lbl_co2.set_text(f"{co2:04d}")
            co2_color = self._get_co2_color(co2)
            self.bar_co2.set_style_bg_color(lv.color_hex(co2_color), 0)
        else:
            self.lbl_co2.set_text("N/A")
            self.bar_co2.set_style_bg_color(lv.color_hex(self.COLOR_NEUTRAL), 0)

    def onStop(self, screen):
        """Clean up active timers upon exiting activity."""
        if self.timer:
            self.timer._del()
            self.timer = None
