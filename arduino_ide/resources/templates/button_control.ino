/*
  Button Control Template

  Debounced button input with LED control.
*/

// Pin definitions
const int BUTTON_PIN = 2;
const int LED_PIN = 13;

// Variables
int buttonState = 0;
int lastButtonState = 0;
int ledState = LOW;

// Debounce variables
unsigned long lastDebounceTime = 0;
unsigned long debounceDelay = 50;

void setup() {
  // Initialize serial communication
  Serial.begin(9600);

  // Configure pins
  pinMode(BUTTON_PIN, INPUT_PULLUP);  // Use internal pull-up resistor
  pinMode(LED_PIN, OUTPUT);

  digitalWrite(LED_PIN, ledState);

  Serial.println("Button Control Initialized");
}

void loop() {
  // Read button state
  int reading = digitalRead(BUTTON_PIN);

  // Check if button state changed (with debouncing)
  if (reading != lastButtonState) {
    lastDebounceTime = millis();
  }

  if ((millis() - lastDebounceTime) > debounceDelay) {
    // If the button state has changed
    if (reading != buttonState) {
      buttonState = reading;

      // Only toggle the LED if the button is pressed (LOW due to pullup)
      if (buttonState == LOW) {
        ledState = !ledState;
        digitalWrite(LED_PIN, ledState);

        Serial.print("Button pressed! LED is now: ");
        Serial.println(ledState ? "ON" : "OFF");
      }
    }
  }

  lastButtonState = reading;
}
