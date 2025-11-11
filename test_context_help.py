#!/usr/bin/env python3
"""
Test script for Context Help database
Verifies that all C++ keywords and Arduino functions are accessible
"""

from arduino_ide.data.arduino_api_reference import get_api_info, get_all_functions

def test_database():
    """Test the comprehensive database"""
    print("=" * 60)
    print("Context Help Database Test")
    print("=" * 60)

    # Get all available entries
    all_items = get_all_functions()
    print(f"\n✓ Total entries in database: {len(all_items)}")

    # Test Arduino functions
    print("\n" + "=" * 60)
    print("Testing Arduino Functions:")
    print("=" * 60)
    arduino_tests = ["Serial.begin", "pinMode", "digitalWrite", "analogRead", "delay"]
    for func in arduino_tests:
        info = get_api_info(func)
        if info:
            print(f"✓ {func}: {info['title']} ({info['category']})")
        else:
            print(f"✗ {func}: NOT FOUND")

    # Test C++ data types
    print("\n" + "=" * 60)
    print("Testing C++ Data Types:")
    print("=" * 60)
    type_tests = ["int", "float", "char", "bool", "void", "double", "long"]
    for dtype in type_tests:
        info = get_api_info(dtype)
        if info:
            print(f"✓ {dtype}: {info['title']} ({info['category']})")
        else:
            print(f"✗ {dtype}: NOT FOUND")

    # Test C++ keywords
    print("\n" + "=" * 60)
    print("Testing C++ Keywords:")
    print("=" * 60)
    keyword_tests = ["if", "else", "for", "while", "switch", "case", "break", "return"]
    for keyword in keyword_tests:
        info = get_api_info(keyword)
        if info:
            print(f"✓ {keyword}: {info['title']} ({info['category']})")
        else:
            print(f"✗ {keyword}: NOT FOUND")

    # Test operators
    print("\n" + "=" * 60)
    print("Testing Operators:")
    print("=" * 60)
    operator_tests = ["=", "==", "!=", "<", ">", "&&", "||", "!", "++", "--", "+", "-", "*", "/", "%"]
    for op in operator_tests:
        info = get_api_info(op)
        if info:
            print(f"✓ {op}: {info['title']} ({info['category']})")
        else:
            print(f"✗ {op}: NOT FOUND")

    # Test storage classes
    print("\n" + "=" * 60)
    print("Testing Storage Classes:")
    print("=" * 60)
    storage_tests = ["const", "static", "volatile"]
    for storage in storage_tests:
        info = get_api_info(storage)
        if info:
            print(f"✓ {storage}: {info['title']} ({info['category']})")
        else:
            print(f"✗ {storage}: NOT FOUND")

    # Test preprocessor
    print("\n" + "=" * 60)
    print("Testing Preprocessor Directives:")
    print("=" * 60)
    preprocessor_tests = ["#include", "#define", "#ifdef", "#ifndef", "#if", "#endif"]
    for directive in preprocessor_tests:
        info = get_api_info(directive)
        if info:
            print(f"✓ {directive}: {info['title']} ({info['category']})")
        else:
            print(f"✗ {directive}: NOT FOUND")

    # Test object-oriented features
    print("\n" + "=" * 60)
    print("Testing Object-Oriented Features:")
    print("=" * 60)
    oop_tests = ["class", "struct", "public", "private", "protected", "this"]
    for feature in oop_tests:
        info = get_api_info(feature)
        if info:
            print(f"✓ {feature}: {info['title']} ({info['category']})")
        else:
            print(f"✗ {feature}: NOT FOUND")

    # Display example entry
    print("\n" + "=" * 60)
    print("Example Entry (for loop):")
    print("=" * 60)
    for_info = get_api_info("for")
    if for_info:
        print(f"Title: {for_info['title']}")
        print(f"Category: {for_info['category']}")
        print(f"Description: {for_info['description']}")
        print(f"Syntax:\n{for_info['syntax']}")
        if for_info.get('example'):
            print(f"Example:\n{for_info['example']}")

    print("\n" + "=" * 60)
    print("Categories in Database:")
    print("=" * 60)
    categories = set()
    for item in all_items:
        info = get_api_info(item)
        if info and 'category' in info:
            categories.add(info['category'])

    for cat in sorted(categories):
        print(f"• {cat}")

    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    test_database()
