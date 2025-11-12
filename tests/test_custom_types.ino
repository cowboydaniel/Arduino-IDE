// Test sketch with custom types to verify prototype generation fix

struct PointControl {
  int pin;
  int state;
  unsigned long lastUpdate;
};

// Functions using the custom type - prototypes should NOT be generated
void initializePoint(PointControl& point);
void updatePoint(PointControl& point, unsigned long now);
int interpretState(const PointControl& point, int analogValue);

// Regular function with built-in types - prototype SHOULD be generated
void blinkLED(int pin, int duration);

PointControl myPoint;

void setup() {
  Serial.begin(9600);
  initializePoint(myPoint);
}

void loop() {
  unsigned long now = millis();
  updatePoint(myPoint, now);
  blinkLED(13, 500);
  delay(1000);
}

// Function implementations
void initializePoint(PointControl& point) {
  point.pin = 2;
  point.state = 0;
  point.lastUpdate = 0;
}

void updatePoint(PointControl& point, unsigned long now) {
  point.lastUpdate = now;
  point.state = interpretState(point, analogRead(point.pin));
}

int interpretState(const PointControl& point, int analogValue) {
  if (analogValue > 512) {
    return 1;
  }
  return 0;
}

void blinkLED(int pin, int duration) {
  digitalWrite(pin, HIGH);
  delay(duration / 2);
  digitalWrite(pin, LOW);
  delay(duration / 2);
}
