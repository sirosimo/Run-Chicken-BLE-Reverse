# BLE Command Guide: Open/Close BLE Device via Custom Payload

This guide documents how to generate and send BLE commands to control a Bluetooth Low Energy (BLE) device using a custom 33-byte payload. The command can be used to open or close a device remotely. This was reverse-engineered and validated with a CRC-8/SMBus checksum.

---

## Device Characteristics

* **Protocol**: BLE (Bluetooth Low Energy)
* **Write Type**: Write Request
* **Service UUID**: `00000000-cc7a-482a-984a-7f2ed5b3e58f`
* **Characteristic UUID**: `00000000-8e22-4541-9d4c-21edae82ed19`
* **Handle**: `0x0012`
* **Payload Size**: 33 bytes
* **Checksum**: CRC-8/SMBus over the first 32 bytes (using `anycrc` library)

---

## Payload Format (33 Bytes)

| Byte Range | Purpose            | Description                                                                         |
| ---------- | ------------------ | ----------------------------------------------------------------------------------- |
| 0–3        | Nonce / Session ID | 4-byte value; changes per command and session, possibly a rolling or random counter |
| 4–7        | Nonce Echo         | Exact copy of bytes 0–3 (validation or replay protection)                           |
| 8–13       | Reserved Padding   | Always `00 00 00 00 00 00`                                                          |
| 14–15      | Reserved           | Always `00 00`                                                                      |
| 16         | UTC Hour           | Byte representing the UTC hour when command is sent                                 |
| 17         | UTC Minute         | Byte representing the current UTC minute                                            |
| 18         | Mirror of Byte 16  | Copy of Byte 16                                                                     |
| 19         | Mirror of Byte 17  | Copy of Byte 17                                                                     |
| 20–23      | Reserved           | Always `00 00 00 00`                                                                |
| 24         | Command            | `01 = open`, `02 = close`                                                           |
| 25–31      | Padding            | Always `00 00 00 00 00 00 00`                                                       |
| 32         | CRC-8/SMBus        | Calculated over bytes 0–31 using the `anycrc` Python library                        |

**Note on Time Tick (Bytes 16–19):**

* Bytes 16 and 17 represent the UTC hour and minute respectively.
* Bytes 18 and 19 are exact mirrors of 16 and 17.
* This provides freshness validation; values should be updated once per minute.

---

## Python Example Code Using `anycrc`

```python
import anycrc
import struct
from datetime import datetime, timezone

def get_current_tick() -> bytes:
    now = datetime.now(timezone.utc)
    h = now.hour
    m = now.minute
    return bytes([h, m, h, m])

def build_ble_command(counter: int, tick: bytes, command: int) -> bytes:
    c_bytes = struct.pack('<I', counter)
    echo = c_bytes
    reserved = b'\x00' * 6
    reserved2 = b'\x00\x00'
    reserved3 = b'\x00\x00\x00\x00'
    cmd = bytes([command])
    pad = b'\x00' * 7

    payload = (
        c_bytes + echo + reserved + reserved2 +
        tick + reserved3 + cmd + pad
    )

    crc8 = anycrc.Model('CRC8-SMBUS')
    crc = crc8.calc(payload)
    return payload + bytes([crc])

# Example usage
tick = get_current_tick()
payload = build_ble_command(counter=0x008a403a, tick=tick, command=0x01)
print("Payload:", payload.hex())
```

---

## Transmission Instructions

1. Connect to the BLE device as a GATT client.
2. Use the following identifiers:

   * **Service UUID**: `00000000-cc7a-482a-984a-7f2ed5b3e58f`
   * **Characteristic UUID**: `00000000-8e22-4541-9d4c-21edae82ed19`
   * **Handle**: `0x0012` (if writing by handle instead of UUID)
3. Write the 33-byte payload using a Write Request.
4. Update the counter and tick fields for every command.
5. The BLE device will process the command if the structure and checksum are valid.

---

## Command Opcodes

| Command | Byte Value (24) |
| ------- | --------------- |
| Open    | `0x01`          |
| Close   | `0x02`          |

---

## Notes

* Do **not** reuse counters or timestamp values — devices may reject old commands.
* Tick bytes 16–19 must mirror `[hour][minute][hour][minute]` in **UTC**.
* If commands fail, double-check CRC and freshness.

For questions or changes to this payload format, analyze additional packets using Wireshark or Android HCI dumps and compare evolving fields.
