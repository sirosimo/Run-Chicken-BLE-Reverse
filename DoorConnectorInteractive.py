import asyncio
import anycrc
from datetime import datetime, timezone
from bleak import BleakClient
import time
import hashlib

# --- User-configurable variables ---
DEVICE_ADDRESS = "00:80:E1:22:C2:7C"  # Your device's MAC address
HANDLE = 0x0012  # Your characteristic handle
CHARACTERISTIC_UUID = "00000000-8e22-4541-9d4c-21edae82ed19"  # Your characteristic UUID
SERVICE_UUID = "00000000-cc7a-482a-984a-7f2ed5b3e58f"  # Your service UUID

# CRC-8/SMBus setup (poly=0x31, init=0x00, xorOut=0x00, reversed)
crc8 = anycrc.Model('CRC8-SMBUS')

def generate_session_id():
    """Generate session ID that changes every 5 minutes."""
    t = int(time.time() // 300)  # changes every 5 min
    seed = f"{t}".encode()
    h = hashlib.sha1(seed).digest()
    return h[:3]  # bytes for [1–3]

def generate_nonce(counter: int):
    """Generate 4-byte nonce using counter and session ID."""
    session_id = generate_session_id()
    return bytes([counter]) + session_id

def get_current_tick() -> bytes:
    """Generate UTC hour and minute mirroring for freshness validation."""
    now = datetime.now(timezone.utc)
    h = now.hour
    m = now.minute
    return bytes([h, m, h, m])

def build_ble_command(counter: int, tick: bytes, command: int) -> bytes:
    """Build the 33-byte BLE command payload."""
    # 0–3: Nonce / Counter (4 bytes, little-endian)
    nonce = generate_nonce(counter)
    # 4–7: Nonce Echo (copy of nonce)
    echo = nonce
    # 8–13: Reserved Padding
    reserved = b'\x00' * 6
    # 14–15: Reserved
    reserved2 = b'\x00\x00'
    # 16–19: UTC hour and minute mirroring
    tick_block = tick
    # 20–23: Reserved
    reserved3 = b'\x00\x00\x00\x00'
    # 24: Command opcode
    cmd = bytes([command])
    # 25–31: Padding
    pad = b'\x00' * 7

    # Assemble first 32 bytes
    payload_32 = (
        nonce + echo + reserved + reserved2 +
        tick_block + reserved3 + cmd + pad
    )
    # Calculate CRC-8/SMBus checksum
    crc = crc8.calc(payload_32)
    # Append CRC to payload
    return payload_32 + bytes([crc])

async def send_command(client: BleakClient, counter: int, command: int):
    """Send the BLE command to the device."""
    tick = get_current_tick()
    payload = build_ble_command(counter, tick, command)
    await client.write_gatt_char(HANDLE, payload)
    print(f"Sent payload: {payload.hex()}")

async def main():
    print(f"Door Control Script - Device MAC Address: {DEVICE_ADDRESS}")
    connect_choice = input("Do you want to connect to the door? (y/n): ").strip().lower()
    if connect_choice != 'y':
        print("Exiting...")
        return

    try:
        async with BleakClient(DEVICE_ADDRESS) as client:
            print("Connected to the door.")
            counter = 0  # Initialize counter
            while True:
                print("Press 'o' to open the door, 'c' to close the door, or 'q' to quit.")
                user_input = input("Enter your choice: ").strip().lower()
                if user_input == 'o':
                    print("Sending open command...")
                    await send_command(client, counter, 0x01)  # Open command
                    counter = (counter + 1) & 0xFF  # Increment counter (wraps at 255)
                elif user_input == 'c':
                    print("Sending close command...")
                    await send_command(client, counter, 0x02)  # Close command
                    counter = (counter + 1) & 0xFF  # Increment counter (wraps at 255)
                elif user_input == 'q':
                    print("Exiting...")
                    break
                else:
                    print("Invalid input. Please enter 'o', 'c', or 'q'.")
    except Exception as e:
        print(f"Failed to connect to the door: {e}")

if __name__ == "__main__":
    asyncio.run(main())