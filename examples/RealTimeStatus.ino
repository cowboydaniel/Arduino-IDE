/*
 * Real-time Status Display Example
 *
 * This sketch demonstrates how to send data to the Arduino IDE's
 * Real-time Status Display panel.
 *
 * The status display can show:
 * - Live variable values with trend indicators
 * - Memory usage (RAM and Flash)
 * - Custom metrics
 *
 * Protocol:
 * - VAR:name=value  - Update a variable
 * - MEM:RAM=45,FLASH=32 - Update memory usage percentages
 *
 * Author: Arduino IDE Modern
 * Date: 2025
 */

// Example variables to monitor
int counter = 0;
int ledState = LOW;
float temperature = 23.5;
int sensorValue = 0;

// Pin definitions
const int LED_PIN = 13;
const int SENSOR_PIN = A0;

// Timing
unsigned long lastUpdate = 0;
const unsigned long UPDATE_INTERVAL = 1000; // Update every 1 second

void setup() {
  // Initialize serial communication
  Serial.begin(9600);

  // Initialize pins
  pinMode(LED_PIN, OUTPUT);
  pinMode(SENSOR_PIN, INPUT);

  // Send startup message
  Serial.println("Real-time Status Example Started");
  Serial.println("Open Tools > Real-time Status to see live data");
  Serial.println("----------------------------------------");
}

void loop() {
  unsigned long currentTime = millis();

  // Update variables
  counter++;

  // Toggle LED every second
  if (currentTime - lastUpdate >= UPDATE_INTERVAL) {
    ledState = !ledState;
    digitalWrite(LED_PIN, ledState);

    // Read sensor
    sensorValue = analogRead(SENSOR_PIN);

    // Simulate temperature reading (with some variation)
    temperature = 20.0 + (sensorValue / 1024.0) * 15.0;

    // Send status updates to IDE
    sendStatusUpdate();

    lastUpdate = currentTime;
  }

  delay(10);
}

void sendStatusUpdate() {
  // Send variable updates
  Serial.print("VAR:counter=");
  Serial.println(counter);

  Serial.print("VAR:ledState=");
  Serial.println(ledState ? "HIGH" : "LOW");

  Serial.print("VAR:temp=");
  Serial.print(temperature, 1);
  Serial.println("°C");

  Serial.print("VAR:sensor=");
  Serial.println(sensorValue);

  // Calculate and send memory usage
  // Note: These are estimates for demonstration
  int freeRam = getFreeRam();
  int totalRam = 2048; // Arduino Uno has 2KB RAM
  int ramPercent = 100 - (freeRam * 100 / totalRam);

  // Flash usage is typically known at compile time
  // For demonstration, we'll use a fixed value
  int flashPercent = 35;

  Serial.print("MEM:RAM=");
  Serial.print(ramPercent);
  Serial.print(",FLASH=");
  Serial.println(flashPercent);
}

// Function to get free RAM
int getFreeRam() {
  extern int __heap_start, *__brkval;
  int v;
  return (int) &v - (__brkval == 0 ? (int) &__heap_start : (int) __brkval);
}

/*
 * Expected output in Real-time Status Display:
 *
 * ┌──────────────────────┐
 * │ Live Values          │
 * ├──────────────────────┤
 * │ counter: 42 [Graph]  │
 * │ ledState: HIGH       │
 * │ temp: 23.5°C ▲       │
 * │ sensor: 512          │
 * │                      │
 * │ Memory Usage         │
 * │ RAM:  ████░░ 45%     │
 * │ Flash: ███░░░ 35%    │
 * └──────────────────────┘
 *
 * Features:
 * - Variables update in real-time as Arduino sends data
 * - Trend indicators (▲▼) show if values are increasing/decreasing
 * - Memory bars show RAM and Flash usage
 * - Click [Graph] button to visualize variable history (future feature)
 * - Pause/Resume button to freeze updates
 * - Clear button to remove all variables
 */
