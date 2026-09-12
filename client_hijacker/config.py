"""
Configuration settings for the Air-Gapped Kinetic Clipboard client application.
"""

# Default ESP32 IP Address (Access Point or Station mode IP)
ESP32_IP = "192.168.4.1"

# Polling and Timeout Settings
POLL_INTERVAL_SEC = 0.5   # Time between status poll requests in seconds
TIMEOUT_SEC = 60.0        # Maximum time to wait for transit completion in seconds

# ESP32 HTTP Endpoints
STATUS_ENDPOINT = "/status"
COPY_ENDPOINT = "/copy"
DATA_ENDPOINT = "/data"
