/*
 ==============================================================================================
  PROJECT: SMART SOIL TESTING & CROP OPTIMIZATION SYSTEM
  SUBTITLE: IoT-Based Soil Monitoring, Analysis and Crop Suitability Platform
  
  ESP32 FIRMWARE FOR 7-IN-1 RS485 / MODBUS RTU SOIL SENSOR
  Transmits Telemetry via Wi-Fi HTTP POST to Flask Backend API
 ==============================================================================================
  
  HARDWARE WIRING ARCHITECTURE:
  ----------------------------------------------------------------------------------------------
  7-in-1 Soil Sensor   MAX485 Module          ESP32 Dev Board
  ------------------   -------------          ---------------
  VCC (6-30V DC) ----> External DC Power Supply (Check sensor datasheet: 9V-24V DC recommended)
  GND ----------------> External GND ---------> ESP32 GND (Common Ground Essential!)
  A (Yellow/Green) ---> MAX485 Pin 'A'
  B (Blue/White) -----> MAX485 Pin 'B'
                       MAX485 VCC -----------> ESP32 3.3V or 5V (MAX485 usually 5V, check board)
                       MAX485 GND -----------> ESP32 GND
                       MAX485 RO (RX Out) ---> ESP32 GPIO 16 (UART2 RX)
                       MAX485 DI (TX In)  ---> ESP32 GPIO 17 (UART2 TX)
                       MAX485 DE & RE -------> Tied together to ESP32 GPIO 4
  ----------------------------------------------------------------------------------------------
  IMPORTANT NETWORK NOTE:
  Do NOT use "localhost" or "127.0.0.1" for SERVER_URL.
  Use your computer's local Wi-Fi IP address (Find via 'ipconfig' on Windows).
  Example: "http://192.168.1.100:5000/api/soil-data"
 ==============================================================================================
*/

#include <WiFi.h>
#include <HTTPClient.h>

// ============================================================================================
// 1. NETWORK & BACKEND API CONFIGURATION (EDIT FOR YOUR SETUP)
// ============================================================================================
const char* WIFI_SSID       = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD   = "YOUR_WIFI_PASSWORD";

// Replace with your laptop/computer's local network IP where Flask is running
const char* SERVER_URL      = "http://192.168.1.100:5000/api/soil-data";

// Must match API_KEY in Flask .env or Settings page
const char* API_KEY         = "CHANGE_THIS";

// Unique identifier for this hardware unit
const char* DEVICE_ID       = "SOIL_001";

// Reading interval in milliseconds (e.g. 5000ms = 5 seconds)
const unsigned long SAMPLING_INTERVAL_MS = 5000;

// ============================================================================================
// 2. HARDWARE & RS485 UART CONFIGURATION
// ============================================================================================
#define RS485_RX_PIN        16      // ESP32 GPIO16 connects to MAX485 RO
#define RS485_TX_PIN        17      // ESP32 GPIO17 connects to MAX485 DI
#define RS485_DE_RE_PIN     4       // ESP32 GPIO4 controls MAX485 DE + RE tied together
#define RS485_BAUD_RATE     9600    // Sensor default baud rate (commonly 4800 or 9600)
#define SENSOR_SLAVE_ID     0x01    // Modbus slave address (default is usually 1)

// ============================================================================================
// 3. MODBUS REGISTER MAP CONFIGURATION (EASY TO CUSTOMIZE)
// ============================================================================================
// NOTE: Different 7-in-1 sensor manufacturers use different starting registers!
// Type A (Sequential 7 registers starting at 0x0000):
//   0x0000 = Moisture, 0x0001 = Temp, 0x0002 = EC, 0x0003 = pH, 0x0004 = N, 0x0005 = P, 0x0006 = K
// Type B (Sequential starting at 0x001E):
//   Adjust STARTING_REGISTER and READ_COUNT to match your sensor datasheet.
// ============================================================================================
const uint16_t MODBUS_START_REGISTER = 0x0000; // Starting register address
const uint16_t MODBUS_REGISTER_COUNT = 0x0007; // Read 7 holding registers

// Hardware serial port for RS485
HardwareSerial RS485Serial(2);

// Timing tracker
unsigned long lastSamplingTime = 0;

// Structure to store raw & parsed parameters
struct SoilParameters {
  float moisture;      // %
  float temperature;   // °C
  float ec;            // µS/cm
  float ph;            // pH scale
  float nitrogen;      // mg/kg
  float phosphorus;    // mg/kg
  float potassium;     // mg/kg
  bool  isValid;
};

