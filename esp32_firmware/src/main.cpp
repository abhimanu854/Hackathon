#include <Arduino.h>
#include <WiFi.h>
#include <ESPAsyncWebServer.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// --- Pin Definitions ---
// L298N Motor Driver Pins
#define IN1_PIN 26
#define IN2_PIN 27
#define IN3_PIN 33
#define IN4_PIN 32

// HC-SR04 Ultrasonic Sensor Pins
#define TRIG_PIN 5
#define ECHO_PIN 18

// OLED Display Pins (I2C)
#define SDA_PIN 21
#define SCL_PIN 22
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1

// --- Global Objects & Variables ---
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
AsyncWebServer server(80);

enum RobotState {
    STATE_IDLE,
    STATE_TRANSIT,
    STATE_ARRIVED,
    STATE_FAILED
};

RobotState currentState = STATE_IDLE;
String storedData = "";

// Non-blocking ultrasonic timer variables
unsigned long lastPingTime = 0;
const unsigned long PING_INTERVAL = 50; // Ping every 50ms

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

void setup() {
    Serial.begin(115200);

    // Seed random number generator
    randomSeed(analogRead(0));

    // Initialize Motor Pins
    pinMode(IN1_PIN, OUTPUT);
    pinMode(IN2_PIN, OUTPUT);
    pinMode(IN3_PIN, OUTPUT);
    pinMode(IN4_PIN, OUTPUT);
    stopMotors();

    // Initialize HC-SR04 Pins
    pinMode(TRIG_PIN, OUTPUT);
    pinMode(ECHO_PIN, INPUT);
    digitalWrite(TRIG_PIN, LOW);

    // Initialize I2C and OLED Display
    Wire.begin(SDA_PIN, SCL_PIN);
    if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
        // Fallback address check if 0x3C fails
        display.begin(SSD1306_SWITCHCAPVCC, 0x3D);
    }
    
    displayIdleStatus();

    // Initialize Wi-Fi Access Point mode for air-gapped transport
    WiFi.mode(WIFI_AP_STA);
    WiFi.softAP("AirGappedClipboard", "12345678");
    Serial.print("Access Point IP: ");
    Serial.println(WiFi.softAPIP());

    // --- Web Server Endpoints ---

    // 1. GET /status endpoint
    server.on("/status", HTTP_GET, [](AsyncWebServerRequest *request) {
        request->send(200, "text/plain", getStatusString());
    });

    // 2. POST /copy endpoint
    server.on("/copy", HTTP_POST, 
        [](AsyncWebServerRequest *request) {
            // Executed after body processing or for query/form params
            if (!request->_tempObject) {
                String payload = "";
                if (request->hasParam("text", true)) {
                    payload = request->getParam("text", true)->value();
                } else if (request->hasParam("text")) {
                    payload = request->getParam("text")->value();
                } else if (request->hasParam("data", true)) {
                    payload = request->getParam("data", true)->value();
                } else if (request->hasParam("data")) {
                    payload = request->getParam("data")->value();
                }
                processCopyPayload(payload);
                request->send(200, "text/plain", "OK - TRANSIT STARTED");
            }
        }, 
        nullptr, 
        [](AsyncWebServerRequest *request, uint8_t *data, size_t len, size_t index, size_t total) {
            static String bodyBuffer = "";
            if (index == 0) {
                bodyBuffer = "";
                request->_tempObject = (void*)1;
            }
            for (size_t i = 0; i < len; i++) {
                bodyBuffer += (char)data[i];
            }
            if (index + len == total) {
                processCopyPayload(bodyBuffer);
                request->send(200, "text/plain", "OK - TRANSIT STARTED");
            }
        }
    );

    // 3. GET /data endpoint
    server.on("/data", HTTP_GET, [](AsyncWebServerRequest *request) {
        String responsePayload = storedData;
        
        // Reset state and screen after paste / data retrieval
        currentState = STATE_IDLE;
        storedData = "";
        displayIdleStatus();
        
        request->send(200, "text/plain", responsePayload);
    });

    server.begin();
    Serial.println("HTTP server started.");
}

void loop() {
    unsigned long currentMillis = millis();

    // Non-blocking ultrasonic distance measurement trigger
    if (currentMillis - lastPingTime >= PING_INTERVAL) {
        lastPingTime = currentMillis;

        // Trigger HC-SR04 pulse
        digitalWrite(TRIG_PIN, LOW);
        delayMicroseconds(2);
        digitalWrite(TRIG_PIN, HIGH);
        delayMicroseconds(10);
        digitalWrite(TRIG_PIN, LOW);

        // Read echo duration with a 25ms timeout (~400cm max range)
        long duration = pulseIn(ECHO_PIN, HIGH, 25000);
        float distanceCm = 999.0;

        if (duration > 0) {
            distanceCm = (duration * 0.0343f) / 2.0f;
        }

        // Crash prevention & arrival logic with 50% packet loss probability
        if (currentState == STATE_TRANSIT && distanceCm > 0.0f && distanceCm < 5.0f) {
            stopMotors();

            // 50/50 probability check
            if (random(0, 100) > 50) {
                // SUCCESS (>50): Keep current behavior
                currentState = STATE_ARRIVED;
                displayArrivedStatus();
                Serial.println("Obstacle detected! Vehicle ARRIVED successfully.");
            } else {
                // FAILURE (<=50): Packet dropped
                currentState = STATE_FAILED;
                storedData = "";
                displayFailedStatus();
                Serial.println("Obstacle detected! PACKET DROPPED.");
            }
        }
    }
}

