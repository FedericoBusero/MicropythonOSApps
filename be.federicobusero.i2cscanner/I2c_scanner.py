import lvgl as lv
from mpos import Activity, DeviceManager

class I2CScannerActivity(Activity):
    """
    I2C Bus Scanner Activity for MPOS on Fri3d Badge 2026.
    Scans the system I2C bus periodically and visualizes active addresses
    in a 16x8 hex grid using LVGL.
    """

    def onCreate(self):
        screen = lv.obj()
        
        """Initialize activity instance variables."""
        self.i2c = None
        self.scan_timer = None
        self.table = None
        self.status_label = None
        self.found_count = 0

        """Set up dark mode UI, obtain I2C bus, and start background scanner."""
        # 1. Dark Mode Background Setup
        screen.set_style_bg_color(lv.color_hex(0x121212), 0)
        screen.set_style_bg_opa(lv.OPA.COVER, 0)

        # 2. Layout Container (Flex Column)
        container = lv.obj(screen)
        container.set_size(lv.pct(100), lv.pct(100))
        container.set_style_bg_opa(lv.OPA.TRANSP, 0)
        container.set_style_border_width(0, 0)
        container.set_style_pad_all(4, 0)
        container.set_style_pad_gap(4, 0)
        container.set_flex_flow(lv.FLEX_FLOW.COLUMN)

        # 3. Header Section (Title + Dynamic Status Indicator)
        header = lv.obj(container)
        header.set_size(lv.pct(100), 36)
        header.set_style_bg_color(lv.color_hex(0x1E1E1E), 0)
        header.set_style_border_color(lv.color_hex(0x333333), 0)
        header.set_style_border_width(1, 0)
        header.set_style_radius(4, 0)
        header.set_style_pad_hor(8, 0)
        header.set_flex_flow(lv.FLEX_FLOW.ROW)
        header.set_flex_align(
            lv.FLEX_ALIGN.SPACE_BETWEEN,
            lv.FLEX_ALIGN.CENTER,
            lv.FLEX_ALIGN.CENTER
        )

        title_label = lv.label(header)
        title_label.set_text("I2C Scanner")
        title_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)

        self.status_label = lv.label(header)
        self.status_label.set_text("Initializing...")
        self.status_label.set_style_text_color(lv.color_hex(0xAAAAAA), 0)

        # 4. Address Grid (16 x 8 Hex Table)
        self._build_table_grid(container)

        # 5. Hardware Acquisition via DeviceManager
        self.i2c = DeviceManager.getBus(type="i2c")
        if self.i2c is None:
            raise RuntimeError("I2C bus unavailable")

        self.setContentView(screen)

    def onStart(self, screen):
        # 6. Non-blocking Background Scan Timer (Every 2000 ms)
        self.scan_timer = lv.timer_create(self._perform_scan, 2000, None)
        self._perform_scan(None)  # Perform immediate first scan

    
    def onStop(self, screen):
        """Resource management & cleanup on Activity teardown."""
        # Deactivate and delete LVGL timer safely
        if self.scan_timer is not None:
            self.scan_timer._del()
            self.scan_timer = None

        # Clear references to prevent memory leaks
        self.i2c = None
        self.table = None
        self.status_label = None

    def _build_table_grid(self, parent):
        """Constructs and styles the 16x8 Hex grid table."""
        self.table = lv.table(parent)
        self.table.set_size(lv.pct(100), lv.pct(80))
        
        # Grid dimensions: 1 header row + 8 rows (00..70); 1 header col + 16 cols (0..F)
        self.table.set_row_count(9)
        self.table.set_column_count(17)

        # Styling adjustments for badge screen compactness
        self.table.set_style_bg_color(lv.color_hex(0x181818), 0)
        self.table.set_style_text_color(lv.color_hex(0xCCCCCC), 0)
        self.table.set_style_border_color(lv.color_hex(0x2A2A2A), 0)
        self.table.set_style_pad_all(1, lv.PART.ITEMS)

        # First column width (row headers: 00-70)
        self.table.set_column_width(0, 26)
        
        # Hex columns width (0 to F)
        for c in range(1, 17):
            self.table.set_column_width(c, 17)

        # Set Top Header Row Labels (0 to F)
        self.table.set_cell_value(0, 0, "")
        for col in range(16):
            self.table.set_cell_value(0, col + 1, f"{col:X}")

        # Set Left Header Column Labels (00 to 70) and initialize cells
        for row in range(8):
            row_idx = row + 1
            self.table.set_cell_value(row_idx, 0, f"{row * 16:02X}")
            for col in range(16):
                self.table.set_cell_value(row_idx, col + 1, "--")

    def _perform_scan(self, timer):
        """Periodic non-blocking bus scan and UI update callback."""
        if not self.i2c:
            self._update_status("I2C Offline", is_error=True)
            return

        try:
            # MicroPython standard I2C bus scan returning list of 7-bit addresses
            detected_addresses = set(self.i2c.scan())
            found_count = len(detected_addresses)

            # Update Hex Grid cells
            for row in range(8):
                row_idx = row + 1
                for col in range(16):
                    col_idx = col + 1
                    address = (row * 16) + col

                    # Exclude reserved I2C address ranges (0x00-0x07 and 0x78-0x7F)
                    if address < 0x08 or address > 0x77:
                        self.table.set_cell_value(row_idx, col_idx, "")
                    elif address in detected_addresses:
                        self.table.set_cell_value(row_idx, col_idx, f"{address:02X}")
                    else:
                        self.table.set_cell_value(row_idx, col_idx, "--")

            # Update status indicator
            if found_count == 0:
                self._update_status("No devices found", is_error=False, warning=True)
            else:
                self._update_status(f"Found: {found_count} device(s)", is_error=False)

        except Exception as err:
            self._update_status(f"Scan Fail: {err}", is_error=True)

    def _update_status(self, message, is_error=False, warning=False):
        """Updates status text and color-codes depending on state."""
        if not self.status_label:
            return

        self.status_label.set_text(message)

        if is_error:
            # Bright red for I2C errors
            self.status_label.set_style_text_color(lv.color_hex(0xFF5555), 0)
        elif warning:
            # Orange/Yellow when bus is OK but no devices present
            self.status_label.set_style_text_color(lv.color_hex(0xFFAA00), 0)
        else:
            # Green when active devices are detected
            self.status_label.set_style_text_color(lv.color_hex(0x55FF55), 0)
