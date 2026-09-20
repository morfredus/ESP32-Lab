#!/usr/bin/env python3

import json
import struct
import sys
from pathlib import Path

PAGE_SIZE = 4096
ENTRY_SIZE = 32
ENTRIES_OFFSET = 64
HEADER_SIZE = 32
BITMAP_SIZE = 32


def get_state(bitmap, index):
    byte = bitmap[index // 4]
    shift = (index % 4) * 2
    return (byte >> shift) & 3


def main():
    path = Path(sys.argv[1])
    raw = path.read_bytes()
    results = []

    for page_index in range(len(raw) // PAGE_SIZE):
        page = raw[page_index * PAGE_SIZE:(page_index + 1) * PAGE_SIZE]
        bitmap = page[HEADER_SIZE:HEADER_SIZE + BITMAP_SIZE]

        for index in range(126):
            if get_state(bitmap, index) != 2:
                continue

            offset = ENTRIES_OFFSET + index * ENTRY_SIZE
            entry = page[offset:offset + ENTRY_SIZE]

            namespace = entry[0]
            entry_type = entry[1]
            span = entry[2]
            chunk = entry[3]

            if span != 1 or chunk != 255:
                continue

            if entry_type not in (1, 2, 3, 4, 5, 6):
                continue

            key = entry[8:24].split(b"\0", 1)[0].decode(
                "utf-8", errors="replace"
            )

            results.append({
                "page": page_index,
                "entry": index,
                "namespace": namespace,
                "type": entry_type,
                "key": key,
                "value_hex": entry[24:32].hex(" "),
                "value_u64_le": struct.unpack("<Q", entry[24:32])[0],
            })

    output = Path("data/analysis/reports/nvs_scalar_values.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    for item in results:
        print(
            f"page={item['page']} | "
            f"namespace={item['namespace']} | "
            f"type={item['type']} | "
            f"{item['key']} | "
            f"{item['value_hex']}"
        )

    print(f"\nRapport : {output}")


if __name__ == "__main__":
    main()
