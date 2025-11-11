// Test sketch to verify function prototype generation
// This sketch has functions called before they're defined

void setup() {
  Serial.begin(9600);
  calibrateSensors();
}

void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();

    switch (cmd) {
      case '1':
        testRawSensorReadings();
        break;
      case '2':
        testThresholdDetection();
        break;
      case '3':
        testLightOutputs();
        break;
      case '4':
        testCalibration();
        break;
      case '5':
        testFullSystem();
        break;
      case '6':
        continuousMonitor();
        break;
      case '7':
        displayBaselines();
        break;
    }
  }
}

// Function definitions below (called before defined)

void calibrateSensors() {
  Serial.println("Calibrating sensors...");
}

void testRawSensorReadings() {
  Serial.println("Testing raw sensor readings...");
}

void testThresholdDetection() {
  Serial.println("Testing threshold detection...");
}

void testLightOutputs() {
  Serial.println("Testing light outputs...");
}

void testCalibration() {
  Serial.println("Testing calibration...");
}

void testFullSystem() {
  Serial.println("Testing full system...");
}

void continuousMonitor() {
  Serial.println("Continuous monitoring...");
}

void displayBaselines() {
  Serial.println("Displaying baselines...");
}
