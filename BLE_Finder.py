import asyncio
from bleak import discover, BleakClient

async def list_ble_devices():
    print("Scanning for BLE devices...")
    devices = await discover()
    if devices:
        print(f"Found {len(devices)} devices:")
        for device in devices:
            print(f"Name: {device.name}, Address: {device.address}, RSSI: {device.rssi}")
            # Try to connect and list UUIDs if possible
            try:
                async with BleakClient(device.address) as client:
                    connected = await client.is_connected()
                    if connected:
                        services = await client.get_services()
                        print("  Services and Characteristics UUIDs:")
                        for service in services:
                            print(f"    Service: {service.uuid}")
                            for char in service.characteristics:
                                print(f"      Characteristic: {char.uuid} (Handle: {char.handle})")
            except Exception as e:
                print(f"  Could not connect or fetch UUIDs: {e}")
    else:
        print("No BLE devices found.")

if __name__ == "__main__":
    asyncio.run(list_ble_devices())