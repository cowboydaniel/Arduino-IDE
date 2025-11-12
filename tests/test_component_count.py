#!/usr/bin/env python3
"""
Test script to count components in the circuit service
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from arduino_ide.services.circuit_service import CircuitService
from arduino_ide.models.circuit_domain import ComponentType

def main():
    print("Initializing Circuit Service...")
    service = CircuitService()

    # Get all components
    all_components = service.get_all_component_definitions()
    print(f"\nTotal Components: {len(all_components)}")

    # Count by type
    print("\n=== Components by Type ===")
    type_counts = {}
    for comp in all_components:
        comp_type = comp.component_type
        if comp_type not in type_counts:
            type_counts[comp_type] = 0
        type_counts[comp_type] += 1

    for comp_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"{comp_type.value:20s}: {count:5d} components")

    # Show some examples
    print("\n=== Sample Components ===")
    for comp_type in ComponentType:
        comps = service.get_components_by_type(comp_type)
        if comps:
            print(f"\n{comp_type.value}:")
            for comp in comps[:3]:  # Show first 3
                print(f"  - {comp.name}")
            if len(comps) > 3:
                print(f"  ... and {len(comps) - 3} more")

if __name__ == "__main__":
    main()
