#!/usr/bin/env python3

import re
import subprocess
import sys
from pathlib import Path

PORT = "/dev/ttyACM0"
CHIP = "esp32s3"
TOTAL_BYTES = 256
CHUNK_SIZE = 4

output = bytearray()

for address in range(0, TOTAL_BYTES, CHUNK_SIZE):
    print(f"Lecture SFDP à l'adresse 0x{address:02X}...")

    command = [
        ".venv/bin/esptool",
        "--chip", CHIP,
        "--port", PORT,
        "read-flash-sfdp",
        str(address),
        str(CHUNK_SIZE),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    text = result.stdout + result.stderr

    match = re.search(
        r"Flash memory SFDP\[\d+\.\.\d+\]:\s*((?:0x[0-9a-fA-F]{2}\s*)+)",
        text,
    )

    if result.returncode != 0 or not match:
        print(f"Erreur à l'adresse 0x{address:02X}")
        print(text)
        sys.exit(1)

    values = re.findall(
        r"0x([0-9a-fA-F]{2})",
        match.group(1),
    )

    if len(values) != CHUNK_SIZE:
        print(f"Nombre d'octets inattendu à 0x{address:02X}")
        print(text)
        sys.exit(1)

    output.extend(int(value, 16) for value in values)

output = output[:TOTAL_BYTES]

destination = Path("data/analysis/raw/sfdp_s3.bin")
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_bytes(output)

print()
print(f"Lecture terminée : {len(output)} octets")
print(f"Fichier enregistré : {destination}")
print(output.hex(" "))
