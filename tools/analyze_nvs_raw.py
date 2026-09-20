#!/usr/bin/env python3

import json
import math
import sys
from pathlib import Path

PAGE_SIZE = 4096
HEADER_SIZE = 32
BITMAP_SIZE = 32
ENTRIES_OFFSET = 64
ENTRIES_SIZE = 126 * 32


def entropy(data):
    if not data:
        return 0.0

    counts = {}
    for byte in data:
        counts[byte] = counts.get(byte, 0) + 1

    total = len(data)
    return -sum(
        (count / total) * math.log2(count / total)
        for count in counts.values()
    )


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <nvs.bin>")
        sys.exit(1)

    path = Path(sys.argv[1])
    raw = path.read_bytes()
    pages = []

    for index in range(len(raw) // PAGE_SIZE):
        page = raw[index * PAGE_SIZE:(index + 1) * PAGE_SIZE]

        if page == b"\xff" * PAGE_SIZE:
            continue

        header = page[:HEADER_SIZE]
        bitmap = page[HEADER_SIZE:ENTRIES_OFFSET]
        entries = page[ENTRIES_OFFSET:ENTRIES_OFFSET + ENTRIES_SIZE]

        pages.append({
            "page": index,
            "header_hex": header.hex(" "),
            "bitmap_hex": bitmap.hex(" "),
            "entries_entropy": round(entropy(entries), 4),
            "entries_first_64_hex": entries[:64].hex(" "),
            "non_ff_entries_bytes": sum(
                byte != 0xFF for byte in entries
            ),
        })

    report = {
        "file": str(path),
        "size_bytes": len(raw),
        "pages": pages,
        "limitations": [
            "Analyse brute des pages, sans décodage des entrées.",
            "L'entropie seule ne permet pas de conclure à un chiffrement.",
            "Les données NVS peuvent nécessiter la configuration exacte d'ESP-IDF."
        ],
    }

    output = Path("data/analysis/reports/nvs_raw_analysis.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
