#!/usr/bin/env python3

import json
import struct
import sys
from collections import Counter
from pathlib import Path

PAGE_SIZE = 4096
HEADER_SIZE = 32
BITMAP_SIZE = 32
ENTRY_SIZE = 32
ENTRIES_OFFSET = HEADER_SIZE + BITMAP_SIZE


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <nvs.bin>")
        sys.exit(1)

    path = Path(sys.argv[1])
    raw = path.read_bytes()

    entries = []

    for page_index in range(len(raw) // PAGE_SIZE):
        page = raw[page_index * PAGE_SIZE:(page_index + 1) * PAGE_SIZE]

        if page == b"\xff" * PAGE_SIZE:
            continue

        for entry_index in range(126):
            bitmap_pos = HEADER_SIZE + entry_index // 4
            shift = (entry_index % 4) * 2
            state = (page[bitmap_pos] >> shift) & 0x03

            if state != 0b10:
                continue

            offset = ENTRIES_OFFSET + entry_index * ENTRY_SIZE
            entry = page[offset:offset + ENTRY_SIZE]

            namespace_index = entry[0]
            entry_type = entry[1]
            span = entry[2]
            chunk_index = entry[3]

            key = ""
            if chunk_index == 0 or span == 1:
                key = entry[8:24].split(b"\0", 1)[0].decode(
                    "utf-8", errors="replace"
                )

            entries.append({
                "page": page_index,
                "entry": entry_index,
                "namespace": namespace_index,
                "type": entry_type,
                "span": span,
                "chunk_index": chunk_index,
                "key": key,
            })

    report = {
        "file": str(path),
        "entry_count": len(entries),
        "span_distribution": dict(
            sorted(
                Counter(item["span"] for item in entries).items()
            )
        ),
        "type_distribution": dict(
            sorted(
                Counter(item["type"] for item in entries).items()
            )
        ),
        "chunk_distribution": dict(
            sorted(
                Counter(item["chunk_index"] for item in entries).items()
            )
        ),
        "entries": entries,
    }

    output = Path("data/analysis/reports/nvs_entries_analysis.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(json.dumps({
        "entry_count": len(entries),
        "span_distribution": report["span_distribution"],
        "type_distribution": report["type_distribution"],
        "report": str(output),
    }, indent=2))


if __name__ == "__main__":
    main()
