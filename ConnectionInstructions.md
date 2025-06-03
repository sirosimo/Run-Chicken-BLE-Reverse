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

| Byte Range | Purpose           | Description                                                                            |
| ---------- | ----------------- | -------------------------------------------------------------------------------------- |
| 0–3        | Nonce / Counter   | 4-byte little-endian number; unique per command                                        |
| 4–7        | Device ID / Fixed | Fixed: `68 40 3A 68`                                                                   |
| 8–11       | Echo of Counter   | Same as bytes 0–3 (for redundancy or validation)                                       |
| 12–13      | Signature         | Constant: `3A 68`                                                                      |
| 14–15      | Reserved          | Always `00 00`                                                                         |
| 16–17      | Freshness Counter | 2-byte monotonic value: Byte 17 changes every minute; Byte 16 changes less predictably |
| 18–19      | Mirror of 16–17   | Same as 16–17                                                                          |
| 20–23      | Reserved          | Always `00 00 00 00`                                                                   |
| 24         | Command           | `01 = open`, `02 = close`                                                              |
| 25–31      | Padding           | Always `00 00 00 00 00 00 00`                                                          |
| 32         | CRC-8/SMBus       | Calculated over bytes 0–31 using the `anycrc` Python library                           |

**Note on Freshness Counter (Bytes 16–17):**

* Byte 17 appears to increment once per minute (modulo 256)
* Byte 16 changes less predictably and may represent a session ID or boot counter
* Use mirrored 2-byte value across both 16–17 and 18–19
* For best results, update Byte 17 every minute and reuse Byte 16 unless a pattern emerges

---

## Python Example Code Using `anycrc`

```python
import anycrc
import struct

def build_ble_command(counter: int, freshness: int, command: int) -> bytes:
    c_bytes = struct.pack('<I', counter)
    fixed_id = bytes.fromhex('68403a68')
    echo = c_bytes
    signature = bytes.fromhex('3a68')
    reserved = b'\x00\x00'

    freshness_bytes = freshness.to_bytes(2, 'big')
    ts_block = freshness_bytes + freshness_bytes  # mirrored

    reserved2 = b'\x00\x00\x00\x00'
    cmd = bytes([command])
    pad = b'\x00' * 7

    payload = (
        c_bytes + fixed_id + echo + signature + reserved +
        ts_block + reserved2 + cmd + pad
    )

    crc8 = anycrc.Model('CRC8-SMBUS')
    crc = crc8.calc(payload)
    return payload + bytes([crc])

# Example usage
payload = build_ble_command(counter=0x008a403a, freshness=0x1722, command=0x01)
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
4. Update the counter and freshness fields for every command.
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
* Timestamp bytes 16–19 should increment slowly and stay mirrored.
* If commands fail, double-check CRC and freshness of mirrored timestamp bytes.

---

For questions or changes to this payload format, analyze additional packets using Wireshark or Android HCI dumps and compare evolving fields.
