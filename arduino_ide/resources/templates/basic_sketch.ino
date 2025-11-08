/*
  Basic Arduino Sketch

  This is a template for a basic Arduino program with setup and loop functions.
*/

void setup() {
  // Initialize serial communication at 9600 bits per second
  Serial.begin(9600);

  // Initialize digital pin LED_BUILTIN as an output
  pinMode(LED_BUILTIN, OUTPUT);

  Serial.println("Setup complete!");
}

void loop() {
  // Turn the LED on
  digitalWrite(LED_BUILTIN, HIGH);
  Serial.println("LED ON");
  delay(1000);  // Wait for 1 second

  // Turn the LED off
  digitalWrite(LED_BUILTIN, LOW);
  Serial.println("LED OFF");
  delay(1000);  // Wait for 1 second
}
