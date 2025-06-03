import struct
import crcmod

# Use the SMBus predefined CRC
crc8 = crcmod.predefined.mkCrcFun('crc-8-smbus')

def build_ble_command(counter: int, session_counter: int, command: int) -> bytes:
    c_bytes = struct.pack('<I', counter)
    fixed = bytes.fromhex('68403a68')
    echo = c_bytes
    signature = bytes.fromhex('3a68')
    reserved1 = bytes([0x00, 0x00])
    ts = struct.pack('>H', session_counter & 0xFFFF)
    ts_block = ts + ts
    reserved2 = bytes([0x00, 0x00, 0x00, 0x00])
    cmd = bytes([command])
    padding = bytes([0x00] * 7)
    payload_32 = (
        c_bytes + fixed + echo + signature + reserved1 +
        ts_block + reserved2 + cmd + padding
    )
    crc = crc8(payload_32)
    payload = payload_32 + bytes([crc])
    return payload

if __name__ == "__main__":
    counter = 0x683e3823
    session_counter = 0x8a67
    command = 0x02
    payload = build_ble_command(counter, session_counter, command)
    print(f"Test payload: {payload.hex()}")
    print(f"Expected CRC (last byte): {payload[-1]:02x}")