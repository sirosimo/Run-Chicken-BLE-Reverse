import asyncio
import struct
import time
import anycrc
from bleak import BleakClient

# --- User-configurable variables ---
DEVICE_ADDRESS = "00:80:E1:22:C2:7C"  # Your device's MAC address
CHARACTERISTIC_UUID = "00000000-8e22-4541-9d4c-21edae82ed19"  # Your characteristic UUID
SERVICE_UUID = "00000000-cc7a-482a-984a-7f2ed5b3e58f"  # Your service UUID
HANDLE = 0x0012  # Your characteristic handle
COMMAND_OPCODE = 0x02  # 0x01 = Open, 0x02 = Close


# CRC-8/SMBus setup (poly=0x31, init=0x00, xorOut=0x00, reversed)
crc8 = anycrc.Model('CRC8-SMBUS')

def get_mirrored_counter_block(counter_value: int) -> bytes:
    b = counter_value.to_bytes(2, byteorder='big')
    return b + b

def build_ble_command(counter: int, freshness_counter: int, command: int) -> bytes:
    # 0–3: Nonce / Counter (4 bytes, little-endian)
    c_bytes = struct.pack('<I', counter)
    # 4–7: Fixed Session Bytes
    fixed = bytes.fromhex('68403a68')
    # 8–11: Echo of Counter
    echo = c_bytes
    # 12–13: Device signature
    signature = bytes.fromhex('3a68')
    # 14–15: Reserved
    reserved1 = bytes([0x00, 0x00])
    # 16–19: Timestamp block (mirrored 2-byte value, big-endian)
    ts = struct.pack('>H', freshness_counter & 0xFFFF)
    ts_block = ts + ts
    # 20–23: Reserved
    reserved2 = bytes([0x00, 0x00, 0x00, 0x00])
    # 24: Command opcode
    cmd = bytes([command])
    # 25–31: Padding
    padding = bytes([0x00] * 7)

    # Assemble first 32 bytes
    payload_32 = (
        c_bytes + fixed + echo + signature + reserved1 +
        ts_block + reserved2 + cmd + padding
    )
    # Calculate CRC-8/SMBus checksum
    crc = crc8.calc(payload_32)
    # Append CRC to payload
    payload = payload_32 + bytes([crc])
    return payload

async def send_command(counter: int, freshness_counter: int, command: int):
    async with BleakClient(DEVICE_ADDRESS) as client:
        payload = build_ble_command(counter, freshness_counter, command)
        await client.write_gatt_char(HANDLE, payload)
        print(f"Sent payload: {payload.hex()}")

if __name__ == "__main__":
    counter = 0x683e3823
    freshness_counter = int(time.time() // 60) & 0xFFFF  # Increment Byte 17 every minute
    command = COMMAND_OPCODE
    asyncio.run(send_command(counter, freshness_counter, command))