/* WString.h - String class stub */
#ifndef WString_h
#define WString_h

#include <stdlib.h>
#include <string.h>

class String;

class __FlashStringHelper;
#define F(string_literal) (reinterpret_cast<const __FlashStringHelper *>(PSTR(string_literal)))

// Minimal String class stub for compilation
class String {
public:
    String(const char *cstr = "") {}
    String(const String &str) {}
    String(const __FlashStringHelper *str) {}
    ~String(void) {}

    unsigned int length(void) const { return 0; }
    char charAt(unsigned int index) const { return 0; }
    void setCharAt(unsigned int index, char c) {}
    char operator [] (unsigned int index) const { return 0; }
    char& operator [] (unsigned int index) { static char c; return c; }

    bool operator == (const String &rhs) const { return false; }
    bool operator != (const String &rhs) const { return true; }

    String & operator = (const String &rhs) { return *this; }
    String & operator += (const String &rhs) { return *this; }
    String operator + (const String &rhs) { return *this; }

    const char * c_str() const { return ""; }
};

#endif
