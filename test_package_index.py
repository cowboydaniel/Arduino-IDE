#!/usr/bin/env python3
"""Debug script to test package index download"""

import requests
import json

url = "https://downloads.arduino.cc/packages/package_index.json"

print("Attempting to download package index...")
print(f"URL: {url}\n")

try:
    response = requests.get(url, timeout=30)
    print(f"Status code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
    print(f"Content-Length: {response.headers.get('Content-Length', 'N/A')}")
    print(f"Actual response length: {len(response.content)} bytes\n")

    if response.status_code == 200:
        print("First 500 characters of response:")
        print(response.text[:500])
        print("\n" + "="*60 + "\n")

        try:
            data = response.json()
            print(f"JSON parsed successfully")
            print(f"Top-level keys: {list(data.keys())}")

            if "packages" in data:
                packages = data["packages"]
                print(f"Number of packages: {len(packages)}")
                if packages:
                    print(f"\nFirst package name: {packages[0].get('name', 'N/A')}")
                    print(f"First package maintainer: {packages[0].get('maintainer', 'N/A')}")
                    if "platforms" in packages[0]:
                        print(f"Number of platforms in first package: {len(packages[0]['platforms'])}")
            else:
                print("WARNING: No 'packages' key in JSON response!")

        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to parse JSON: {e}")
    else:
        print(f"ERROR: Got status code {response.status_code}")
        print(f"Response body: {response.text[:500]}")

except requests.RequestException as e:
    print(f"ERROR: Request failed: {e}")
