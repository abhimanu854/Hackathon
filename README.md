# 🏎️ Air-Gapped Clipboard: Kinetic Transport Vehicle System

[![Platform](https://img.shields.io/badge/Platform-ESP32%20%7C%20Windows%20%7C%20Fedora%20Linux-blue.svg)](https://github.com/abhimanu854/Hackathon)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-yellow.svg)](https://www.python.org/)
[![Arduino](https://img.shields.io/badge/Framework-Arduino%20IDE%20%2F%20ESP32-00979D.svg)](https://www.arduino.cc/)

> **The Absurd Kinetic Security Solution**: An air-gapped clipboard system that intercepts local OS copy events on a Windows laptop, wipes the local clipboard, transmits the payload over an independent ESP32 Wi-Fi SoftAP network, physically drives a 4WD robot car across the room, and injects the data into a target Fedora Linux receiver's clipboard upon physical collision — assuming the goldfish-brained robot doesn't get disoriented and forget the payload!

---

## 📐 System Architecture Overview

```
 [ SENDER LAPTOP ]                             [ ESP32 ROBOT CAR ]                            [ RECEIVER LAPTOP ]
  (Windows 10/11)                             (AirGappedClipboard AP)                           (Fedora Linux)
+-----------------+                          +-----------------------+                        +------------------+
| User presses    |                          |  Access Point (SoftAP)|                        | Receiver App     |
| Ctrl+C          |                          |  IP: 192.168.4.1      |                        | (receiver.py)    |
|                 |                          +-----------------------+                        +------------------+
| client.py       |   HTTP POST /copy        | WebServer (Port 80)   |                                |
| 1. Intercepts   |------------------------->| 1. Stores text payload|                                |
| 2. Wipes OS Clip|  Payload: {"text":...}   | 2. Displays on OLED   |                                |
| 3. Starts Timer |                          | 3. Drives 4WD Forward |                                |
+-----------------+                          +-----------------------+                                |
                                                         |                                            |
                                                         | (Physical Transit)                         |
                                                         v                                            |
                                             [ Physical Collision ]                                   |
                                             IR Obstacle Sensor (Pin 33)                              |
                                             Triggers LOW on Docking Impact                           |
                                                         |                                            |
                                                         +--------------------------------------------+
                                                         | Goldfish Memory Check (1..100)             |
                                                         |                                            |
                                                         |---> 70% SUCCESS (>30): Status = "ARRIVED"  |
                                                         |     HTTP GET /status -> "ARRIVED" -------->|
                                                         |     HTTP GET /data   -> Downloads text ----> Inject to OS Clip
                                                         |                                            | (pyperclip.copy)
                                                         |---> 30% FAILURE (<=30): Status = "FAILED"  |
                                                               ( O_o ) "Uhh... I forgot."             |
                                                               HTTP GET /status -> "FAILED" ---------> Log Memory Loss
```

---

## 📁 Repository Directory Layout

```text
air-gapped-clipboard/
├── client_hijacker/              # Client Applications (Sender & Receiver)
│   ├── config.py                 # Central IP and HTTP endpoint configurations
│   ├── client.py                 # Windows Sender App (Ctrl+C interceptor + Tkinter GUI)
│   ├── receiver.py               # Fedora Linux Receiver App (Arrival Radar + Clipboard Injector)
│   ├── main.py                   # Unified Desktop Client Entry Point
│   └── requirements.txt          # Python dependencies (requests, pyperclip, keyboard)
│
├── esp32_firmware/               # ESP32 Microcontroller Firmware (Arduino IDE)
│   └── esp32_firmware.ino        # Master sketch (.ino) - Goldfish Memory, WebServer, OLED, L298N, IR Sensor
│
└── README.md                     # Comprehensive Master Documentation
```

---

## 🔌 Hardware Setup & Pin Wiring

The kinetic vehicle is built on a 4WD robot car chassis powered by an ESP32 microcontroller, an L298N dual H-bridge motor driver, a 0.96" I2C SSD1306 OLED display, and an active-LOW IR Obstacle Sensor bumper.

### Pin Connections Table

| Component | ESP32 GPIO Pin | Function / Wire Details |
| :--- | :--- | :--- |
| **L298N IN1** | `GPIO 26` | Left Motors Forward Direction |
| **L298N IN2** | `GPIO 27` | Left Motors Reverse Direction |
| **L298N IN3** | `GPIO 14` | Right Motors Forward Direction |
| **L298N IN4** | `GPIO 12` | Right Motors Reverse Direction |
| **IR Sensor OUT** | `GPIO 33` | Bumper Arrival Sensor (Active LOW on collision) |
| **OLED SDA** | `GPIO 21` | I2C Data Line (SSD1306) |
| **OLED SCL** | `GPIO 22` | I2C Clock Line (SSD1306) |
| **Power Supply** | `VIN / GND` | External 7.4V - 9V Battery Pack (L298N Power) |

---

## 📦 Prerequisite Installation

### 1. ESP32 Firmware (Arduino IDE)
1. Open **Arduino IDE** (v2.x recommended).
2. Go to **File -> Preferences** and add the ESP32 Board Manager URL:
   `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
3. Open **Tools -> Board -> Boards Manager**, search for `esp32`, and install **ESP32 Core v3.x**.
4. Open **Tools -> Manage Libraries** and install:
   - `Adafruit GFX Library` (by Adafruit)
   - `Adafruit SSD1306` (by Adafruit)
   *(Note: The sketch uses standard built-in `<WebServer.h>` and `<WiFi.h>` included in ESP32 Core v3.x).*
5. Open [`esp32_firmware/esp32_firmware.ino`](file:///c:/Users/harig/air-gapped-clipboard/esp32_firmware/esp32_firmware.ino), select **ESP32 Dev Module**, and click **Upload**.

---

### 2. Windows Sender Laptop Setup
1. Ensure Python 3.10+ is installed.
2. Open terminal/PowerShell inside `client_hijacker/`:
   ```bash
   pip install -r requirements.txt
   ```

---

### 3. Fedora Linux Receiver Laptop Setup
On Fedora Linux, `pyperclip` requires a system clipboard utility (`xclip` or `wl-clipboard` for Wayland) and Python Tkinter:

```bash
# Install system clipboard utilities and Tkinter on Fedora Linux
sudo dnf install -y python3-tkinter xclip wl-clipboard

# Install Python dependencies inside client_hijacker/
pip install requests pyperclip
```

---

## 🐟 The "Goldfish Memory" Feature

To add physical comedy and realistically simulate kinetic data loss, the ESP32 vehicle features the memory retention span of a **goldfish**:

1. **RNG Seeding**: In `setup()`, the random number generator is seeded with noise from floating analog pin 0: `randomSeed(analogRead(0))`.
2. **Impact Memory Roll**: The moment the IR bumper hits the receiving dock (`digitalRead(33) == LOW`), the ESP32 stops the motors and rolls `random(1, 101)`:
   - **70% Success (`roll > 30`)**: The robot remembers the payload! State transitions to `STATE_ARRIVED` and data is preserved for retrieval via `/data`.
   - **30% Memory Loss (`roll <= 30`)**: Goldfish memory loss! State transitions to `STATE_FAILED`, `storedData` is wiped clean (`""`), and the robot forgets why it drove across the room.
3. **Confused ASCII OLED Display**: When memory loss occurs, the OLED screen displays:
   ```text
      ( O_o )
    Uhh... I forgot.
   [ Goldfish Memory ]
   ```

---

## 🚀 Live Two-Laptop Demo Setup

### Step 1: Power On the ESP32 Vehicle
1. Connect the battery pack to power up the ESP32 car.
2. The OLED screen will display `"Status: IDLE"`.
3. The ESP32 will broadcast a standalone Wi-Fi Access Point:
   - **SSID:** `AirGappedClipboard`
   - **Password:** `12345678`
   - **Default IP:** `192.168.4.1`

### Step 2: Connect Both Laptops to the ESP32 Wi-Fi
- Connect **Laptop A (Windows Sender)** to `AirGappedClipboard`.
- Connect **Laptop B (Fedora Linux Receiver)** to `AirGappedClipboard`.

### Step 3: Launch the Receiver Radar on Laptop B (Fedora)
On Laptop B, run:
```bash
python3 client_hijacker/receiver.py
```
The application will begin continuously scanning `http://192.168.4.1/status`.

### Step 4: Launch the Sender Hijacker on Laptop A (Windows)
On Laptop A, run (with Administrator privileges if using global hotkeys):
```bash
python client_hijacker/client.py
```

### Step 5: Execute the Kinetic Copy/Paste!
1. On **Laptop A**, select any text and press `Ctrl+C`.
2. **Local Interception**: `client.py` captures the text, immediately **wipes Laptop A's clipboard**, and sends `HTTP POST /copy` to `192.168.4.1`.
3. **Kinetic Transit**: The ESP32 car powers its 4WD BO motors forward across the floor with the copied text printed on its OLED screen.
4. **Physical Collision**: The car collides with **Laptop B's dock**, driving IR sensor Pin 33 `LOW`.
5. **Data Injection**:
   - **70% Chance**: The robot remembers its payload! **Laptop B's** `receiver.py` fetches the text from `/data`, plays a chime, and **injects it directly into Laptop B's OS clipboard**. Press `Ctrl+V` on Laptop B to paste!
   - **30% Chance**: The robot gets confused upon impact! Its OLED displays `( O_o ) Uhh... I forgot.`, wipes its memory, and Laptop B logs a `PACKET DROPPED` physical memory failure!

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.