// ============================================================================================
// MODBUS CRC16 CALCULATION (STANDARD RTU POLYNOMIAL 0xA001)
// ============================================================================================
uint16_t calculateModbusCRC(const uint8_t *buffer, uint8_t length) {
  uint16_t crc = 0xFFFF;
  for (uint8_t pos = 0; pos < length; pos++) {
    crc ^= (uint16_t)buffer[pos];
    for (uint8_t i = 8; i != 0; i--) {
      if ((crc & 0x0001) != 0) {
        crc >>= 1;
        crc ^= 0xA001;
      } else {
        crc >>= 1;
      }
    }
  }
  return crc;
}

// RS485 Transmit / Receive Mode Switching
void setRS485ModeTransmit() {
  digitalWrite(RS485_DE_RE_PIN, HIGH);
  delayMicroseconds(50);
}

void setRS485ModeReceive() {
  RS485Serial.flush(); // Ensure outgoing bytes are physically transmitted
  delayMicroseconds(50);
  digitalWrite(RS485_DE_RE_PIN, LOW);
}

// ============================================================================================
// MODBUS RTU QUERY EXECUTION & VALIDATION
// ============================================================================================
SoilParameters read7in1SoilSensor() {
  SoilParameters result = {0, 0, 0, 0, 0, 0, 0, false};

  // Build Modbus RTU Read Holding Registers Request (Function Code 0x03)
  // [Slave ID][Function 0x03][Start High][Start Low][Count High][Count Low][CRC Low][CRC High]
  uint8_t request[8];
  request[0] = SENSOR_SLAVE_ID;
  request[1] = 0x03; // Function code: Read Holding Registers
  request[2] = (MODBUS_START_REGISTER >> 8) & 0xFF;
  request[3] = MODBUS_START_REGISTER & 0xFF;
  request[4] = (MODBUS_REGISTER_COUNT >> 8) & 0xFF;
  request[5] = MODBUS_REGISTER_COUNT & 0xFF;

  uint16_t crc = calculateModbusCRC(request, 6);
  request[6] = crc & 0xFF;        // CRC LSB
  request[7] = (crc >> 8) & 0xFF; // CRC MSB

  // Clear serial input buffer
  while (RS485Serial.available()) {
    RS485Serial.read();
  }

  // Send request via RS485
  Serial.print("[RS485] Sending Modbus Query to Sensor ID ");
  Serial.println(SENSOR_SLAVE_ID);
  
  setRS485ModeTransmit();
  RS485Serial.write(request, 8);
  setRS485ModeReceive();

  // Expected response size: 
  // [Slave ID][Function 0x03][Byte Count (14)][Data: 14 bytes][CRC LSB][CRC MSB] = 19 bytes
  const uint8_t EXPECTED_RESPONSE_LEN = 3 + (MODBUS_REGISTER_COUNT * 2) + 2;
  uint8_t response[32];
  uint8_t bytesRead = 0;

  unsigned long startTime = millis();
  while ((millis() - startTime) < 1500) { // 1.5s timeout
    if (RS485Serial.available()) {
      response[bytesRead++] = RS485Serial.read();
      if (bytesRead >= EXPECTED_RESPONSE_LEN) {
        break;
      }
    }
  }

  if (bytesRead < EXPECTED_RESPONSE_LEN) {
    Serial.print("[RS485 ERROR] Timeout or incomplete response. Received bytes: ");
    Serial.println(bytesRead);
    return result;
  }

  // Validate CRC of incoming response
  uint16_t receivedCRC = response[bytesRead - 2] | (response[bytesRead - 1] << 8);
  uint16_t calculatedCRC = calculateModbusCRC(response, bytesRead - 2);

  if (receivedCRC != calculatedCRC) {
    Serial.println("[RS485 ERROR] CRC mismatch! Data packet corrupted.");
    return result;
  }

  // Validate Slave ID and Function
  if (response[0] != SENSOR_SLAVE_ID || response[1] != 0x03) {
    Serial.println("[RS485 ERROR] Unexpected Modbus Header or Exception code.");
    return result;
  }

  // Extract 16-bit register values
  // Moisture: value * 0.1 (%)
  int16_t rawMoisture = (response[3] << 8) | response[4];
  result.moisture = rawMoisture * 0.1f;

  // Temperature: value * 0.1 (°C) (Handle signed negative temperatures)
  int16_t rawTemp = (response[5] << 8) | response[6];
  result.temperature = rawTemp * 0.1f;

  // Electrical Conductivity: value (µS/cm)
  uint16_t rawEC = (response[7] << 8) | response[8];
  result.ec = (float)rawEC;

  // Soil pH: value * 0.1 (scale)
  uint16_t rawPH = (response[9] << 8) | response[10];
  result.ph = rawPH * 0.1f;

  // Nitrogen: value (mg/kg)
  uint16_t rawN = (response[11] << 8) | response[12];
  result.nitrogen = (float)rawN;

  // Phosphorus: value (mg/kg)
  uint16_t rawP = (response[13] << 8) | response[14];
  result.phosphorus = (float)rawP;

  // Potassium: value (mg/kg)
  uint16_t rawK = (response[15] << 8) | response[16];
  result.potassium = (float)rawK;

  result.isValid = true;
  return result;
}

