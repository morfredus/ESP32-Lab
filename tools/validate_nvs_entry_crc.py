#!/usr/bin/env python3

import json
import struct
import sys
import zlib
from pathlib import Path

ENTRY_SIZE = 32
PAGE_SIZE = 4096
HEADER_SIZE = 32
BITMAP_SIZE = 32
ENTRIES_OFFSET = HEADER_SIZE + BITMAP_SIZE


def crc_standard(data):
    return zlib.crc32(data) & 0xFFFFFFFF


def crc_init_ff(data):
    return zlib.crc32(data, 0xFFFFFFFF) & 0xFFFFFFFF


def crc_reflected(data, initial):
    crc = initial

    for byte in data:
        crc ^= byte

        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xEDB88320
            else:
                crc >>= 1

    return crc & 0xFFFFFFFF


def crc_variants(data):
    return {
        "zlib_standard": crc_standard(data),
        "zlib_init_ff": crc_init_ff(data),
        "reflected_init_0": crc_reflected(data, 0),
        "reflected_init_ff": crc_reflected(data, 0xFFFFFFFF),
    }


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <nvs.bin>")
        sys.exit(1)

    path = Path(sys.argv[1])
    raw = path.read_bytes()

    results = []

    for page_index in range(len(raw) // PAGE_SIZE):
        page_offset = page_index * PAGE_SIZE
        page = raw[page_offset:page_offset + PAGE_SIZE]

        if page == b"\xFF" * PAGE_SIZE:
            continue

        for entry_index in range(126):
            offset = ENTRIES_OFFSET + entry_index * ENTRY_SIZE
            entry = page[offset:offset + ENTRY_SIZE]

            if len(entry) != ENTRY_SIZE:
                continue

            bitmap_byte_offset = entry_index // 4
            bitmap_shift = (entry_index % 4) * 2
            bitmap_value = (
                page[HEADER_SIZE + bitmap_byte_offset] >> bitmap_shift
            ) & 0x03

            # 0b10 = written
            if bitmap_value != 0b10:
                continue

            stored_crc = struct.unpack_from("<I", entry, 4)[0]
            crc_data = entry[8:32]
            variants = crc_variants(crc_data)

            matches = [
                name
                for name, value in variants.items()
                if value == stored_crc
            ]

            key = entry[8:24].split(b"\x00", 1)[0].decode(
                "utf-8", errors="replace"
            )

            results.append({
                "page": page_index,
                "entry": entry_index,
                "offset": f"0x{page_offset + offset:05X}",
                "key": key,
                "stored_crc": f"0x{stored_crc:08X}",
                "matches": matches,
                "variants": {
                    name: f"0x{value:08X}"
                    for name, value in variants.items()
                },
            })

    total = len(results)
    matched = sum(1 for item in results if item["matches"])

    report = {
        "file": str(path),
        "written_entries": total,
        "entries_with_crc_match": matched,
        "entries_without_crc_match": total - matched,
        "results": results,
        "limitations": [
            "Les variantes CRC sont comparées à titre diagnostique.",
            "Une absence de correspondance ne prouve pas une corruption.",
            "Le format exact et la zone CRC doivent être confirmés avec la version ESP-IDF utilisée."
        ],
    }

    output = Path("data/analysis/reports/nvs_entry_crc_validation.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(json.dumps({
        "written_entries": total,
        "entries_with_crc_match": matched,
        "entries_without_crc_match": total - matched,
        "report": str(output),
    }, indent=2))


if __name__ == "__main__":
    main()
