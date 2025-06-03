import asyncio
import struct
import time
import crcmod
from bleak import BleakClient

# --- User-configurable variables ---
DEVICE_ADDRESS = "00:80:E1:22:C2:7C"  # Your device's MAC address
CHARACTERISTIC_UUID = "00000000-8e22-4541-9d4c-21edae82ed19"  # Your characteristic UUID
COMMAND_OPCODE = 0x02  # 0x01 = Open, 0x02 = Close

# CRC-8/SMBus setup (poly=0x31, init=0x00, xorOut=0x00, reversed)
crc8 = crcmod.mkCrcFun(0x131, initCrc=0x00, xorOut=0x00, rev=True)
def get_mirrored_counter_block(counter_value: int) -> bytes:
    b = counter_value.to_bytes(2, byteorder='big')
    return b + b

def build_ble_command(counter: int, session_counter: int, command: int) -> bytes:
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
    ts = struct.pack('>H', session_counter & 0xFFFF)
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
    assert len(payload_32) == 32, f"Payload before CRC should be 32 bytes, got {len(payload_32)}"

    # CRC-8/SMBus over first 32 bytes
    crc = crc8(payload_32)
    payload = payload_32 + bytes([crc])
    assert len(payload) == 33, f"Final payload should be 33 bytes, got {len(payload)}"
    return payload

async def connect_and_send_command(address, char_uuid, command_opcode):
    print(f"Attempting to connect to BLE device at {address}...")
    try:
        async with BleakClient(address) as client:
            connected = await client.is_connected()
            if connected:
                print(f"Connected to {address}")
                # Use current time for counter and session_counter (mirrored block)
                counter = int(time.time()) & 0xFFFFFFFF
                session_counter = int(time.time() // 30) & 0xFFFF  # increments every 30s, mirrored
                payload = build_ble_command(counter, session_counter, command_opcode)
                print(f"Sending command ({len(payload)} bytes): {payload.hex()}")
                await client.write_gatt_char(char_uuid, payload, response=True)
                print("Command sent. Staying connected for 5 seconds...")
                await asyncio.sleep(5)
                print("Disconnecting.")
            else:
                print(f"Failed to connect to {address}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(connect_and_send_command(DEVICE_ADDRESS, CHARACTERISTIC_UUID, COMMAND_OPCODE))