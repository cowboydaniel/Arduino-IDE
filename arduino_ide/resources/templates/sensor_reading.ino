/*
  Sensor Reading Template

  Read analog sensor values and display them via serial.
*/

// Pin definitions
const int SENSOR_PIN = A0;
const int LED_PIN = 13;

// Variables
int sensorValue = 0;
float voltage = 0.0;

void setup() {
  // Initialize serial communication
  Serial.begin(9600);

  // Configure pins
  pinMode(LED_PIN, OUTPUT);
  pinMode(SENSOR_PIN, INPUT);

  Serial.println("Sensor Reader Initialized");
  Serial.println("Reading from pin A0...");
}

void loop() {
  // Read the analog sensor
  sensorValue = analogRead(SENSOR_PIN);

  // Convert to voltage (0-5V for most Arduino boards)
  voltage = sensorValue * (5.0 / 1023.0);

  // Display values
  Serial.print("Raw Value: ");
  Serial.print(sensorValue);
  Serial.print(" | Voltage: ");
  Serial.print(voltage);
  Serial.println("V");

  // Visual indicator
  if (sensorValue > 512) {
    digitalWrite(LED_PIN, HIGH);
  } else {
    digitalWrite(LED_PIN, LOW);
  }

  // Wait before next reading
  delay(500);
}
