// Demo file showing inline suggestions feature
// This file demonstrates various suggestions that will appear

int sensorPin = 2;

void setup() {
  Serial.begin(9600);
  pinMode(13, OUTPUT);  // 💡 Tip: Use LED_BUILTIN instead

  digitalWrite(sensorPin, HIGH);  // 💡 Tip: Don't forget to set pinMode for pin 'sensorPin' in setup()

  pinMode(A0, INPUT);  // 💡 Note: pinMode is not required for analogRead() on analog pins
}

void loop() {
  // 💡 You're using Serial but haven't checked Serial Monitor
  Serial.println("Hello");

  digitalWrite(13, HIGH);  // 💡 Tip: Use LED_BUILTIN instead of hardcoding 13
  delay(1000);  // 💡 Tip: Consider using millis() instead of delay() for non-blocking code
  digitalWrite(13, LOW);
  delay(1000);

  int sensorValue = analogRead(A0);
  if (sensorValue > 500) {  // 💡 Tip: Consider using a named constant for threshold value 500
    digitalWrite(13, HIGH);
  }

  pinMode(7, OUTPUT);  // 💡 Tip: Consider using a named constant instead of pin 7
  digitalWrite(7, HIGH);
}
