# bluetooth_scan.py
# ─────────────────────────────────────────────────────────────
# This is a STANDALONE script — it does NOT connect to Flask.
# Run it separately to scan for nearby Bluetooth devices.
#
# Requirements:
#   pip install bleak
#
# Run with:
#   python bluetooth_scan.py
# ─────────────────────────────────────────────────────────────

import asyncio
from bleak import BleakScanner


async def scan_bluetooth_devices():
    """
    Scan for nearby Bluetooth Low Energy (BLE) devices.
    Prints each device's name and MAC address.
    """
    print("🔵 Scanning for nearby Bluetooth devices...")
    print("   (This may take a few seconds)\n")

    # BleakScanner.discover() returns a list of BLEDevice objects
    # timeout=5.0 means we scan for 5 seconds
    devices = await BleakScanner.discover(timeout=5.0)

    if not devices:
        print("❌ No Bluetooth devices found nearby.")
        return

    print(f"✅ Found {len(devices)} device(s):\n")
    print(f"{'#':<4} {'Device Name':<30} {'Address':<20}")
    print("-" * 56)

    for i, device in enumerate(devices, start=1):
        # device.name might be None if the device doesn't broadcast a name
        name    = device.name or "Unknown Device"
        address = device.address

        print(f"{i:<4} {name:<30} {address:<20}")

    print("\nTip: Attach a BLE tracker tag (like Tile or AirTag) to")
    print("     your item and its address will appear here.")


# ─────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────
if __name__ == "__main__":
    # asyncio.run() is needed because bleak uses async/await
    asyncio.run(scan_bluetooth_devices())