// ============================================================================================
// WI-FI CONNECTION & RECONNECTION HANDLER
// ============================================================================================
void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.print("[WiFi] Connecting to SSID: ");
  Serial.println(WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long startAttempt = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - startAttempt) < 15000) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WiFi] Connected successfully!");
    Serial.print("[WiFi] IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n[WiFi ERROR] Failed to connect within timeout.");
  }
}

// ============================================================================================
// HTTP POST TELEMETRY TRANSMISSION TO FLASK BACKEND
// ============================================================================================
bool sendSoilDataToAPI(const SoilParameters &data) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[HTTP ERROR] Cannot transmit: Wi-Fi disconnected.");
    return false;
  }

  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", API_KEY);

  // Build JSON Payload
  char jsonBuffer[300];
  snprintf(jsonBuffer, sizeof(jsonBuffer),
    "{\"device_id\":\"%s\","
    "\"moisture\":%.1f,"
    "\"temperature\":%.1f,"
    "\"ec\":%.0f,"
    "\"ph\":%.1f,"
    "\"nitrogen\":%.0f,"
    "\"phosphorus\":%.0f,"
    "\"potassium\":%.0f}",
    DEVICE_ID,
    data.moisture,
    data.temperature,
    data.ec,
    data.ph,
    data.nitrogen,
    data.phosphorus,
    data.potassium
  );

  Serial.print("[HTTP POST] Destination: ");
  Serial.println(SERVER_URL);
  Serial.print("[HTTP POST] Payload: ");
  Serial.println(jsonBuffer);

  int httpResponseCode = http.POST(jsonBuffer);

  if (httpResponseCode > 0) {
    String responseString = http.getString();
    Serial.print("[HTTP SUCCESS] Code: ");
    Serial.print(httpResponseCode);
    Serial.print(" | Response: ");
    Serial.println(responseString);
    http.end();
    return (httpResponseCode == 200 || httpResponseCode == 201);
  } else {
    Serial.print("[HTTP ERROR] POST failed. Error code: ");
    Serial.println(httpResponseCode);
    http.end();
    return false;
  }
}

// ============================================================================================
// SETUP
// ============================================================================================
void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n=======================================================");
  Serial.println("  SMART SOIL TESTING & CROP OPTIMIZATION SYSTEM");
  Serial.println("  ESP32 7-in-1 RS485 Modbus RTU Telemetry Node");
  Serial.println("=======================================================");

  // Initialize MAX485 Control Pin
  pinMode(RS485_DE_RE_PIN, OUTPUT);
  setRS485ModeReceive();

  // Initialize RS485 Serial UART2 (GPIO 16 = RX, GPIO 17 = TX)
  RS485Serial.begin(RS485_BAUD_RATE, SERIAL_8N1, RS485_RX_PIN, RS485_TX_PIN);
  Serial.println("[RS485] UART2 Initialized on GPIO16(RX) and GPIO17(TX).");

  // Connect to Wi-Fi
  connectWiFi();
}

// ============================================================================================
// MAIN LOOP
// ============================================================================================
void loop() {
  // Maintain Wi-Fi connectivity
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  // Periodic sensor read and transmit
  if (millis() - lastSamplingTime >= SAMPLING_INTERVAL_MS) {
    lastSamplingTime = millis();

    Serial.println("\n--- [Reading 7-in-1 Soil Sensor] ---");
    SoilParameters soil = read7in1SoilSensor();

    if (soil.isValid) {
      Serial.printf("Moisture:    %.1f %%\n", soil.moisture);
      Serial.printf("Temperature: %.1f °C\n", soil.temperature);
      Serial.printf("EC:          %.0f µS/cm\n", soil.ec);
      Serial.printf("pH:          %.1f\n", soil.ph);
      Serial.printf("Nitrogen:    %.0f mg/kg\n", soil.nitrogen);
      Serial.printf("Phosphorus:  %.0f mg/kg\n", soil.phosphorus);
      Serial.printf("Potassium:   %.0f mg/kg\n", soil.potassium);

      // Transmit to Flask REST API
      sendSoilDataToAPI(soil);
    } else {
      Serial.println("[WARNING] Sensor read failed or sensor not responding.");
      Serial.println("Check: 1) Sensor 12V/24V power supply, 2) RS485 A/B polarity, 3) Modbus ID/Baud rate.");
    }
  }

  delay(50);
}
