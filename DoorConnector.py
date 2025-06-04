import asyncio
import struct
import anycrc
from datetime import datetime, timezone
from bleak import BleakClient

# --- User-configurable variables ---
DEVICE_ADDRESS = "00:80:E1:22:C2:7C"  # Your device's MAC address
CHARACTERISTIC_UUID = "00000000-8e22-4541-9d4c-21edae82ed19"  # Your characteristic UUID
SERVICE_UUID = "00000000-cc7a-482a-984a-7f2ed5b3e58f"  # Your service UUID
HANDLE = 0x0012  # Your characteristic handle
COMMAND_OPCODE = 0x02  # 0x01 = Open, 0x02 = Close

# CRC-8/SMBus setup (poly=0x31, init=0x00, xorOut=0x00, reversed)
crc8 = anycrc.Model('CRC8-SMBUS')

def get_current_tick() -> bytes:
    """Generate UTC hour and minute mirroring for freshness validation."""
    now = datetime.now(timezone.utc)
    h = now.hour
    m = now.minute
    return bytes([h, m, h, m])

def build_ble_command(counter: int, tick: bytes, command: int) -> bytes:
    """Build the 33-byte BLE command payload."""
    # 0–3: Nonce / Counter (4 bytes, little-endian)
    c_bytes = struct.pack('<I', counter)
    # 4–7: Nonce Echo (copy of counter)
    echo = c_bytes
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
        c_bytes + echo + reserved + reserved2 +
        tick_block + reserved3 + cmd + pad
    )
    # Calculate CRC-8/SMBus checksum
    crc = crc8.calc(payload_32)
    # Append CRC to payload
    return payload_32 + bytes([crc])

async def send_command(counter: int, command: int):
    """Send the BLE command to the device."""
    async with BleakClient(DEVICE_ADDRESS) as client:
        tick = get_current_tick()
        payload = build_ble_command(counter, tick, command)
        await client.write_gatt_char(HANDLE, payload)
        print(f"Sent payload: {payload.hex()}")

if __name__ == "__main__":
    counter = 0x008a403a  # Example counter value
    command = COMMAND_OPCODE  # Close command
    asyncio.run(send_command(counter, command))