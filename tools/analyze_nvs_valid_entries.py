#!/usr/bin/env python3

import json
import sys
from pathlib import Path

PAGE_SIZE = 4096
HEADER_SIZE = 32
BITMAP_SIZE = 32
ENTRY_SIZE = 32
ENTRIES_OFFSET = 64

VALID_TYPES = set(range(1, 12))


def state(bitmap, index):
    byte = bitmap[index // 4]
    shift = (index % 4) * 2
    return (byte >> shift) & 3


def main():
    path = Path(sys.argv[1])
    raw = path.read_bytes()
    entries = []

    for page_index in range(len(raw) // PAGE_SIZE):
        page = raw[page_index * PAGE_SIZE:(page_index + 1) * PAGE_SIZE]
        bitmap = page[HEADER_SIZE:HEADER_SIZE + BITMAP_SIZE]
        index = 0

        while index < 126:
            if state(bitmap, index) != 2:
                index += 1
                continue

            offset = ENTRIES_OFFSET + index * ENTRY_SIZE
            entry = page[offset:offset + ENTRY_SIZE]

            namespace = entry[0]
            entry_type = entry[1]
            span = entry[2]
            chunk = entry[3]

            if entry_type not in VALID_TYPES or span < 1 or span > 126 - index:
                index += 1
                continue

            key = entry[8:24].split(b"\0", 1)[0].decode(
                "utf-8", errors="replace"
            )

            entries.append({
                "page": page_index,
                "entry": index,
                "namespace": namespace,
                "type": entry_type,
                "span": span,
                "chunk_index": chunk,
                "key": key,
            })

            index += span

    report = {
        "file": str(path),
        "valid_entry_starts": len(entries),
        "entries": entries,
    }

    output = Path("data/analysis/reports/nvs_valid_entries.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(json.dumps({
        "valid_entry_starts": len(entries),
        "report": str(output),
        "entries": entries,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
