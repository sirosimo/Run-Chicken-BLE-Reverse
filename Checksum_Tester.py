import random
import anycrc

# Initialize the CRC-8/SMBUS model
crc8 = anycrc.Model('CRC8-SMBUS')

def generate_random_payload() -> bytes:
    # Generate a random 8-byte payload
    payload = bytes(random.getrandbits(8) for _ in range(8))
    return payload

def append_crc_to_payload(payload: bytes) -> bytes:
    # Calculate the CRC checksum for the payload
    crc = crc8.calc(payload)
    # Append the checksum to the payload
    return payload + bytes([crc])

if __name__ == "__main__":
    # Generate a random payload
    payload = generate_random_payload()
    # Append the CRC checksum
    payload_with_crc = append_crc_to_payload(payload)
    
    print(f"Random payload: {payload.hex()}")
    print(f"Payload with CRC: {payload_with_crc.hex()}")
    print(f"CRC (last byte): {payload_with_crc[-1]:02x}")