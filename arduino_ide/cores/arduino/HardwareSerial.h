/* HardwareSerial.h - Hardware serial stub */
#ifndef HardwareSerial_h
#define HardwareSerial_h

#include <inttypes.h>
#include "WString.h"

class HardwareSerial {
public:
    void begin(unsigned long baud) {}
    void begin(unsigned long baud, uint8_t config) {}
    void end() {}

    int available(void) { return 0; }
    int peek(void) { return -1; }
    int read(void) { return -1; }
    void flush(void) {}

    size_t write(uint8_t c) { return 1; }
    size_t write(const uint8_t *buffer, size_t size) { return size; }
    size_t write(const char *str) { return 0; }

    void print(const char *str) {}
    void print(char c) {}
    void print(int n, int base = DEC) {}
    void print(unsigned int n, int base = DEC) {}
    void print(long n, int base = DEC) {}
    void print(unsigned long n, int base = DEC) {}
    void print(double n, int digits = 2) {}
    void print(const String &s) {}

    void println(const char *str) {}
    void println(char c) {}
    void println(int n, int base = DEC) {}
    void println(unsigned int n, int base = DEC) {}
    void println(long n, int base = DEC) {}
    void println(unsigned long n, int base = DEC) {}
    void println(double n, int digits = 2) {}
    void println(const String &s) {}
    void println(void) {}

    operator bool() { return true; }
};

extern HardwareSerial Serial;

#endif
