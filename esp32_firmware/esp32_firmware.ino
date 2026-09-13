/*
  =============================================================================
  AIR-GAPPED CLIPBOARD: KINETIC TRANSPORT VEHICLE FIRMWARE
  Arduino IDE Compatible Master Sketch (esp32_firmware.ino)
  =============================================================================
  
  FEATURE: "GOLDFISH MEMORY" EDITION 🐟
  This robot car possesses the memory retention span of a goldfish (3-5 seconds max).
  If kinetic transit takes too long or a random distraction occurs mid-transit,
  the ESP32 literally forgets what text payload it was carrying, wipes its memory,
  and displays a confused face on its OLED display.

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

// Goldfish Memory Timer Variables (Short-Term Memory Loss Engine)
unsigned long transitStartTime = 0;
unsigned long goldfishAttentionSpan = 4000; // Robot forgets everything after 3-5 seconds!

// --- Motor Control Helper Functions ---
void stopMotors() {
    digitalWrite(IN1_PIN, LOW);
    digitalWrite(IN2_PIN, LOW);
    digitalWrite(IN3_PIN, LOW);
    digitalWrite(IN4_PIN, LOW);
}

void driveForward() {
    // Drive all 4 wheels forward blindly
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
    display.println("Waiting for copy...");
    display.display();
}

void displayTransitText(const String& text) {
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.setTextWrap(true);
    display.println("IN TRANSIT (Thinking):");
    display.println(text);
    display.display();
}

void displayArrivedStatus() {
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.setTextWrap(true);
    display.println("Status: ARRIVED!");
    display.println("I remembered!");
    display.println("READY TO PASTE");
    display.display();
}

// Humorous Goldfish Memory Loss Screen
void displayFailedStatus() {
    display.clearDisplay();
    display.setTextSize(2);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(20, 4);
    display.println("( O_o )"); // Stupid confused ASCII face
    
    display.setTextSize(1);
    display.setCursor(12, 32);
    display.println("Uhh... I forgot.");
    display.setCursor(4, 48);
    display.println("[ Goldfish Memory ]");
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
    
    // Record start of transit & randomize goldfish attention span (3.0s to 5.0s)
    transitStartTime = millis();
    goldfishAttentionSpan = random(3000, 5000); 
    
    Serial.print("Payload received! Goldfish memory timer set to ");
    Serial.print(goldfishAttentionSpan);
    Serial.println(" ms.");

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
    storedData = ""; // Memory wiped clean after retrieval!
    displayIdleStatus();
    
    server.send(200, "text/plain", responsePayload);
}

void setup() {
    Serial.begin(115200);

    // Seed random number generator using floating analog noise
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
    Serial.println("HTTP server started. Ready for goldfish transport.");
}

void loop() {
    // Process incoming client HTTP requests
    server.handleClient();

    // --- GOLDFISH MEMORY ENGINE ---
    if (currentState == STATE_TRANSIT) {
        unsigned long currentMillis = millis();

        // 1. Check if the robot's short-term memory expired mid-transit!
        if (currentMillis - transitStartTime >= goldfishAttentionSpan) {
            stopMotors();
            currentState = STATE_FAILED;
            storedData = ""; // LITERAL MEMORY WIPE: Robot forgot what it was holding!
            displayFailedStatus();
            Serial.println("GOLDFISH BRAIN TRIGGERED: Robot drove for too long, got distracted, and forgot the payload!");
            return;
        }

        // 2. Check if IR Obstacle Sensor triggered physical arrival
        if (digitalRead(IR_SENSOR_PIN) == LOW) {
            stopMotors();

            // Random distraction check on collision: Did the bump make it forget?
            if (random(0, 100) > 40) {
                // SUCCESS: Robot actually remembered!
                currentState = STATE_ARRIVED;
                displayArrivedStatus();
                Serial.println("Miracle! Robot bumped into target and remembered the payload.");
            } else {
                // FAILURE: Impact caused instant memory wipe!
                currentState = STATE_FAILED;
                storedData = ""; // Payload erased!
                displayFailedStatus();
                Serial.println("BLANK STARE: Robot hit the receiver, but forgot why it came here!");
            }
        }
    }
}
