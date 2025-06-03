# BLE Command Guide: Open/Close BLE Device via Custom Payload

This guide documents how to generate and send BLE commands to control a Bluetooth Low Energy (BLE) device using a custom 33-byte payload. The command can be used to open or close a device remotely. This was reverse-engineered and validated with a CRC-8/SMBus checksum.

---

## Device Characteristics

* **Protocol**: BLE (Bluetooth Low Energy)
* **Write Type**: Write Request
* **Characteristic Handle**: `0x0012`
* **Payload Size**: 33 bytes
* **Checksum**: CRC-8/SMBus over the first 32 bytes

---

## Payload Format (33 Bytes)

| Byte Range | Purpose             | Description                                              |
| ---------- | ------------------- | -------------------------------------------------------- |
| 0–3        | Nonce / Counter     | 4-byte little-endian integer, must be unique per command |
| 4–7        | Fixed Session Bytes | Constant: `68 40 3A 68`                                  |
| 8–11       | Echo of Counter     | Exact copy of bytes 0–3                                  |
| 12–13      | Device Signature    | Constant: `3A 68`                                        |
| 14–15      | Reserved            | Always `00 00`                                           |
| 16–19      | Timestamp Block     | **Mirrored 2-byte monotonic counter**, increments slowly |
| 20–23      | Reserved            | Always `00 00 00 00`                                     |
| 24         | Command Opcode      | `0x01 = Open`, `0x02 = Close`                            |
| 25–31      | Padding             | Always `00 00 00 00 00 00 00`                            |
| 32         | CRC-8/SMBus         | Calculated over bytes 0–31                               |

---

## CRC-8/SMBus Details

* **Polynomial**: `0x31` (x^8 + x^5 + x^4 + 1)
* **Init**: `0x00`
* **XOR Out**: `0x00`
* **RefIn/RefOut**: True

Use a standard CRC-8/SMBus implementation to generate the checksum byte.

---

## Python Example Code

```python
import time
import struct
import crcmod

# Setup CRC-8/SMBus
crc8 = crcmod.predefined.mkPredefinedCrcFun('crc-8-smbus')

def get_mirrored_counter_block(counter_value: int) -> bytes:
    b = counter_value.to_bytes(2, byteorder='big')
    return b + b

def build_ble_command(counter: int, session_counter: int, command: int) -> bytes:
    c_bytes = struct.pack('<I', counter)
    fixed = bytes.fromhex('68403a68')
    echo = c_bytes
    header = c_bytes + fixed + echo + bytes.fromhex('3a680000')
    ts_block = get_mirrored_counter_block(session_counter)
    reserved = b'\x00' * 4
    cmd_block = bytes([command]) + b'\x00' * 7
    payload = header + ts_block + reserved + cmd_block
    crc = crc8(payload)
    return payload + bytes([crc])

# Example usage
payload = build_ble_command(0x009e403a, 0x1722, 0x01)  # Open command
print("BLE Payload:", payload.hex())
```

---

## Timestamp Field Clarification (Bytes 16–19)

Analysis of BLE packet logs shows that bytes 16–19:

* Are two identical 2-byte values (mirrored)
* Increment slowly over time, not with every command
* Do not directly correlate with epoch time or Unix timestamps

**Interpretation:**
This field appears to be a **monotonic session or freshness counter** used by the device to:

* Prevent replay attacks
* Validate command recency
* Possibly synchronize with internal timing logic

**Recommended Strategy:**

* Treat it as a 16-bit integer that increments periodically (e.g., every 10–30 seconds)
* Mirror the value across both halves
* Increment it with every command or group of commands to avoid reuse

---

## Transmission Instructions

1. Connect to the BLE device as a GATT client.
2. Write the 33-byte payload to characteristic handle `0x0012` using a Write Request.
3. Update the counter and timestamp for each new command.
4. The BLE device will process the command if the structure and checksum are valid.

---

## Command Opcodes

| Command | Byte Value (24) |
| ------- | --------------- |
| Open    | `0x01`          |
| Close   | `0x02`          |

---

## Notes

* Do **not** reuse counters or timestamp values — devices may reject old commands.
* Timestamp bytes 16–19 should increment slowly and stay mirrored.
* If commands fail, double-check CRC and freshness of mirrored timestamp bytes.

---

For questions or changes to this payload format, analyze additional packets using Wireshark or Android HCI dumps and compare evolving fields.
