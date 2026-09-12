"""
Air-Gapped Kinetic Clipboard v1.0 - Client Hijacker Application
Windows 10/11 Desktop Client with Tkinter GUI, Global Clipboard Interception,
and Asynchronous ESP32 Telemetry Engine.
"""

import time
import datetime
import threading
import winsound
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
import pyperclip
import keyboard

import config

class AirGappedClipboardApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Air-Gapped Kinetic Clipboard v1.0")
        self.root.geometry("680x620")
        self.root.minsize(600, 550)

        # State Variables
        self.esp32_ip = tk.StringVar(value=config.ESP32_IP)
        self.status_state = "IDLE"  # IDLE, TRANSITING, DOCKED, PACKET DROPPED, ERROR
        self.is_transiting = False
        self.transit_start_time = None
        self.last_copied_payload = ""
        self.interceptor_active = True

        # Configure Dark Theme Colors
        self.bg_color = "#1E1E2E"       # Main background
        self.card_bg = "#282A36"        # Card surface
        self.fg_color = "#F8F8F2"       # Primary text
        self.accent_color = "#89B4FA"   # Accent blue
        self.status_idle_color = "#94E2D5"     # Cyan/Teal
        self.status_transit_color = "#F9E2AF"  # Amber
        self.status_docked_color = "#A6E3A1"   # Green
        self.status_failed_color = "#F38BA8"   # Red/Pink
        self.border_color = "#45475A"

        self.root.configure(bg=self.bg_color)
        self._setup_styles()
        self._build_ui()
        self._start_global_interceptor()
        self._start_timer_updater()

        self.log_activity("System initialized. Air-Gapped Kinetic Clipboard Ready.")

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background=self.bg_color, foreground=self.fg_color)
        style.configure("TFrame", background=self.bg_color)
        style.configure("Card.TFrame", background=self.card_bg, relief="flat")

        style.configure("TLabel", background=self.card_bg, foreground=self.fg_color, font=("Segoe UI", 10))
        style.configure("Header.TLabel", background=self.bg_color, foreground=self.accent_color, font=("Segoe UI", 16, "bold"))
        style.configure("SubHeader.TLabel", background=self.bg_color, foreground="#CDD6F4", font=("Segoe UI", 9, "italic"))
        
        style.configure("TEntry", fieldbackground="#313244", foreground=self.fg_color, insertcolor=self.fg_color)
        style.configure("TButton", background="#45475A", foreground=self.fg_color, font=("Segoe UI", 9, "bold"), borderwidth=0)
        style.map("TButton", background=[("active", "#585B70")])

    def _build_ui(self):
        # Top Header Frame
        header_frame = tk.Frame(self.root, bg=self.bg_color, pady=10)
        header_frame.pack(fill="x", px=15)

        lbl_title = ttk.Label(header_frame, text="Air-Gapped Kinetic Clipboard v1.0", style="Header.TLabel")
        lbl_title.pack(anchor="w")

        lbl_subtitle = ttk.Label(
            header_frame, 
            text="Physical Transport Interception & Telemetry Control System", 
            style="SubHeader.TLabel"
        )
        lbl_subtitle.pack(anchor="w")

        # Connection Configuration Card
        conn_card = tk.Frame(self.root, bg=self.card_bg, bd=1, relief="solid", highlightbackground=self.border_color)
        conn_card.pack(fill="x", px=15, py=10)

        conn_inner = tk.Frame(conn_card, bg=self.card_bg, padx=12, pady=10)
        conn_inner.pack(fill="x")

        lbl_ip = tk.Label(conn_inner, text="ESP32 Robot IP:", bg=self.card_bg, fg=self.fg_color, font=("Segoe UI", 10, "bold"))
        lbl_ip.pack(side="left", px=(0, 10))

        entry_ip = ttk.Entry(conn_inner, textvariable=self.esp32_ip, width=20, font=("Consolas", 10))
        entry_ip.pack(side="left", px=(0, 15))

        btn_ping = ttk.Button(conn_inner, text="Connect / Test Ping", command=self.test_connection)
        btn_ping.pack(side="left")

        # Telemetry & Dashboard Grid Frame
        telemetry_frame = tk.Frame(self.root, bg=self.bg_color)
        telemetry_frame.pack(fill="x", px=15, py=5)

        # Status Display Card
        status_card = tk.Frame(telemetry_frame, bg=self.card_bg, bd=1, relief="solid", highlightbackground=self.border_color)
        status_card.pack(side="left", fill="both", expand=True, px=(0, 5), py=5)

        tk.Label(status_card, text="TRANSFER STATUS", bg=self.card_bg, fg="#BAC2DE", font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
        
        self.lbl_status_badge = tk.Label(
            status_card, 
            text="IDLE", 
            bg=self.card_bg, 
            fg=self.status_idle_color, 
            font=("Segoe UI", 14, "bold")
        )
        self.lbl_status_badge.pack(anchor="w", padx=10, pady=(0, 8))

        # Live Timer Card
        timer_card = tk.Frame(telemetry_frame, bg=self.card_bg, bd=1, relief="solid", highlightbackground=self.border_color)
        timer_card.pack(side="left", fill="both", expand=True, px=(5, 5), py=5)

        tk.Label(timer_card, text="TRANSIT STOPWATCH", bg=self.card_bg, fg="#BAC2DE", font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
        
        self.lbl_timer = tk.Label(
            timer_card, 
            text="0.00 s", 
            bg=self.card_bg, 
            fg=self.accent_color, 
            font=("Consolas", 14, "bold")
        )
        self.lbl_timer.pack(anchor="w", padx=10, pady=(0, 8))

        # Security Payload Preview Card
        payload_card = tk.Frame(self.root, bg=self.card_bg, bd=1, relief="solid", highlightbackground=self.border_color)
        payload_card.pack(fill="x", px=15, py=5)

        payload_inner = tk.Frame(payload_card, bg=self.card_bg, padx=10, pady=8)
        payload_inner.pack(fill="x")

        tk.Label(payload_inner, text="SECURITY PAYLOAD PREVIEW:", bg=self.card_bg, fg="#BAC2DE", font=("Segoe UI", 8, "bold")).pack(anchor="w")
        
        self.lbl_payload_preview = tk.Label(
            payload_inner, 
            text="[No Payload In Transit]", 
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

        tk.Label(log_inner, text="ACTIVITY & TELEMETRY LOG", bg=self.card_bg, fg="#BAC2DE", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 5))

        self.txt_log = scrolledtext.ScrolledText(
            log_inner, 
            bg="#181825", 
            fg="#CDD6F4", 
            insertbackground="white", 
            font=("Consolas", 9),
            state="disabled",
            wrap="word",
            bd=0
        )
        self.txt_log.pack(fill="both", expand=True)

    def log_activity(self, message: str):
        """Thread-safe activity logger with ISO timestamps."""
        def _log():
            timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            log_line = f"[{timestamp}] {message}\n"
            self.txt_log.config(state="normal")
            self.txt_log.insert(tk.END, log_line)
            self.txt_log.see(tk.END)
            self.txt_log.config(state="disabled")
        
        self.root.after(0, _log)

    def update_status(self, new_status: str, detail_text: str = ""):
        """Thread-safe UI status badge and state update."""
        def _update():
            self.status_state = new_status
            display_text = new_status
            if detail_text:
                display_text = f"{new_status} ({detail_text})"

            color_map = {
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
        """Mask payload for security display."""
        def _update():
            if not text:
                self.lbl_payload_preview.config(text="[No Payload In Transit]", fg="#A6ADC8")
            else:
                length = len(text)
                preview_snippet = text[:15].replace("\n", " ")
                masked = f"🔒 [SECURITY MASKED: {length} chars] (\"{preview_snippet}...\")"
                self.lbl_payload_preview.config(text=masked, fg=self.accent_color)
        
        self.root.after(0, _update)

    def _start_timer_updater(self):
        """Update live transit timer every 50ms."""
        if self.is_transiting and self.transit_start_time:
            elapsed = time.time() - self.transit_start_time
            self.lbl_timer.config(text=f"{elapsed:.2f} s")
        elif not self.is_transiting and self.status_state == "IDLE":
            self.lbl_timer.config(text="0.00 s")
        
        self.root.after(50, self._start_timer_updater)

    def test_connection(self):
        """Test HTTP connectivity to ESP32 /status endpoint."""
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
                    self.log_activity(f"Ping HTTP Warning: Code {resp.status_code}")
            except Exception as e:
                self.log_activity(f"Ping Error: Failed to reach ESP32 at {ip}. {e}")
                messagebox.showerror("Connection Error", f"Unable to reach ESP32 at {ip}.\nPlease verify IP and Access Point connection.")

        threading.Thread(target=_worker, daemon=True).start()

    def _start_global_interceptor(self):
        """Start global clipboard listener using keyboard module and polling fallback."""
        def _on_copy_shortcut():
            if not self.interceptor_active:
                return
            # Small delay to ensure OS clipboard finishes writing
            time.sleep(0.05)
            self._handle_clipboard_interception()

        try:
            keyboard.add_hotkey('ctrl+c', _on_copy_shortcut)
            self.log_activity("Global Ctrl+C hotkey listener registered.")
        except Exception as e:
            self.log_activity(f"Hotkey Warning: Could not bind global keyboard hook ({e}). Using clipboard poll fallback.")

        # Fallback thread monitoring clipboard content changes
        def _clipboard_monitor():
            last_seen = ""
            while self.interceptor_active:
                try:
                    current_text = pyperclip.paste()
                    if current_text and current_text != last_seen and current_text != self.last_copied_payload:
                        last_seen = current_text
                        self._handle_clipboard_interception(current_text)
                except Exception:
                    pass
                time.sleep(0.2)

        threading.Thread(target=_clipboard_monitor, daemon=True).start()

    def _handle_clipboard_interception(self, text: str = None):
        """Capture clipboard, wipe local clipboard, send payload to ESP32, start transit."""
        if self.is_transiting:
            return  # Prevent starting multiple simultaneous transits

        try:
            if text is None:
                text = pyperclip.paste()
            
            if not text or text.strip() == "":
                return

            self.last_copied_payload = text

            # 1. Immediately wipe local OS clipboard to prevent early local paste
            pyperclip.copy("")
            self.log_activity(f"INTERCEPTED {len(text)} bytes from OS Clipboard. Local clipboard WIPED!")

            # 2. Update UI State & Timer
            self.is_transiting = True
            self.transit_start_time = time.time()
            self.update_status("TRANSITING", "In Physical Transit")
            self.update_payload_preview(text)

            # 3. Send HTTP POST to ESP32 /copy endpoint in background thread
            threading.Thread(target=self._send_payload_and_poll, args=(text,), daemon=True).start()

        except Exception as e:
            self.log_activity(f"Interception Error: {e}")

    def _send_payload_and_poll(self, payload: str):
        """Send payload to ESP32 and initiate polling loop."""
        ip = self.esp32_ip.get().strip()
        copy_url = f"http://{ip}{config.COPY_ENDPOINT}"
        status_url = f"http://{ip}{config.STATUS_ENDPOINT}"
        data_url = f"http://{ip}{config.DATA_ENDPOINT}"

        self.log_activity(f"Posting payload ({len(payload)} chars) to {copy_url}...")

        try:
            # Post text payload to ESP32
            response = requests.post(copy_url, data={"text": payload}, timeout=5.0)
            if response.status_code == 200:
                self.log_activity("ESP32 Acknowledged /copy! Robot car engaged in TRANSIT.")
            else:
                self.log_activity(f"Warning: /copy returned HTTP {response.status_code}")
        except Exception as e:
            self.log_activity(f"Connection Error posting payload to ESP32: {e}")
            self.update_status("ERROR", "Connection Lost")
            self.is_transiting = False
            return

        # 4. Initiate Polling Engine
        start_time = time.time()
        while self.is_transiting:
            time.sleep(config.POLL_INTERVAL_SEC)

            # Check timeout threshold
            elapsed = time.time() - start_time
            if elapsed > config.TIMEOUT_SEC:
                self.log_activity(f"Transit TIMEOUT ({config.TIMEOUT_SEC}s exceeded). Aborting.")
                self.update_status("ERROR", "Transit Timeout")
                self.is_transiting = False
                break

            try:
                status_resp = requests.get(status_url, timeout=3.0)
                if status_resp.status_code == 200:
                    esp_status = status_resp.text.strip().upper()
                    
                    if esp_status == "ARRIVED":
                        self.log_activity("ESP32 reported status: ARRIVED! Fetching payload from /data...")
                        self._handle_arrival_success(data_url)
                        break

                    elif esp_status == "FAILED":
                        self.log_activity("PHYSICAL DATA CORRUPTION: The car failed the transfer (PACKET DROPPED!).")
                        self._handle_arrival_failure()
                        break

                    elif esp_status == "TRANSIT":
                        # Still moving, continue polling
                        pass
                    else:
                        self.log_activity(f"Polling state: {esp_status}")

            except requests.exceptions.RequestException as req_err:
                self.log_activity(f"Polling Network Warning: {req_err}")

    def _handle_arrival_success(self, data_url: str):
        """Fetch payload, restore local clipboard, chime, update UI."""
        try:
            data_resp = requests.get(data_url, timeout=5.0)
            if data_resp.status_code == 200:
                received_payload = data_resp.text
                
                # Write back into local OS clipboard
                pyperclip.copy(received_payload)
                
                # Play Windows system chime
                try:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except Exception:
                    pass

                self.is_transiting = False
                self.update_status("DOCKED", "Payload Delivered")
                self.update_payload_preview("")
                self.log_activity(f"SUCCESS: Received {len(received_payload)} bytes from ESP32. Written back to system clipboard!")
                self.log_activity("Ready to PASTE (Ctrl+V)!")
            else:
                self.log_activity(f"Error fetching /data: HTTP {data_resp.status_code}")
                self.update_status("ERROR", "Data Retrieval Failed")
                self.is_transiting = False
        except Exception as e:
            self.log_activity(f"Error retrieving payload from /data: {e}")
            self.update_status("ERROR", "Data Retrieval Error")
            self.is_transiting = False

    def _handle_arrival_failure(self):
        """Handle 50% packet drop failure: keep clipboard empty and log error."""
        # Ensure clipboard remains blank
        pyperclip.copy("")
        
        try:
            winsound.MessageBeep(winsound.MB_ICONHAND)
        except Exception:
            pass

        self.is_transiting = False
        self.update_status("PACKET DROPPED", "Physical Collision / Loss")
        self.update_payload_preview("")
        self.log_activity("PHYSICAL DATA CORRUPTION: The car failed the transfer. Clipboard remains empty. Try copying again!")


def main():
    root = tk.Tk()
    app = AirGappedClipboardApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
