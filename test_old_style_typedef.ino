/*
 * Test old C-style typedef syntax compatibility
 * This should compile without errors after the preprocessor fix
 */

// Pin definitions
const int SENSOR_PIN = A0;
const int RELAY_PIN = 5;

// Forward declarations (appear before type definitions)
void initializeControl(ControlStruct& ctrl);
void updateControl(ControlStruct& ctrl);
const char* getStatus(const ControlStruct& ctrl);

// Old C-style typedef (name after closing brace)
typedef struct {
  const char* label;
  int sensorPin;
  int relayPin;
  int currentState;
  int lastReading;
  unsigned long lastDebounceTime;
} ControlStruct;

ControlStruct myControl = {
  "Test Control",
  SENSOR_PIN,
  RELAY_PIN,
  0,
  0,
  0
};

void setup() {
  Serial.begin(9600);
  pinMode(myControl.relayPin, OUTPUT);
  initializeControl(myControl);
  Serial.println("System Ready!");
}

void loop() {
  updateControl(myControl);
}

void initializeControl(ControlStruct& ctrl) {
  ctrl.lastDebounceTime = millis();
  Serial.print("Initialized: ");
  Serial.println(ctrl.label);
}

void updateControl(ControlStruct& ctrl) {
  int reading = analogRead(ctrl.sensorPin);

  if (reading != ctrl.lastReading) {
    ctrl.lastDebounceTime = millis();
  }

  ctrl.lastReading = reading;
}

const char* getStatus(const ControlStruct& ctrl) {
  return ctrl.label;
}
