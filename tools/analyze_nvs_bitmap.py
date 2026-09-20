#!/usr/bin/env python3

import json
import sys
from collections import Counter
from pathlib import Path

PAGE_SIZE = 4096
HEADER_SIZE = 32
BITMAP_SIZE = 32
ENTRY_SIZE = 32
ENTRIES_OFFSET = 64


def get_state(bitmap, index, msb_first):
    byte = bitmap[index // 4]
    shift = (3 - index % 4) * 2 if msb_first else (index % 4) * 2
    return (byte >> shift) & 0x03


def main():
    path = Path(sys.argv[1])
    raw = path.read_bytes()
    result = {}

    for msb_first in (False, True):
        states = []
        valid_entries = []

        for page_index in range(len(raw) // PAGE_SIZE):
            page = raw[page_index * PAGE_SIZE:(page_index + 1) * PAGE_SIZE]
            if page == b"\xff" * PAGE_SIZE:
                continue

            bitmap = page[HEADER_SIZE:HEADER_SIZE + BITMAP_SIZE]

            for index in range(126):
                state = get_state(bitmap, index, msb_first)
                states.append(state)

                if state == 2:
                    entry_offset = ENTRIES_OFFSET + index * ENTRY_SIZE
                    entry = page[entry_offset:entry_offset + ENTRY_SIZE]

                    valid_entries.append({
                        "page": page_index,
                        "entry": index,
                        "namespace": entry[0],
                        "type": entry[1],
                        "span": entry[2],
                        "chunk_index": entry[3],
                        "key": entry[8:24].split(b"\0", 1)[0].decode(
                            "utf-8", errors="replace"
                        ),
                    })

        result["msb_first" if msb_first else "lsb_first"] = {
            "state_distribution": dict(Counter(states)),
            "written_entries": len(valid_entries),
            "entries": valid_entries,
        }

    output = Path("data/analysis/reports/nvs_bitmap_analysis.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    for mode, data in result.items():
        print(f"\n[{mode}]")
        print(f"written_entries: {data['written_entries']}")
        print(f"state_distribution: {data['state_distribution']}")
        print("examples:")
        for entry in data["entries"][:8]:
            print(
                f"  page={entry['page']} entry={entry['entry']} "
                f"type={entry['type']} span={entry['span']} "
                f"chunk={entry['chunk_index']} key={entry['key']!r}"
            )

    print(f"\nReport: {output}")


if __name__ == "__main__":
    main()
