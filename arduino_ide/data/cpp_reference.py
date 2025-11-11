"""
C++ Language Reference Database
Comprehensive reference for C++ keywords, types, operators, and language features
"""

CPP_REFERENCE = {
    # ==================== DATA TYPES ====================

    "int": {
        "title": "int",
        "category": "Data Type",
        "description": "Integer data type for whole numbers",
        "syntax": "int variable_name;\nint variable_name = value;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Size is platform-dependent (typically 16 or 32 bits)",
            "⚠️  Arduino Uno: 16 bits (-32,768 to 32,767)",
            "⚠️  Overflow wraps around (32,767 + 1 = -32,768)"
        ],
        "tips": [
            "💡 Use 'long' for larger values",
            "💡 Use 'unsigned int' for 0-65,535 on Arduino Uno"
        ],
        "example": """int counter = 0;
int sensorValue = 512;
int temperature = -10;"""
    },

    "long": {
        "title": "long",
        "category": "Data Type",
        "description": "Long integer for larger whole numbers",
        "syntax": "long variable_name;\nlong variable_name = value;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Arduino: 32 bits (-2,147,483,648 to 2,147,483,647)",
            "⚠️  Takes more memory than int"
        ],
        "tips": [
            "💡 Use for millis() return values",
            "💡 Use unsigned long for 0 to 4,294,967,295"
        ],
        "example": """long bigNumber = 1000000;
unsigned long startTime = millis();"""
    },

    "float": {
        "title": "float",
        "category": "Data Type",
        "description": "Floating-point number for decimal values",
        "syntax": "float variable_name;\nfloat variable_name = value;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  32-bit, ~6-7 decimal digits precision",
            "⚠️  Arithmetic is slower than integer math",
            "⚠️  Avoid comparing floats with == (use range comparison)"
        ],
        "tips": [
            "💡 Use for sensor calculations and voltage conversions",
            "💡 Use 'f' suffix for float literals: 3.14f"
        ],
        "example": """float voltage = 3.3;
float temperature = 25.5f;
float pi = 3.14159;"""
    },

    "double": {
        "title": "double",
        "category": "Data Type",
        "description": "Double-precision floating-point number",
        "syntax": "double variable_name;\ndouble variable_name = value;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  On Arduino, double is same as float (32-bit)",
            "⚠️  On PC, double is 64-bit with higher precision"
        ],
        "tips": [
            "💡 For Arduino, prefer float to save confusion",
            "💡 On PC, use for high-precision calculations"
        ],
        "example": """double preciseValue = 3.141592653589793;
double result = 1.0 / 3.0;"""
    },

    "char": {
        "title": "char",
        "category": "Data Type",
        "description": "Single character or small integer (-128 to 127)",
        "syntax": "char variable_name;\nchar variable_name = 'c';",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  8-bit signed by default",
            "⚠️  Use single quotes for character literals: 'A'",
            "⚠️  Use double quotes for strings: \"Hello\""
        ],
        "tips": [
            "💡 Use unsigned char for 0-255",
            "💡 Can store ASCII characters or small numbers"
        ],
        "example": """char letter = 'A';
char newline = '\\n';
char buffer[32];"""
    },

    "bool": {
        "title": "bool",
        "category": "Data Type",
        "description": "Boolean value (true or false)",
        "syntax": "bool variable_name;\nbool variable_name = true;",
        "parameters": [],
        "common_values": [
            {"value": "true", "description": "Boolean true (non-zero)"},
            {"value": "false", "description": "Boolean false (zero)"}
        ],
        "warnings": [
            "⚠️  Internally stored as 1 byte (true = 1, false = 0)"
        ],
        "tips": [
            "💡 Use for state flags and conditions",
            "💡 More readable than int for true/false values"
        ],
        "example": """bool isRunning = true;
bool buttonPressed = false;
bool ledState = !ledState; // Toggle"""
    },

    "void": {
        "title": "void",
        "category": "Data Type",
        "description": "Indicates no value or no parameters",
        "syntax": "void function_name(void)\nvoid function_name()",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Cannot declare void variables",
            "⚠️  void functions don't return a value"
        ],
        "tips": [
            "💡 Use for functions that perform actions without returning data",
            "💡 setup() and loop() are void functions"
        ],
        "example": """void setup() {
  // Initialization code
}

void blinkLED() {
  digitalWrite(13, HIGH);
  delay(500);
  digitalWrite(13, LOW);
}"""
    },

    "byte": {
        "title": "byte",
        "category": "Data Type (Arduino)",
        "description": "8-bit unsigned integer (0 to 255)",
        "syntax": "byte variable_name;\nbyte variable_name = value;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Arduino-specific, equivalent to unsigned char",
            "⚠️  Range: 0 to 255 only (no negative values)"
        ],
        "tips": [
            "💡 Commonly used for raw sensor data",
            "💡 Use for small positive integers to save memory"
        ],
        "example": """byte brightness = 128;
byte buffer[64];
byte ipAddress[] = {192, 168, 1, 1};"""
    },

    "String": {
        "title": "String",
        "category": "Data Type (Arduino)",
        "description": "Arduino String object for text manipulation",
        "syntax": "String variable_name;\nString variable_name = \"text\";",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Uses dynamic memory allocation (can cause fragmentation)",
            "⚠️  May cause issues in long-running programs",
            "⚠️  Case-sensitive: 'String' is object, 'string' doesn't exist in Arduino"
        ],
        "tips": [
            "💡 For simple projects, String is convenient",
            "💡 For production code, prefer char arrays",
            "💡 Has many built-in methods: .length(), .substring(), etc."
        ],
        "example": """String message = "Hello";
String combined = message + " World";
int len = message.length();"""
    },

    # ==================== KEYWORDS & CONTROL FLOW ====================

    "if": {
        "title": "if Statement",
        "category": "Control Flow",
        "description": "Executes code block if condition is true",
        "syntax": "if (condition) {\n  // code\n}\nif (condition) statement;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Use == for comparison, not = (assignment)",
            "⚠️  Be careful with semicolons after condition"
        ],
        "tips": [
            "💡 Use braces {} even for single statements",
            "💡 Can chain with else if and else"
        ],
        "example": """if (temperature > 25) {
  digitalWrite(fan, HIGH);
}

if (buttonPressed == true) {
  Serial.println("Button!");
}"""
    },

    "else": {
        "title": "else Statement",
        "category": "Control Flow",
        "description": "Executes code when if condition is false",
        "syntax": "if (condition) {\n  // code\n} else {\n  // alternative code\n}",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Must follow an if statement",
            "⚠️  Watch for 'dangling else' with nested ifs"
        ],
        "tips": [
            "💡 Use else if for multiple conditions",
            "💡 else catches all remaining cases"
        ],
        "example": """if (value > 100) {
  Serial.println("High");
} else {
  Serial.println("Low");
}"""
    },

    "for": {
        "title": "for Loop",
        "category": "Control Flow",
        "description": "Repeats code block a specific number of times",
        "syntax": "for (init; condition; increment) {\n  // code\n}",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Infinite loop if condition never becomes false",
            "⚠️  Be careful with loop variable scope"
        ],
        "tips": [
            "💡 Common pattern: for (int i = 0; i < n; i++)",
            "💡 Can declare loop variable in initialization"
        ],
        "example": """for (int i = 0; i < 10; i++) {
  Serial.println(i);
}

for (int pin = 2; pin <= 8; pin++) {
  pinMode(pin, OUTPUT);
}"""
    },

    "while": {
        "title": "while Loop",
        "category": "Control Flow",
        "description": "Repeats code while condition is true",
        "syntax": "while (condition) {\n  // code\n}",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Can create infinite loop if condition never becomes false",
            "⚠️  Condition checked before each iteration"
        ],
        "tips": [
            "💡 Good for waiting for events",
            "💡 Use 'break' to exit early"
        ],
        "example": """while (digitalRead(button) == HIGH) {
  // Wait for button release
}

int count = 0;
while (count < 10) {
  Serial.println(count);
  count++;
}"""
    },

    "do": {
        "title": "do-while Loop",
        "category": "Control Flow",
        "description": "Executes code block at least once, then repeats while condition is true",
        "syntax": "do {\n  // code\n} while (condition);",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Always executes at least once (condition checked after)",
            "⚠️  Don't forget semicolon after while()"
        ],
        "tips": [
            "💡 Use when you need to run code at least once",
            "💡 Less common than regular while loop"
        ],
        "example": """int i = 0;
do {
  Serial.println(i);
  i++;
} while (i < 10);"""
    },

    "switch": {
        "title": "switch Statement",
        "category": "Control Flow",
        "description": "Multi-way branch based on value",
        "syntax": "switch (variable) {\n  case value1:\n    // code\n    break;\n  case value2:\n    // code\n    break;\n  default:\n    // code\n}",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Don't forget 'break' statements",
            "⚠️  Only works with integer types and char",
            "⚠️  Falls through to next case without break"
        ],
        "tips": [
            "💡 Use 'default' for unhandled cases",
            "💡 More efficient than multiple if-else for many cases"
        ],
        "example": """switch (command) {
  case 'A':
    motorForward();
    break;
  case 'B':
    motorBackward();
    break;
  default:
    motorStop();
}"""
    },

    "case": {
        "title": "case Label",
        "category": "Control Flow",
        "description": "Defines a case in a switch statement",
        "syntax": "case constant:\n  // code\n  break;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Must be inside a switch statement",
            "⚠️  Case values must be constants",
            "⚠️  Add break to prevent fall-through"
        ],
        "tips": [
            "💡 Multiple cases can share the same code",
            "💡 Can use character or integer constants"
        ],
        "example": """case 1:
case 2:
case 3:
  Serial.println("Low");
  break;
case 10:
  Serial.println("High");
  break;"""
    },

    "break": {
        "title": "break Statement",
        "category": "Control Flow",
        "description": "Exits from loop or switch statement",
        "syntax": "break;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Only exits innermost loop or switch",
            "⚠️  Doesn't exit functions (use return for that)"
        ],
        "tips": [
            "💡 Use to exit early from loops",
            "💡 Required in switch cases to prevent fall-through"
        ],
        "example": """for (int i = 0; i < 100; i++) {
  if (i == 50) {
    break; // Exit loop at 50
  }
}

switch (val) {
  case 1:
    doSomething();
    break; // Exit switch
}"""
    },

    "continue": {
        "title": "continue Statement",
        "category": "Control Flow",
        "description": "Skips rest of current loop iteration",
        "syntax": "continue;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Only affects current iteration",
            "⚠️  Loop continues with next iteration"
        ],
        "tips": [
            "💡 Use to skip processing for certain values",
            "💡 Loop condition is still checked"
        ],
        "example": """for (int i = 0; i < 10; i++) {
  if (i == 5) {
    continue; // Skip 5
  }
  Serial.println(i);
}"""
    },

    "return": {
        "title": "return Statement",
        "category": "Control Flow",
        "description": "Exits function and optionally returns a value",
        "syntax": "return;\nreturn value;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Must match function return type",
            "⚠️  Void functions use 'return;' without value",
            "⚠️  Exits immediately (subsequent code not executed)"
        ],
        "tips": [
            "💡 Can have multiple return statements",
            "💡 Good practice to return at end of function"
        ],
        "example": """int add(int a, int b) {
  return a + b;
}

void checkSensor() {
  if (error) {
    return; // Exit early
  }
  // Process sensor
}"""
    },

    # ==================== STORAGE CLASSES ====================

    "const": {
        "title": "const Qualifier",
        "category": "Storage Class",
        "description": "Makes variable read-only (constant)",
        "syntax": "const type name = value;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Must be initialized when declared",
            "⚠️  Cannot be modified after initialization",
            "⚠️  Better than #define for type safety"
        ],
        "tips": [
            "💡 Use for pin numbers and configuration values",
            "💡 Helps prevent accidental changes",
            "💡 May be stored in flash memory (saves RAM)"
        ],
        "example": """const int ledPin = 13;
const float pi = 3.14159;
const char* message = "Hello";"""
    },

    "static": {
        "title": "static Qualifier",
        "category": "Storage Class",
        "description": "Variable retains value between function calls, or limits scope to file",
        "syntax": "static type variable_name;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Initialized only once",
            "⚠️  Different behavior for local vs global variables"
        ],
        "tips": [
            "💡 Local static: preserves value between calls",
            "💡 Global static: limits visibility to current file",
            "💡 Useful for counting function calls"
        ],
        "example": """void countCalls() {
  static int count = 0;
  count++;
  Serial.println(count);
}
// Each call increments and displays"""
    },

    "volatile": {
        "title": "volatile Qualifier",
        "category": "Storage Class",
        "description": "Prevents compiler optimization for variables that can change unexpectedly",
        "syntax": "volatile type variable_name;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Required for variables modified in ISRs (interrupts)",
            "⚠️  Slightly reduces performance"
        ],
        "tips": [
            "💡 Use with interrupt service routines",
            "💡 Use with variables changed by hardware",
            "💡 Tells compiler value can change 'outside' normal flow"
        ],
        "example": """volatile bool buttonPressed = false;

void setup() {
  attachInterrupt(0, buttonISR, RISING);
}

void buttonISR() {
  buttonPressed = true;
}"""
    },

    # ==================== OPERATORS ====================

    "=": {
        "title": "Assignment Operator",
        "category": "Operator",
        "description": "Assigns value to variable",
        "syntax": "variable = value;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Don't confuse with == (comparison)",
            "⚠️  Assignment returns the assigned value"
        ],
        "tips": [
            "💡 Can chain assignments: a = b = c = 0;",
            "💡 Right side evaluated first"
        ],
        "example": """int x = 10;
x = x + 5;
y = x; // y gets value of x"""
    },

    "==": {
        "title": "Equality Operator",
        "category": "Operator",
        "description": "Compares two values for equality",
        "syntax": "value1 == value2",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Don't confuse with = (assignment)",
            "⚠️  Avoid with floats (use range comparison)",
            "⚠️  Returns true (1) or false (0)"
        ],
        "tips": [
            "💡 Use in if statements and conditions",
            "💡 For floats: if (abs(a - b) < 0.001)"
        ],
        "example": """if (x == 10) {
  Serial.println("Equal");
}

bool same = (a == b);"""
    },

    "!=": {
        "title": "Inequality Operator",
        "category": "Operator",
        "description": "Checks if two values are not equal",
        "syntax": "value1 != value2",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Opposite of ==",
            "⚠️  Returns true if values differ"
        ],
        "tips": [
            "💡 Often used to check for non-zero: if (x != 0)",
            "💡 Same warnings as == for floats"
        ],
        "example": """if (status != 0) {
  handleError();
}

while (Serial.read() != -1) {
  // Read available data
}"""
    },

    "<": {
        "title": "Less Than Operator",
        "category": "Operator",
        "description": "Checks if left value is less than right value",
        "syntax": "value1 < value2",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Returns true (1) or false (0)",
            "⚠️  Can be used with signed or unsigned types"
        ],
        "tips": [
            "💡 Commonly used in for loop conditions",
            "💡 Can chain comparisons: if (0 < x && x < 10)"
        ],
        "example": """if (temperature < 20) {
  heaterOn();
}

for (int i = 0; i < 100; i++) {
  // Loop
}"""
    },

    ">": {
        "title": "Greater Than Operator",
        "category": "Operator",
        "description": "Checks if left value is greater than right value",
        "syntax": "value1 > value2",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Returns true (1) or false (0)"
        ],
        "tips": [
            "💡 Use for threshold checking",
            "💡 Opposite of <"
        ],
        "example": """if (sensorValue > 500) {
  digitalWrite(led, HIGH);
}

while (count > 0) {
  count--;
}"""
    },

    "<=": {
        "title": "Less Than or Equal Operator",
        "category": "Operator",
        "description": "Checks if left value is less than or equal to right value",
        "syntax": "value1 <= value2",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  True if less than OR equal"
        ],
        "tips": [
            "💡 Inclusive comparison",
            "💡 Useful for array bounds: if (i <= lastIndex)"
        ],
        "example": """if (speed <= maxSpeed) {
  accelerate();
}

for (int i = 1; i <= 10; i++) {
  // Runs for 1 through 10
}"""
    },

    ">=": {
        "title": "Greater Than or Equal Operator",
        "category": "Operator",
        "description": "Checks if left value is greater than or equal to right value",
        "syntax": "value1 >= value2",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  True if greater than OR equal"
        ],
        "tips": [
            "💡 Inclusive comparison",
            "💡 Often used with thresholds"
        ],
        "example": """if (battery >= 20) {
  Serial.println("OK");
}

if (millis() >= timeout) {
  reset();
}"""
    },

    "&&": {
        "title": "Logical AND Operator",
        "category": "Operator",
        "description": "Returns true if both conditions are true",
        "syntax": "condition1 && condition2",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Short-circuit evaluation (stops at first false)",
            "⚠️  Don't confuse with & (bitwise AND)"
        ],
        "tips": [
            "💡 Use for multiple conditions",
            "💡 Right side not evaluated if left is false"
        ],
        "example": """if (temp > 20 && temp < 30) {
  Serial.println("Comfortable");
}

if (buttonPressed && !motorRunning) {
  startMotor();
}"""
    },

    "||": {
        "title": "Logical OR Operator",
        "category": "Operator",
        "description": "Returns true if at least one condition is true",
        "syntax": "condition1 || condition2",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Short-circuit evaluation (stops at first true)",
            "⚠️  Don't confuse with | (bitwise OR)"
        ],
        "tips": [
            "💡 Use for alternative conditions",
            "💡 Right side not evaluated if left is true"
        ],
        "example": """if (error1 || error2) {
  handleError();
}

if (command == 'A' || command == 'a') {
  processCommand();
}"""
    },

    "!": {
        "title": "Logical NOT Operator",
        "category": "Operator",
        "description": "Inverts boolean value (true becomes false, vice versa)",
        "syntax": "!condition",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Works on any value (0 is false, non-zero is true)",
            "⚠️  Don't confuse with != (not equal)"
        ],
        "tips": [
            "💡 Use for negation: if (!flag)",
            "💡 !! converts to boolean: bool b = !!value;"
        ],
        "example": """if (!buttonPressed) {
  waitForButton();
}

bool ledState = !ledState; // Toggle

if (!Serial.available()) {
  return;
}"""
    },

    "++": {
        "title": "Increment Operator",
        "category": "Operator",
        "description": "Increases variable by 1",
        "syntax": "variable++  // Post-increment\n++variable  // Pre-increment",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Post-increment (i++) returns old value then increments",
            "⚠️  Pre-increment (++i) increments then returns new value"
        ],
        "tips": [
            "💡 Commonly used in for loops",
            "💡 i++ and ++i have same effect when used alone"
        ],
        "example": """int count = 0;
count++;  // count is now 1

for (int i = 0; i < 10; i++) {
  Serial.println(i);
}"""
    },

    "--": {
        "title": "Decrement Operator",
        "category": "Operator",
        "description": "Decreases variable by 1",
        "syntax": "variable--  // Post-decrement\n--variable  // Pre-decrement",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Post-decrement (i--) returns old value then decrements",
            "⚠️  Pre-decrement (--i) decrements then returns new value"
        ],
        "tips": [
            "💡 Use for counting down",
            "💡 Same as: variable = variable - 1"
        ],
        "example": """int countdown = 10;
countdown--;  // countdown is now 9

for (int i = 10; i > 0; i--) {
  Serial.println(i);
}"""
    },

    "+": {
        "title": "Addition Operator",
        "category": "Operator",
        "description": "Adds two numbers",
        "syntax": "result = value1 + value2;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Can cause overflow with integer types",
            "⚠️  Rounding errors possible with floats"
        ],
        "tips": [
            "💡 Works with integers and floats",
            "💡 Use += for: x = x + y → x += y"
        ],
        "example": """int sum = 10 + 20;
float total = 3.5 + 2.1;
count = count + 1;"""
    },

    "-": {
        "title": "Subtraction Operator",
        "category": "Operator",
        "description": "Subtracts second number from first, or negates a number",
        "syntax": "result = value1 - value2;\nresult = -value;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Can cause underflow with unsigned types",
            "⚠️  Unary minus negates value"
        ],
        "tips": [
            "💡 Use -= for: x = x - y → x -= y",
            "💡 Unary: int neg = -x;"
        ],
        "example": """int diff = 50 - 20;
int negative = -10;
temperature = temperature - 5;"""
    },

    "*": {
        "title": "Multiplication Operator",
        "category": "Operator",
        "description": "Multiplies two numbers, or dereferences pointer",
        "syntax": "result = value1 * value2;\nvalue = *pointer;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Can cause overflow quickly",
            "⚠️  Different meaning with pointers"
        ],
        "tips": [
            "💡 Use *= for: x = x * y → x *= y",
            "💡 Integer multiplication faster than float"
        ],
        "example": """int product = 5 * 10;
float area = width * height;
scaled = value * 2;"""
    },

    "/": {
        "title": "Division Operator",
        "category": "Operator",
        "description": "Divides first number by second",
        "syntax": "result = value1 / value2;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Integer division truncates: 5 / 2 = 2",
            "⚠️  Division by zero causes crash",
            "⚠️  Use float for decimal results"
        ],
        "tips": [
            "💡 Cast to float for decimal: float x = (float)5 / 2;",
            "💡 Always check divisor is not zero",
            "💡 Use /= for: x = x / y → x /= y"
        ],
        "example": """int half = 10 / 2;        // 5
int truncated = 7 / 2;    // 3 (not 3.5)
float precise = 7.0 / 2.0; // 3.5"""
    },

    "%": {
        "title": "Modulo Operator",
        "category": "Operator",
        "description": "Returns remainder after division",
        "syntax": "result = value1 % value2;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Only works with integers",
            "⚠️  Sign of result matches first operand"
        ],
        "tips": [
            "💡 Use for cycling: index = (index + 1) % arraySize",
            "💡 Check even/odd: if (n % 2 == 0) // even",
            "💡 Great for wrapping values"
        ],
        "example": """int remainder = 10 % 3;  // 1
bool isEven = (n % 2 == 0);
int cyclic = count % 10; // 0-9"""
    },

    "&": {
        "title": "Bitwise AND / Address-of Operator",
        "category": "Operator",
        "description": "Performs bitwise AND operation, or gets address of variable",
        "syntax": "result = value1 & value2;\npointer = &variable;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Don't confuse with && (logical AND)",
            "⚠️  Different meaning with pointers"
        ],
        "tips": [
            "💡 Use for bit masking",
            "💡 Use &= for: x = x & y → x &= y",
            "💡 Extract specific bits"
        ],
        "example": """// Bitwise AND
byte result = 0b1100 & 0b1010; // 0b1000

// Check if bit is set
if (flags & 0x01) { }

// Get address
int* ptr = &variable;"""
    },

    "|": {
        "title": "Bitwise OR Operator",
        "category": "Operator",
        "description": "Performs bitwise OR operation",
        "syntax": "result = value1 | value2;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Don't confuse with || (logical OR)"
        ],
        "tips": [
            "💡 Use for setting bits",
            "💡 Use |= for: x = x | y → x |= y",
            "💡 Combines bit flags"
        ],
        "example": """byte result = 0b1100 | 0b0011; // 0b1111

// Set bit
flags |= 0x01;

// Combine options
pinMode(pin, INPUT | PULLUP);"""
    },

    "^": {
        "title": "Bitwise XOR Operator",
        "category": "Operator",
        "description": "Performs bitwise exclusive OR operation",
        "syntax": "result = value1 ^ value2;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  1 if bits differ, 0 if same"
        ],
        "tips": [
            "💡 Use for toggling bits",
            "💡 Use ^= for: x = x ^ y → x ^= y",
            "💡 x ^ x = 0, x ^ 0 = x"
        ],
        "example": """byte result = 0b1100 ^ 0b1010; // 0b0110

// Toggle bit
flags ^= 0x01;

// Swap without temp: a^=b; b^=a; a^=b;"""
    },

    "~": {
        "title": "Bitwise NOT Operator",
        "category": "Operator",
        "description": "Inverts all bits (one's complement)",
        "syntax": "result = ~value;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Flips all bits including sign bit",
            "⚠️  ~0 = -1 for signed integers"
        ],
        "tips": [
            "💡 Use for inverting bit patterns",
            "💡 Often used with bit masks"
        ],
        "example": """byte inverted = ~0b11110000; // 0b00001111

// Clear bit
flags &= ~0x01;

byte mask = ~0x0F; // 0xF0"""
    },

    "<<": {
        "title": "Left Shift Operator",
        "category": "Operator",
        "description": "Shifts bits left, filling with zeros",
        "syntax": "result = value << n;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Bits shifted off left are lost",
            "⚠️  Equivalent to multiplying by 2^n"
        ],
        "tips": [
            "💡 Fast multiplication by powers of 2",
            "💡 Use <<= for: x = x << n → x <<= n",
            "💡 Common in bit manipulation"
        ],
        "example": """int doubled = 5 << 1;   // 10 (5 * 2)
int times4 = 5 << 2;    // 20 (5 * 4)
byte bit3 = 1 << 3;     // 0b00001000"""
    },

    ">>": {
        "title": "Right Shift Operator",
        "category": "Operator",
        "description": "Shifts bits right",
        "syntax": "result = value >> n;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Bits shifted off right are lost",
            "⚠️  Sign bit behavior depends on signed/unsigned",
            "⚠️  Arithmetic shift for signed, logical for unsigned"
        ],
        "tips": [
            "💡 Fast division by powers of 2",
            "💡 Use >>= for: x = x >> n → x >>= n",
            "💡 Extract high bits"
        ],
        "example": """int halved = 10 >> 1;   // 5 (10 / 2)
int div4 = 20 >> 2;     // 5 (20 / 4)
byte high = value >> 4; // Get upper nibble"""
    },

    # ==================== STRUCTURE ====================

    "struct": {
        "title": "struct",
        "category": "Data Structure",
        "description": "Groups related variables under one name",
        "syntax": "struct name {\n  type1 member1;\n  type2 member2;\n};",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Don't forget semicolon after closing brace",
            "⚠️  Members are public by default"
        ],
        "tips": [
            "💡 Use for related data (e.g., coordinates, sensor data)",
            "💡 Access members with dot: myStruct.member",
            "💡 Can contain functions in C++"
        ],
        "example": """struct Point {
  int x;
  int y;
};

Point p1;
p1.x = 10;
p1.y = 20;

struct Sensor {
  float temperature;
  float humidity;
  bool valid;
};"""
    },

    "class": {
        "title": "class",
        "category": "Object-Oriented",
        "description": "Defines a user-defined type with data and functions",
        "syntax": "class ClassName {\npublic:\n  // public members\nprivate:\n  // private members\n};",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Members are private by default (unlike struct)",
            "⚠️  Don't forget semicolon after closing brace"
        ],
        "tips": [
            "💡 Use for encapsulation and OOP",
            "💡 Convention: class names start with capital letter",
            "💡 Can have constructors and destructors"
        ],
        "example": """class LED {
private:
  int pin;
public:
  LED(int p) {
    pin = p;
    pinMode(pin, OUTPUT);
  }

  void on() {
    digitalWrite(pin, HIGH);
  }

  void off() {
    digitalWrite(pin, LOW);
  }
};

LED led(13);
led.on();"""
    },

    "public": {
        "title": "public Access Specifier",
        "category": "Object-Oriented",
        "description": "Makes class members accessible from outside",
        "syntax": "public:\n  // public members",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Affects all members until next access specifier"
        ],
        "tips": [
            "💡 Use for interface (methods users should call)",
            "💡 Typically used for methods, not data"
        ],
        "example": """class Motor {
public:
  void start();
  void stop();
  int getSpeed();
private:
  int speed;
};"""
    },

    "private": {
        "title": "private Access Specifier",
        "category": "Object-Oriented",
        "description": "Makes class members accessible only within the class",
        "syntax": "private:\n  // private members",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Default for class members",
            "⚠️  Cannot be accessed from outside"
        ],
        "tips": [
            "💡 Use for internal implementation details",
            "💡 Promotes encapsulation",
            "💡 Provide public methods to access private data"
        ],
        "example": """class Counter {
private:
  int count;  // Hidden
public:
  Counter() : count(0) {}
  void increment() { count++; }
  int getCount() { return count; }
};"""
    },

    "protected": {
        "title": "protected Access Specifier",
        "category": "Object-Oriented",
        "description": "Makes members accessible in class and derived classes",
        "syntax": "protected:\n  // protected members",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  More permissive than private, less than public"
        ],
        "tips": [
            "💡 Use when deriving classes need access",
            "💡 Not accessible from outside like public"
        ],
        "example": """class Vehicle {
protected:
  int speed;
public:
  void setSpeed(int s) { speed = s; }
};

class Car : public Vehicle {
public:
  void accelerate() {
    speed += 10;  // Can access protected member
  }
};"""
    },

    # ==================== PREPROCESSOR ====================

    "#include": {
        "title": "#include Directive",
        "category": "Preprocessor",
        "description": "Includes header file contents",
        "syntax": "#include <filename.h>\n#include \"filename.h\"",
        "parameters": [],
        "common_values": [
            {"value": "<header.h>", "description": "System/library headers (search system paths)"},
            {"value": "\"header.h\"", "description": "Local headers (search current directory first)"}
        ],
        "warnings": [
            "⚠️  <> for system includes, \"\" for local includes",
            "⚠️  Circular includes can cause errors"
        ],
        "tips": [
            "💡 Use include guards to prevent multiple inclusion",
            "💡 Order matters: Arduino.h should come first"
        ],
        "example": """#include <Arduino.h>
#include <Wire.h>
#include \"myHeader.h\"

// Common Arduino libraries
#include <SPI.h>
#include <Servo.h>"""
    },

    "#define": {
        "title": "#define Directive",
        "category": "Preprocessor",
        "description": "Defines a macro (constant or function-like)",
        "syntax": "#define NAME value\n#define NAME(params) expression",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  No type checking (use const instead when possible)",
            "⚠️  No semicolon at end",
            "⚠️  Beware of macro expansion issues"
        ],
        "tips": [
            "💡 Convention: use ALL_CAPS for macro names",
            "💡 Use const for typed constants",
            "💡 Can be undefined with #undef"
        ],
        "example": """#define LED_PIN 13
#define MAX_VALUE 100
#define PI 3.14159

// Function-like macro
#define MAX(a,b) ((a)>(b)?(a):(b))

digitalWrite(LED_PIN, HIGH);"""
    },

    "#ifdef": {
        "title": "#ifdef Directive",
        "category": "Preprocessor",
        "description": "Conditional compilation if macro is defined",
        "syntax": "#ifdef MACRO_NAME\n  // code\n#endif",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Only checks if defined, not value",
            "⚠️  Must close with #endif"
        ],
        "tips": [
            "💡 Use for platform-specific code",
            "💡 Useful for debug code",
            "💡 #ifndef checks if NOT defined"
        ],
        "example": """#ifdef DEBUG
  Serial.println("Debug mode");
#endif

#ifdef ARDUINO_AVR_UNO
  // Uno-specific code
#endif"""
    },

    "#ifndef": {
        "title": "#ifndef Directive",
        "category": "Preprocessor",
        "description": "Conditional compilation if macro is NOT defined",
        "syntax": "#ifndef MACRO_NAME\n  // code\n#endif",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Must close with #endif"
        ],
        "tips": [
            "💡 Common for include guards",
            "💡 Opposite of #ifdef"
        ],
        "example": """#ifndef MY_HEADER_H
#define MY_HEADER_H
  // header content
#endif

#ifndef LED_PIN
  #define LED_PIN 13
#endif"""
    },

    "#if": {
        "title": "#if Directive",
        "category": "Preprocessor",
        "description": "Conditional compilation based on expression",
        "syntax": "#if expression\n  // code\n#endif",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Evaluates at compile time",
            "⚠️  Can use #elif and #else"
        ],
        "tips": [
            "💡 More flexible than #ifdef",
            "💡 Can check values and do arithmetic"
        ],
        "example": """#if ARDUINO >= 100
  #include <Arduino.h>
#else
  #include <WProgram.h>
#endif

#if defined(__AVR__)
  // AVR code
#endif"""
    },

    "#else": {
        "title": "#else Directive",
        "category": "Preprocessor",
        "description": "Alternative code in conditional compilation",
        "syntax": "#if condition\n  // code\n#else\n  // alternative\n#endif",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Must be between #if/#ifdef and #endif"
        ],
        "tips": [
            "💡 Use for platform-specific alternatives"
        ],
        "example": """#ifdef USE_LCD
  lcd.print("Hello");
#else
  Serial.println("Hello");
#endif"""
    },

    "#elif": {
        "title": "#elif Directive",
        "category": "Preprocessor",
        "description": "Else-if in conditional compilation",
        "syntax": "#if condition1\n  // code1\n#elif condition2\n  // code2\n#endif",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Evaluated in order",
            "⚠️  First true condition is used"
        ],
        "tips": [
            "💡 Better than nested #if statements",
            "💡 Can have multiple #elif"
        ],
        "example": """#if BOARD_TYPE == 1
  // Board 1 code
#elif BOARD_TYPE == 2
  // Board 2 code
#else
  // Default code
#endif"""
    },

    "#endif": {
        "title": "#endif Directive",
        "category": "Preprocessor",
        "description": "Ends conditional compilation block",
        "syntax": "#endif",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Must match with #if/#ifdef/#ifndef"
        ],
        "tips": [
            "💡 Add comments for nested blocks: #endif // DEBUG"
        ],
        "example": """#ifdef DEBUG
  Serial.begin(9600);
#endif  // DEBUG"""
    },

    # ==================== MEMORY & POINTERS ====================

    "sizeof": {
        "title": "sizeof Operator",
        "category": "Memory",
        "description": "Returns size of type or variable in bytes",
        "syntax": "sizeof(type)\nsizeof(variable)",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Size can vary between platforms",
            "⚠️  For arrays, sizeof includes all elements"
        ],
        "tips": [
            "💡 Get array length: sizeof(arr) / sizeof(arr[0])",
            "💡 Evaluated at compile time"
        ],
        "example": """int size = sizeof(int);      // Typically 2 or 4
int arrSize = sizeof(array); // Total bytes

int nums[] = {1, 2, 3, 4, 5};
int count = sizeof(nums) / sizeof(nums[0]);"""
    },

    "new": {
        "title": "new Operator",
        "category": "Memory",
        "description": "Allocates memory dynamically (heap)",
        "syntax": "type* ptr = new type;\ntype* arr = new type[size];",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Must be freed with delete or delete[]",
            "⚠️  Can cause memory fragmentation on Arduino",
            "⚠️  Limited heap memory on microcontrollers"
        ],
        "tips": [
            "💡 Avoid on Arduino if possible",
            "💡 Always check if allocation succeeded",
            "💡 Use delete for single, delete[] for arrays"
        ],
        "example": """int* ptr = new int;
*ptr = 42;
delete ptr;

int* arr = new int[10];
delete[] arr;"""
    },

    "delete": {
        "title": "delete Operator",
        "category": "Memory",
        "description": "Frees dynamically allocated memory",
        "syntax": "delete ptr;\ndelete[] array_ptr;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Use delete[] for arrays allocated with new[]",
            "⚠️  Don't delete same pointer twice",
            "⚠️  Don't delete stack variables"
        ],
        "tips": [
            "💡 Set pointer to nullptr after delete",
            "💡 Match new with delete, new[] with delete[]"
        ],
        "example": """int* ptr = new int;
delete ptr;
ptr = nullptr;

int* arr = new int[10];
delete[] arr;"""
    },

    "nullptr": {
        "title": "nullptr",
        "category": "Pointer",
        "description": "Null pointer constant (C++11)",
        "syntax": "type* ptr = nullptr;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Preferred over NULL or 0 in modern C++",
            "⚠️  May not be available on older Arduino cores"
        ],
        "tips": [
            "💡 Type-safe null pointer",
            "💡 Always initialize pointers"
        ],
        "example": """int* ptr = nullptr;

if (ptr == nullptr) {
  Serial.println("Null pointer");
}"""
    },

    "NULL": {
        "title": "NULL",
        "category": "Pointer",
        "description": "Null pointer macro (legacy)",
        "syntax": "type* ptr = NULL;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Actually defined as 0 or ((void*)0)",
            "⚠️  Use nullptr in modern C++ code"
        ],
        "tips": [
            "💡 Check pointers before dereferencing",
            "💡 Initialize pointers to NULL if not ready to use"
        ],
        "example": """char* str = NULL;

if (str != NULL) {
  Serial.println(str);
}"""
    },

    # ==================== SPECIAL KEYWORDS ====================

    "typedef": {
        "title": "typedef",
        "category": "Type Alias",
        "description": "Creates an alias for an existing type",
        "syntax": "typedef existing_type new_name;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Doesn't create a new type, just an alias",
            "⚠️  Can make code less clear if overused"
        ],
        "tips": [
            "💡 Use for complex types or portability",
            "💡 Common: typedef struct {...} Name;"
        ],
        "example": """typedef unsigned char byte;
typedef unsigned int uint;

typedef struct {
  int x;
  int y;
} Point;

Point p1;"""
    },

    "enum": {
        "title": "enum",
        "category": "Enumeration",
        "description": "Defines a set of named integer constants",
        "syntax": "enum Name {\n  VALUE1,\n  VALUE2,\n  VALUE3\n};",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Values start at 0 by default",
            "⚠️  Actually integers (can be assigned to int)"
        ],
        "tips": [
            "💡 Makes code more readable",
            "💡 Can specify values: VALUE = 5",
            "💡 Good for state machines"
        ],
        "example": """enum State {
  IDLE,
  RUNNING,
  PAUSED,
  STOPPED
};

State currentState = IDLE;

enum Pins {
  LED_PIN = 13,
  BUTTON_PIN = 2
};"""
    },

    "true": {
        "title": "true",
        "category": "Boolean Constant",
        "description": "Boolean true value",
        "syntax": "bool variable = true;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Any non-zero value is considered true"
        ],
        "tips": [
            "💡 More readable than 1",
            "💡 Use with bool type"
        ],
        "example": """bool isActive = true;

if (isActive == true) {
  // Or simply: if (isActive)
  doSomething();
}"""
    },

    "false": {
        "title": "false",
        "category": "Boolean Constant",
        "description": "Boolean false value",
        "syntax": "bool variable = false;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Only zero is false"
        ],
        "tips": [
            "💡 More readable than 0",
            "💡 Use with bool type"
        ],
        "example": """bool isRunning = false;

if (isRunning == false) {
  // Or simply: if (!isRunning)
  stopMotor();
}"""
    },

    # ==================== ADVANCED KEYWORDS ====================

    "inline": {
        "title": "inline",
        "category": "Function Modifier",
        "description": "Suggests compiler to insert function code at call site",
        "syntax": "inline return_type function_name(params) { }",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Only a suggestion to compiler",
            "⚠️  Can increase code size if overused"
        ],
        "tips": [
            "💡 Use for small, frequently called functions",
            "💡 Can improve performance by eliminating call overhead"
        ],
        "example": """inline int square(int x) {
  return x * x;
}

inline void fastToggle(int pin) {
  digitalWrite(pin, !digitalRead(pin));
}"""
    },

    "auto": {
        "title": "auto",
        "category": "Type Deduction",
        "description": "Automatically deduces variable type (C++11)",
        "syntax": "auto variable = expression;",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Type determined at compile time",
            "⚠️  May not be available on older Arduino cores",
            "⚠️  Can reduce code clarity if overused"
        ],
        "tips": [
            "💡 Useful for complex type names",
            "💡 Good with iterators and templates"
        ],
        "example": """auto x = 5;        // int
auto f = 3.14f;    // float
auto c = 'A';      // char

auto result = someComplexFunction();"""
    },

    "namespace": {
        "title": "namespace",
        "category": "Scope",
        "description": "Defines a named scope for identifiers",
        "syntax": "namespace name {\n  // declarations\n}",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Rarely used in Arduino sketches",
            "⚠️  Avoid 'using namespace' in headers"
        ],
        "tips": [
            "💡 Prevents name conflicts",
            "💡 Standard library uses 'std' namespace"
        ],
        "example": """namespace MyProject {
  void init() {
    // initialization
  }
}

MyProject::init();

using namespace MyProject;
init(); // Now can call directly"""
    },

    "this": {
        "title": "this Pointer",
        "category": "Object-Oriented",
        "description": "Pointer to current object instance",
        "syntax": "this->member\n(*this).member",
        "parameters": [],
        "common_values": [],
        "warnings": [
            "⚠️  Only available in non-static member functions",
            "⚠️  Cannot be modified"
        ],
        "tips": [
            "💡 Use to disambiguate member variables from parameters",
            "💡 Can return *this for method chaining"
        ],
        "example": """class Counter {
  int value;
public:
  Counter(int value) {
    this->value = value;  // Disambiguate
  }

  Counter& increment() {
    this->value++;
    return *this;  // Method chaining
  }
};"""
    },
}


def get_cpp_info(keyword):
    """Get C++ reference information for a keyword"""
    if keyword in CPP_REFERENCE:
        return CPP_REFERENCE[keyword]
    return None


def get_all_cpp_keywords():
    """Get list of all documented C++ keywords"""
    return list(CPP_REFERENCE.keys())


def search_cpp_keywords(query):
    """Search for keywords by name or category"""
    results = []
    query_lower = query.lower()

    for keyword, info in CPP_REFERENCE.items():
        if (query_lower in keyword.lower() or
            query_lower in info.get('category', '').lower() or
            query_lower in info.get('description', '').lower()):
            results.append(keyword)

    return results
