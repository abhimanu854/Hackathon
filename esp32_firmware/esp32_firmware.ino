/*
  =============================================================================
  AIR-GAPPED CLIPBOARD: KINETIC TRANSPORT VEHICLE FIRMWARE
  Arduino IDE Compatible Master Sketch (esp32_firmware.ino)
  =============================================================================
  
  REQUIRED ARDUINO LIBRARIES (Install via Arduino Library Manager):
  1. Adafruit GFX Library (by Adafruit)
  2. Adafruit SSD1306 (by Adafruit)
  
  BUILT-IN ESP32 CORE LIBRARIES USED:
  - WiFi.h
  - WebServer.h (Standard built-in WebServer compatible with ESP32 Core v3.x)
  - Wire.h

  HARDWARE PIN MAPPING:
  - ESP32 Microcontroller (ESP32 Dev Module)
  - L298N Motor Driver Pins:
      IN1 -> GPIO 26
      IN2 -> GPIO 27
      IN3 -> GPIO 14
      IN4 -> GPIO 12
  - IR Obstacle Sensor:
      OUT -> GPIO 33 (Active LOW on obstacle detection)
  - 0.96-inch SSD1306 OLED Display (I2C):
      SDA -> GPIO 21
      SCL -> GPIO 22
  =============================================================================
*/

#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// --- Pin Definitions ---
// L298N Motor Driver Pins
#define IN1_PIN 26
#define IN2_PIN 27
#define IN3_PIN 14
#define IN4_PIN 12

// IR Obstacle Sensor Pin
#define IR_SENSOR_PIN 33

// OLED Display Pins (I2C)
#define SDA_PIN 21
#define SCL_PIN 22
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1

// --- Global Objects & State Variables ---
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
WebServer server(80);

enum RobotState {
    STATE_IDLE,
    STATE_TRANSIT,
    STATE_ARRIVED,
    STATE_FAILED
};

RobotState currentState = STATE_IDLE;
String storedData = "";

// --- Motor Control Helper Functions ---
void stopMotors() {
    digitalWrite(IN1_PIN, LOW);
    digitalWrite(IN2_PIN, LOW);
    digitalWrite(IN3_PIN, LOW);
    digitalWrite(IN4_PIN, LOW);
}

void driveForward() {
    // Drive all 4 wheels forward
    digitalWrite(IN1_PIN, HIGH);
    digitalWrite(IN2_PIN, LOW);
    digitalWrite(IN3_PIN, HIGH);
    digitalWrite(IN4_PIN, LOW);
}

// --- OLED Helper Functions ---
void displayIdleStatus() {
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.setTextWrap(true);
    display.println("Status: IDLE");
    display.display();
}

void displayTransitText(const String& text) {
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.setTextWrap(true);
    display.println("IN TRANSIT:");
    display.println(text);
    display.display();
}

void displayArrivedStatus() {
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.setTextWrap(true);
    display.println("Status: ARRIVED /");
    display.println("READY TO PASTE");
    display.display();
}

void displayFailedStatus() {
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.setTextWrap(true);
    display.println("PACKET DROPPED!");
    display.println("Try again.");
    display.display();
}

String getStatusString() {
    switch (currentState) {
        case STATE_TRANSIT:
            return "TRANSIT";
        case STATE_ARRIVED:
            return "ARRIVED";
        case STATE_FAILED:
            return "FAILED";
        case STATE_IDLE:
        default:
            return "IDLE";
    }
}

// Helper to process copy payload
void processCopyPayload(const String& payload) {
    storedData = payload;
    displayTransitText(storedData);
    currentState = STATE_TRANSIT;
    driveForward();
}

// --- Web Server Endpoint Handlers ---
void handleStatus() {
    server.send(200, "text/plain", getStatusString());
}

void handleCopy() {
    String payload = "";
    if (server.hasArg("text")) {
        payload = server.arg("text");
    } else if (server.hasArg("data")) {
        payload = server.arg("data");
    } else if (server.hasArg("plain")) {
        payload = server.arg("plain");
    }
    
    processCopyPayload(payload);
    server.send(200, "text/plain", "OK - TRANSIT STARTED");
}

void handleData() {
    String responsePayload = storedData;
    
    // Reset state and screen after paste / data retrieval
    currentState = STATE_IDLE;
    storedData = "";
    displayIdleStatus();
    
    server.send(200, "text/plain", responsePayload);
}

void setup() {
    Serial.begin(115200);

    // Seed random number generator for packet drop coin toss
    randomSeed(analogRead(0));

    // Initialize Motor Pins
    pinMode(IN1_PIN, OUTPUT);
    pinMode(IN2_PIN, OUTPUT);
    pinMode(IN3_PIN, OUTPUT);
    pinMode(IN4_PIN, OUTPUT);
    stopMotors();

    // Initialize IR Sensor Pin (Active LOW)
    pinMode(IR_SENSOR_PIN, INPUT);

    // Initialize I2C and OLED Display
    Wire.begin(SDA_PIN, SCL_PIN);
    if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
        // Fallback I2C address check if 0x3C fails
        display.begin(SSD1306_SWITCHCAPVCC, 0x3D);
    }
    
    displayIdleStatus();

    // Initialize Wi-Fi Access Point mode for air-gapped transport
    WiFi.mode(WIFI_AP_STA);
    WiFi.softAP("AirGappedClipboard", "12345678");
    Serial.print("Access Point IP: ");
    Serial.println(WiFi.softAPIP());

    // --- Register Web Server Endpoints ---
    server.on("/status", HTTP_GET, handleStatus);
    server.on("/copy", HTTP_POST, handleCopy);
    server.on("/data", HTTP_GET, handleData);

    server.begin();
    Serial.println("HTTP server started.");
}

void loop() {
    // Process incoming client HTTP requests
    server.handleClient();

    // Non-blocking IR Obstacle Sensor check during TRANSIT state
    if (digitalRead(IR_SENSOR_PIN) == LOW && currentState == STATE_TRANSIT) {
        stopMotors();

        // 50/50 probability coin toss for packet drop mechanic
        if (random(0, 100) > 50) {
            // SUCCESS (>50): Transit arrived successfully
            currentState = STATE_ARRIVED;
            displayArrivedStatus();
            Serial.println("IR Obstacle detected! Vehicle ARRIVED successfully.");
        } else {
            // FAILURE (<=50): Packet dropped
            currentState = STATE_FAILED;
            storedData = "";
            displayFailedStatus();
            Serial.println("IR Obstacle detected! PACKET DROPPED.");
        }
    }
}
