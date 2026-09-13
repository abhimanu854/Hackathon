"""
Air-Gapped Kinetic Clipboard v1.0 - Receiver App (receiver.py)
Cross-platform (Linux / Fedora / Windows / macOS) receiver app.
Continuously polls ESP32 status and injects payload into local OS clipboard on physical arrival.
"""

import time
import datetime
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
import pyperclip

import config

class AirGappedClipboardReceiver:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Air-Gapped Kinetic Clipboard - Receiver (Fedora / Cross-Platform)")
        self.root.geometry("680x600")
        self.root.minsize(600, 520)

        # State Variables
        self.esp32_ip = tk.StringVar(value=config.ESP32_IP)
        self.status_state = "SEARCHING"  # SEARCHING, TRANSITING, DOCKED, PACKET DROPPED, ERROR
        self.is_polling = False
        self.last_received_payload = ""

        # Configure Dark Theme Colors
        self.bg_color = "#181825"       # Dark Base
        self.card_bg = "#1E1E2E"        # Surface Card
        self.fg_color = "#CDD6F4"       # Text
        self.accent_color = "#89B4FA"   # Accent Blue
        self.status_idle_color = "#94E2D5"     # Cyan/Teal
        self.status_transit_color = "#F9E2AF"  # Amber
        self.status_docked_color = "#A6E3A1"   # Green
        self.status_failed_color = "#F38BA8"   # Red/Pink
        self.border_color = "#313244"

        self.root.configure(bg=self.bg_color)
        self._setup_styles()
        self._build_ui()
        self.start_radar()

        self.log_activity("Receiver initialized. Radar scanning for ESP32 transport vehicle...")

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background=self.bg_color, foreground=self.fg_color)
        style.configure("TFrame", background=self.bg_color)
        style.configure("Card.TFrame", background=self.card_bg, relief="flat")
        style.configure("TLabel", background=self.card_bg, foreground=self.fg_color, font=("Segoe UI", 10))
        style.configure("Header.TLabel", background=self.bg_color, foreground=self.accent_color, font=("Segoe UI", 16, "bold"))
        style.configure("SubHeader.TLabel", background=self.bg_color, foreground="#BAC2DE", font=("Segoe UI", 9, "italic"))
        style.configure("TEntry", fieldbackground="#313244", foreground=self.fg_color, insertcolor=self.fg_color)
        style.configure("TButton", background="#45475A", foreground=self.fg_color, font=("Segoe UI", 9, "bold"), borderwidth=0)
        style.map("TButton", background=[("active", "#585B70")])

    def _build_ui(self):
        # Header Frame
        header_frame = tk.Frame(self.root, bg=self.bg_color, pady=10)
        header_frame.pack(fill="x", px=15)

        lbl_title = ttk.Label(header_frame, text="Air-Gapped Kinetic Clipboard: RECEIVER", style="Header.TLabel")
        lbl_title.pack(anchor="w")

        lbl_subtitle = ttk.Label(
            header_frame, 
            text="Physical Arrival Radar & Local Clipboard Injection Engine", 
            style="SubHeader.TLabel"
        )
        lbl_subtitle.pack(anchor="w")

        # Connection Card
        conn_card = tk.Frame(self.root, bg=self.card_bg, bd=1, relief="solid", highlightbackground=self.border_color)
        conn_card.pack(fill="x", px=15, py=8)

        conn_inner = tk.Frame(conn_card, bg=self.card_bg, padx=12, pady=10)
        conn_inner.pack(fill="x")

        lbl_ip = tk.Label(conn_inner, text="ESP32 Robot IP:", bg=self.card_bg, fg=self.fg_color, font=("Segoe UI", 10, "bold"))
        lbl_ip.pack(side="left", px=(0, 10))

        entry_ip = ttk.Entry(conn_inner, textvariable=self.esp32_ip, width=20, font=("Consolas", 10))
        entry_ip.pack(side="left", px=(0, 15))

        btn_ping = ttk.Button(conn_inner, text="Test Connection", command=self.test_connection)
        btn_ping.pack(side="left")

        # Telemetry & Status Display Grid Frame
        telemetry_frame = tk.Frame(self.root, bg=self.bg_color)
        telemetry_frame.pack(fill="x", px=15, py=5)

        # Status Display Card
        status_card = tk.Frame(telemetry_frame, bg=self.card_bg, bd=1, relief="solid", highlightbackground=self.border_color)
        status_card.pack(side="left", fill="both", expand=True, px=(0, 5), py=5)

        tk.Label(status_card, text="RADAR STATUS", bg=self.card_bg, fg="#A6ADC8", font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
        
        self.lbl_status_badge = tk.Label(
            status_card, 
            text="SEARCHING", 
            bg=self.card_bg, 
            fg=self.status_idle_color, 
            font=("Segoe UI", 14, "bold")
        )
        self.lbl_status_badge.pack(anchor="w", padx=10, pady=(0, 8))

        # Payload Display Card
        payload_card = tk.Frame(self.root, bg=self.card_bg, bd=1, relief="solid", highlightbackground=self.border_color)
        payload_card.pack(fill="x", px=15, py=5)

        payload_inner = tk.Frame(payload_card, bg=self.card_bg, padx=10, pady=8)
        payload_inner.pack(fill="x")

        tk.Label(payload_inner, text="INJECTED PAYLOAD PREVIEW:", bg=self.card_bg, fg="#A6ADC8", font=("Segoe UI", 8, "bold")).pack(anchor="w")
        
        self.lbl_payload_preview = tk.Label(
            payload_inner, 
            text="[Awaiting Physical Vehicle Arrival...]", 
            bg=self.card_bg, 
            fg="#A6ADC8", 
            font=("Consolas", 9, "italic"),
            anchor="w"
        )
        self.lbl_payload_preview.pack(fill="x", pady=(2, 0))

        # Activity Log Frame
        log_frame = tk.Frame(self.root, bg=self.card_bg, bd=1, relief="solid", highlightbackground=self.border_color)
        log_frame.pack(fill="both", expand=True, px=15, py=10)

        log_inner = tk.Frame(log_frame, bg=self.card_bg, padx=10, pady=8)
        log_inner.pack(fill="both", expand=True)

        tk.Label(log_inner, text="RADAR & INJECTION ACTIVITY LOG", bg=self.card_bg, fg="#A6ADC8", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 5))

        self.txt_log = scrolledtext.ScrolledText(
            log_inner, 
            bg="#11111B", 
            fg="#CDD6F4", 
            insertbackground="white", 
            font=("Consolas", 9),
            state="disabled",
            wrap="word",
            bd=0
        )
        self.txt_log.pack(fill="both", expand=True)

    def log_activity(self, message: str):
        def _log():
            timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            log_line = f"[{timestamp}] {message}\n"
            self.txt_log.config(state="normal")
            self.txt_log.insert(tk.END, log_line)
            self.txt_log.see(tk.END)
            self.txt_log.config(state="disabled")
        
        self.root.after(0, _log)

    def update_status(self, new_status: str, detail_text: str = ""):
        def _update():
            self.status_state = new_status
            display_text = new_status
            if detail_text:
                display_text = f"{new_status} ({detail_text})"

            color_map = {
                "SEARCHING": self.status_idle_color,
                "IDLE": self.status_idle_color,
                "TRANSITING": self.status_transit_color,
                "DOCKED": self.status_docked_color,
                "PACKET DROPPED": self.status_failed_color,
                "ERROR": self.status_failed_color
            }

            badge_color = color_map.get(new_status, self.fg_color)
            self.lbl_status_badge.config(text=display_text, fg=badge_color)

        self.root.after(0, _update)

    def update_payload_preview(self, text: str):
        def _update():
            if not text:
                self.lbl_payload_preview.config(text="[Awaiting Physical Vehicle Arrival...]", fg="#A6ADC8")
            else:
                length = len(text)
                snippet = text[:30].replace("\n", " ")
                display_text = f"📋 Injected ({length} chars): \"{snippet}...\""
                self.lbl_payload_preview.config(text=display_text, fg=self.status_docked_color)
        
        self.root.after(0, _update)

    def test_connection(self):
        ip = self.esp32_ip.get().strip()
        url = f"http://{ip}{config.STATUS_ENDPOINT}"
        self.log_activity(f"Testing ping connection to {url}...")

        def _worker():
            try:
                resp = requests.get(url, timeout=3.0)
                if resp.status_code == 200:
                    status_val = resp.text.strip()
                    self.log_activity(f"Ping SUCCESS! ESP32 Online. Current Status: {status_val}")
                    messagebox.showinfo("Ping Success", f"Connected to ESP32 at {ip}!\nCurrent Status: {status_val}")
                else:
                    self.log_activity(f"Ping Warning: HTTP {resp.status_code}")
            except Exception as e:
                self.log_activity(f"Ping Error: Failed to reach ESP32 at {ip}. {e}")
                messagebox.showerror("Connection Error", f"Unable to reach ESP32 at {ip}.")

        threading.Thread(target=_worker, daemon=True).start()

    def start_radar(self):
        """Start background radar polling thread."""
        self.is_polling = True
        threading.Thread(target=self._radar_loop, daemon=True).start()

    def _radar_loop(self):
        """Continuously poll ESP32 status endpoint."""
        last_handled_state = ""

        while self.is_polling:
            time.sleep(config.POLL_INTERVAL_SEC)
            ip = self.esp32_ip.get().strip()
            status_url = f"http://{ip}{config.STATUS_ENDPOINT}"
            data_url = f"http://{ip}{config.DATA_ENDPOINT}"

            try:
                resp = requests.get(status_url, timeout=2.0)
                if resp.status_code == 200:
                    esp_status = resp.text.strip().upper()

                    if esp_status == "TRANSIT" and last_handled_state != "TRANSIT":
                        last_handled_state = "TRANSIT"
                        self.update_status("TRANSITING", "Car In Motion")
                        self.log_activity("RADAR ALERT: Vehicle dispatched! In kinetic transit...")

                    elif esp_status == "ARRIVED" and last_handled_state != "ARRIVED":
                        last_handled_state = "ARRIVED"
                        self.log_activity("VEHICLE ARRIVED! Collided with receiving dock. Fetching payload...")
                        self._fetch_and_inject_payload(data_url)

                    elif esp_status == "FAILED" and last_handled_state != "FAILED":
                        last_handled_state = "FAILED"
                        self.log_activity("PACKET DROPPED! Physical data corruption occurred on collision.")
                        self.update_status("PACKET DROPPED", "Data Loss")
                        self.update_payload_preview("")

                    elif esp_status == "IDLE" and last_handled_state != "IDLE":
                        last_handled_state = "IDLE"
                        self.update_status("SEARCHING", "Waiting for Next Transfer")

            except requests.exceptions.RequestException:
                if last_handled_state != "OFFLINE":
                    last_handled_state = "OFFLINE"
                    self.update_status("SEARCHING", "Scanning for Access Point...")

    def _fetch_and_inject_payload(self, data_url: str):
        """Retrieve payload from ESP32 and inject into local system clipboard."""
        try:
            resp = requests.get(data_url, timeout=5.0)
            if resp.status_code == 200:
                payload = resp.text
                self.last_received_payload = payload

                # Inject into local OS clipboard
                pyperclip.copy(payload)

                self.update_status("DOCKED", "Payload Injected to Clipboard")
                self.update_payload_preview(payload)
                self.log_activity(f"INJECTION SUCCESS: Injected {len(payload)} bytes into system clipboard! Ready to Paste (Ctrl+V).")
            else:
                self.log_activity(f"Error retrieving payload: HTTP {resp.status_code}")
        except Exception as e:
            self.log_activity(f"Exception retrieving payload from ESP32: {e}")


def main():
    root = tk.Tk()
    app = AirGappedClipboardReceiver(root)
    root.mainloop()

if __name__ == "__main__":
    main()
