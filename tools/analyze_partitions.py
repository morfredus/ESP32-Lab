#!/usr/bin/env python3

import json
import struct
from pathlib import Path


INPUT = Path("data/analysis/raw/partition_table_s3.bin")
OUTPUT = Path("data/analysis/reports/partitions_s3_analysis.json")

ENTRY_SIZE = 32
MAGIC = 0x50AA

TYPE_NAMES = {
    0x00: "app",
    0x01: "data",
}

APP_SUBTYPES = {
    0x00: "factory",
    0x10: "ota_0",
    0x11: "ota_1",
    0x12: "ota_2",
}

DATA_SUBTYPES = {
    0x00: "ota",
    0x01: "phy",
    0x02: "nvs",
    0x03: "coredump",
    0x82: "spiffs",
    0x83: "littlefs",
}


def decode_entry(data, offset):
    if offset + ENTRY_SIZE > len(data):
        return None

    magic = struct.unpack_from("<H", data, offset)[0]

    if magic != MAGIC:
        return None

    partition_type = data[offset + 2]
    subtype = data[offset + 3]
    address = struct.unpack_from("<I", data, offset + 4)[0]
    size = struct.unpack_from("<I", data, offset + 8)[0]

    label_raw = data[offset + 12:offset + 28]
    label = label_raw.split(b"\x00", 1)[0].decode(
        "ascii",
        errors="replace",
    )

    if partition_type == 0x00:
        subtype_name = APP_SUBTYPES.get(
            subtype,
            f"unknown_0x{subtype:02X}",
        )
    elif partition_type == 0x01:
        subtype_name = DATA_SUBTYPES.get(
            subtype,
            f"unknown_0x{subtype:02X}",
        )
    else:
        subtype_name = f"unknown_0x{subtype:02X}"

    return {
        "table_offset": f"0x{offset:04X}",
        "type": f"0x{partition_type:02X}",
        "type_name": TYPE_NAMES.get(
            partition_type,
            f"unknown_0x{partition_type:02X}",
        ),
        "subtype": f"0x{subtype:02X}",
        "subtype_name": subtype_name,
        "address": f"0x{address:06X}",
        "size_bytes": size,
        "size_kib": round(size / 1024, 2),
        "end_address": f"0x{address + size:06X}",
        "label": label,
    }


def analyze_overlaps(partitions):
    warnings = []

    ordered = sorted(
        partitions,
        key=lambda item: int(item["address"], 16),
    )

    for previous, current in zip(ordered, ordered[1:]):
        previous_end = int(previous["end_address"], 16)
        current_start = int(current["address"], 16)

        if previous_end > current_start:
            warnings.append({
                "type": "overlap",
                "first": previous["label"],
                "second": current["label"],
                "message": (
                    f"Chevauchement entre {previous['label']} "
                    f"et {current['label']}."
                ),
            })

    return warnings


def main():
    if not INPUT.exists():
        raise SystemExit(f"Fichier absent : {INPUT}")

    data = INPUT.read_bytes()
    partitions = []

    for offset in range(0, len(data), ENTRY_SIZE):
        entry = decode_entry(data, offset)

        if entry is None:
            continue

        partitions.append(entry)

    report = {
        "file": str(INPUT),
        "size_bytes": len(data),
        "entry_size_bytes": ENTRY_SIZE,
        "partition_count": len(partitions),
        "partitions": partitions,
        "warnings": analyze_overlaps(partitions),
        "limitations": [
            "L'utilisation réelle des partitions n'est pas analysée.",
            "La table ne permet pas à elle seule de connaître "
            "l'espace réellement occupé.",
        ],
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(report, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )

    print(json.dumps(report, indent=4, ensure_ascii=False))
    print()
    print(f"Rapport enregistré : {OUTPUT}")


if __name__ == "__main__":
    main()
