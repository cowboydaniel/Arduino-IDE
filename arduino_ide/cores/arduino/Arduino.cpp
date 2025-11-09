/*
  Arduino.cpp - Minimal Arduino core implementation
*/

#include "Arduino.h"

// Declare external setup and loop functions
extern "C" void setup(void);
extern "C" void loop(void);

// Main function required by AVR
int main(void) {
    setup();

    for (;;) {
        loop();
    }

    return 0;
}

// Digital I/O stubs
void pinMode(uint8_t pin, uint8_t mode) {
    // Stub implementation
    (void)pin;
    (void)mode;
}

void digitalWrite(uint8_t pin, uint8_t val) {
    // Stub implementation
    (void)pin;
    (void)val;
}

int digitalRead(uint8_t pin) {
    // Stub implementation
    (void)pin;
    return LOW;
}

// Analog I/O stubs
int analogRead(uint8_t pin) {
    // Stub implementation
    (void)pin;
    return 0;
}

void analogReference(uint8_t mode) {
    // Stub implementation
    (void)mode;
}

void analogWrite(uint8_t pin, int val) {
    // Stub implementation
    (void)pin;
    (void)val;
}

// Timing stubs
unsigned long millis(void) {
    // Stub implementation - would need timer setup
    return 0;
}

unsigned long micros(void) {
    // Stub implementation
    return 0;
}

void delay(unsigned long ms) {
    // Stub implementation - basic busy wait
    for (unsigned long i = 0; i < ms * 1000; i++) {
        __asm__ __volatile__("nop");
    }
}

void delayMicroseconds(unsigned int us) {
    // Stub implementation
    for (unsigned int i = 0; i < us; i++) {
        __asm__ __volatile__("nop");
    }
}

// Pulse measurement stubs
unsigned long pulseIn(uint8_t pin, uint8_t state, unsigned long timeout) {
    // Stub implementation
    (void)pin;
    (void)state;
    (void)timeout;
    return 0;
}

unsigned long pulseInLong(uint8_t pin, uint8_t state, unsigned long timeout) {
    // Stub implementation
    (void)pin;
    (void)state;
    (void)timeout;
    return 0;
}

// Shift operations stubs
void shiftOut(uint8_t dataPin, uint8_t clockPin, uint8_t bitOrder, uint8_t val) {
    // Stub implementation
    (void)dataPin;
    (void)clockPin;
    (void)bitOrder;
    (void)val;
}

uint8_t shiftIn(uint8_t dataPin, uint8_t clockPin, uint8_t bitOrder) {
    // Stub implementation
    (void)dataPin;
    (void)clockPin;
    (void)bitOrder;
    return 0;
}

// Interrupt stubs
void attachInterrupt(uint8_t interruptNum, void (*userFunc)(void), int mode) {
    // Stub implementation
    (void)interruptNum;
    (void)userFunc;
    (void)mode;
}

void detachInterrupt(uint8_t interruptNum) {
    // Stub implementation
    (void)interruptNum;
}

// Random number functions
void randomSeed(unsigned long seed) {
    if (seed != 0) {
        srand(seed);
    }
}

long random(long howbig) {
    if (howbig == 0) {
        return 0;
    }
    return rand() % howbig;
}

long random(long howsmall, long howbig) {
    if (howsmall >= howbig) {
        return howsmall;
    }
    long diff = howbig - howsmall;
    return random(diff) + howsmall;
}

// Math utility functions
long map(long x, long in_min, long in_max, long out_min, long out_max) {
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}
