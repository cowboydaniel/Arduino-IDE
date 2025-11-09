#!/usr/bin/env python3
"""
Arduino Package Manager Demo

Demonstrates the enhanced package manager features
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from arduino_ide.services.library_manager import LibraryManager
from arduino_ide.services.board_manager import BoardManager
from arduino_ide.services.background_updater import BackgroundUpdater, OfflineDetector
from arduino_ide.services.download_manager import DownloadManager
from arduino_ide.services.index_updater import IndexUpdater


def demo_library_manager():
    """Demonstrate library manager features"""
    print("\n" + "=" * 60)
    print("📚 LIBRARY MANAGER DEMO")
    print("=" * 60)

    lib_manager = LibraryManager()

    # Update index
    print("\n1. Updating library index (with smart caching)...")
    lib_manager.update_index()

    # Search libraries
    print("\n2. Searching for sensor libraries...")
    results = lib_manager.search_libraries(
        query="sensor",
        category="Sensors",
        actively_maintained=True
    )
    print(f"Found {len(results)} sensor libraries")
    for lib in results[:5]:
        print(f"  - {lib.name} v{lib.latest_version} by {lib.author}")
        if lib.stats:
            print(f"    Downloads: {lib.stats.downloads:,}")
            if lib.stats.verified:
                print(f"    ✓ Verified by Arduino")

    # Get dependency tree
    print("\n3. Analyzing dependencies for 'Adafruit NeoPixel'...")
    plan = lib_manager.resolve_dependencies("Adafruit NeoPixel")
    print(f"Installation plan:")
    print(f"  - To install: {len(plan.to_install)} libraries")
    print(f"  - To update: {len(plan.to_update)} libraries")
    print(f"  - Already installed: {len(plan.already_installed)} libraries")

    if plan.to_install:
        print(f"\n  Libraries to install:")
        for name, version in plan.to_install:
            print(f"    - {name} v{version}")

    # List installed
    print("\n4. Listing installed libraries...")
    installed = lib_manager.search_libraries(installed_only=True)
    print(f"You have {len(installed)} libraries installed")
    for lib in installed[:10]:
        status = "✓" if lib.has_update() else " "
        print(f"  {status} {lib.name} v{lib.installed_version}")


def demo_download_manager():
    """Demonstrate download manager features"""
    print("\n" + "=" * 60)
    print("⬇️  DOWNLOAD MANAGER DEMO")
    print("=" * 60)

    cache_dir = Path.home() / ".arduino-ide-modern" / "cache"
    dl_manager = DownloadManager(cache_dir)

    print("\n1. Download manager features:")
    print("  ✓ Multi-mirror fallback")
    print("  ✓ Resume interrupted downloads")
    print("  ✓ SHA-256 checksum verification")
    print("  ✓ Retry with exponential backoff")
    print("  ✓ Real-time progress tracking")

    print("\n2. Example download flow:")
    print("  Primary URL → Failed")
    print("  Mirror #1 → Failed")
    print("  Mirror #2 → Success!")
    print("  Verifying checksum... ✓")
    print("  Download complete in 2.3s")


def demo_background_updater():
    """Demonstrate background updater features"""
    print("\n" + "=" * 60)
    print("🔄 BACKGROUND UPDATER DEMO")
    print("=" * 60)

    updater = BackgroundUpdater()

    print("\n1. Background update checker features:")
    print("  ✓ Checks for updates every 24 hours")
    print("  ✓ Non-blocking operation")
    print("  ✓ Desktop notifications")
    print("  ✓ Respects offline mode")

    # Get last check info
    info = updater.get_last_check_info()
    print(f"\n2. Update status:")
    print(f"  Last checked: {info['last_check_human']}")
    print(f"  Next check: {info['next_check_human']}")

    # Add callback
    def on_updates(updates):
        print(f"\n  📢 Found {len(updates)} updates!")

    updater.add_update_callback(on_updates)


def demo_offline_mode():
    """Demonstrate offline mode features"""
    print("\n" + "=" * 60)
    print("🔌 OFFLINE MODE DEMO")
    print("=" * 60)

    # Check connectivity
    is_online = OfflineDetector.is_online()
    quality = OfflineDetector.get_connection_quality()

    print(f"\n1. Connection status: {'Online' if is_online else 'Offline'}")
    print(f"   Quality: {quality}")

    print("\n2. Offline capabilities:")
    capabilities = {
        "browse_installed": True,
        "browse_cached": True,
        "uninstall": True,
        "view_documentation": True,
        "open_examples": True,
        "search_local": True,
        "install_new": False,
        "check_updates": False,
        "download": False,
    }

    for feature, available in capabilities.items():
        status = "✓" if available else "✗"
        print(f"  {status} {feature.replace('_', ' ').title()}")


def demo_index_updater():
    """Demonstrate index updater features"""
    print("\n" + "=" * 60)
    print("📋 INDEX UPDATER DEMO")
    print("=" * 60)

    cache_dir = Path.home() / ".arduino-ide-modern" / "cache"
    updater = IndexUpdater(cache_dir)

    index_file = cache_dir / "library_index.json"

    print("\n1. Smart caching features:")
    print("  ✓ ETag/If-Modified-Since support")
    print("  ✓ Only downloads when changed")
    print("  ✓ Bandwidth optimization")
    print("  ✓ Offline fallback")

    # Get cache info
    info = updater.get_cache_info(index_file)
    if info['exists']:
        print(f"\n2. Cache information:")
        print(f"   Size: {info['size_human']}")
        print(f"   Last modified: {info['age_human']}")
        print(f"   Status: {'Fresh' if info['age_hours'] < 1 else 'Stale'}")
    else:
        print("\n2. No cache found (first run)")


def demo_board_manager():
    """Demonstrate board manager features"""
    print("\n" + "=" * 60)
    print("🔧 BOARD MANAGER DEMO")
    print("=" * 60)

    board_manager = BoardManager()

    print("\n1. Searching for ESP32 boards...")
    boards = board_manager.search_boards(query="esp32")
    print(f"Found {len(boards)} ESP32 boards")
    for board in boards[:5]:
        print(f"  - {board.name}")
        print(f"    FQBN: {board.fqbn}")
        print(f"    CPU: {board.specs.cpu}")
        print(f"    RAM: {board.specs.ram}")

    print("\n2. Board comparison feature available:")
    print("  - Compare multiple boards side-by-side")
    print("  - View specs, features, and pricing")
    print("  - Filter by capabilities")


def main():
    """Run all demos"""
    print("\n" + "=" * 60)
    print("🎯 ARDUINO PACKAGE MANAGER - ENHANCED FEATURES DEMO")
    print("=" * 60)

    try:
        demo_library_manager()
        demo_download_manager()
        demo_background_updater()
        demo_offline_mode()
        demo_index_updater()
        demo_board_manager()

        print("\n" + "=" * 60)
        print("✅ DEMO COMPLETED")
        print("=" * 60)
        print("\nFor more information, see:")
        print("  - docs/PACKAGE_MANAGER_REDESIGN.md")
        print("  - arduino-cli --help")
        print("\n")

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        sys.exit(130)

    except Exception as e:
        print(f"\n❌ Error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
