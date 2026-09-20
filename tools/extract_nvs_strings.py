#!/usr/bin/env python3

from pathlib import Path
import re

RAW = Path("data/analysis/raw/nvs_s3.bin").read_bytes()

PAGE_SIZE = 4096
HEADER_SIZE = 0x40
ENTRY_SIZE = 32

TARGETS = [
    (0, 71, 3, "sta.ssid"),
    (0, 75, 4, "sta.pswd"),
    (1, 3, 4, "ap.passwd"),
    (4, 1, 3, "ap.ssid"),
]


def extract_ascii(data):
    matches = re.findall(rb"[ -~]{4,}", data)
    return [
        item.decode("ascii", errors="replace")
        for item in matches
    ]


for page, entry, span, name in TARGETS:
    base = (
        page * PAGE_SIZE
        + HEADER_SIZE
        + entry * ENTRY_SIZE
    )

    block = bytearray()

    for slot in range(span):
        offset = base + slot * ENTRY_SIZE
        block.extend(RAW[offset:offset + ENTRY_SIZE])

    strings = extract_ascii(bytes(block))

    print(f"\n=== {name} ===")

    if name in ("sta.pswd", "ap.passwd"):
        print("[SECRET MASQUÉ]")
        print(f"Chaînes ASCII détectées : {len(strings)}")
    else:
        for value in strings:
            print(f"[STRING] {value}")
