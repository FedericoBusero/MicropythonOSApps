This repository is for apps for MicropytonOS

# Fri3d Badge Remote Control

A remote control application designed for the **Fri3d Badge 2024 & 2026**. This app lets you control external Wi-Fi devices—such as hovercrafts and blimps used in MasynMachien workshops—using the badge's hardware joystick and buttons over a WebSocket connection.

**Author:** FedericoBusero  
**Source Repositories:**
- [MicroPython OS App Source](https://github.com/FedericoBusero/MicropythonOSApps/tree/main/be.masynmachien.remotecontrol)
- [Wifi Blimp Source](https://github.com/FedericoBusero/Wifi-Blimp-Browser)
- [Wifi Hovercraft Source](https://github.com/FedericoBusero/Wifi-Hovercraft-Browser/)

---

## 🚀 How to Use

1. **Connect Wi-Fi:** Open the Wi-Fi app on your Fri3d Badge and connect to your target device's Wi-Fi Access Point (`SoftAP`).
2. **Control Movement:** Use the physical **joystick** to control direction and speed.
3. **Adjust Slider / Trim:**
   - Press **Y** to increase the slider value.
   - Press **B** to decrease the slider value.
   - Press **A** to reset the slider to its default center value (`180`).
4. **Status Display:** Incoming text messages from the target device are displayed directly on the top status bar.

---

## 📡 Communication Protocol

The badge connects to the target device's WebSocket server at `ws://192.168.4.1:82/`. It handles real-time, bi-directional messaging as follows:

| Message Type | Frequency | Format | Description |
| :--- | :--- | :--- | :--- |
| **Heartbeat** | Every 1 sec | `0` | Keeps the connection active |
| **Joystick** | Every 80 ms | `1:x,y` | Transmits coordinates (`-180` to `180`). Example: `1:180,45` |
| **Slider** | Every 160 ms | `2:v` | Transmits position (`0` to `360`, default `180`). Example: `2:180` |
| **Incoming** | As received | Text string | Displays incoming device notifications on the screen status bar |

---

## 🛠 Supported Hardware

- **Fri3d Badge 2024:** Uses direct ADC hardware pins for analog joystick readings and standard GPIO buttons.
- **Fri3d Badge 2026:** Communicates via I2C with the onboard CH32 coprocessor for button and analog joystick input.

*The hardware version is automatically detected at startup.*
