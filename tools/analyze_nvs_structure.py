#!/usr/bin/env python3

import json
import struct
import sys
import zlib
from pathlib import Path


PAGE_SIZE = 4096
HEADER_SIZE = 32
BITMAP_SIZE = 32
ENTRY_SIZE = 32
ENTRY_COUNT = 126

ENTRIES_OFFSET = HEADER_SIZE + BITMAP_SIZE

ENTRY_STATES = {
    0b11: "empty",
    0b10: "written",
    0b00: "erased",
    0b01: "undefined",
}

NVS_TYPES = {
    0x00: "u8",
    0x01: "i8",
    0x02: "u16",
    0x03: "i16",
    0x04: "u32",
    0x05: "i32",
    0x06: "u64",
    0x07: "i64",
    0x08: "string",
    0x09: "blob",
    0x0A: "blob_data",
    0x0B: "blob_index",
}


def crc32_esp32(data):
    return zlib.crc32(data, 0xFFFFFFFF) & 0xFFFFFFFF


def decode_page_state(raw_state):
    states = {
        0xFFFFFFFF: "empty_or_uninitialized",
        0xFFFFFFFE: "active",
        0xFFFFFFFC: "full",
        0xFFFFFFF8: "erasing",
        0xFFFFFFF0: "corrupted",
    }

    return states.get(
        raw_state,
        f"unknown (0x{raw_state:08X})",
    )


def decode_entry_state(bitmap, index):
    bit_offset = index * 2
    byte_index = bit_offset // 8
    shift = bit_offset % 8

    value = (bitmap[byte_index] >> shift) & 0b11

    return {
        "raw": f"0b{value:02b}",
        "name": ENTRY_STATES.get(value, "unknown"),
    }


def decode_entry(entry):
    namespace_index = entry[0]
    entry_type = entry[1]
    span = entry[2]
    chunk_index = entry[3]

    crc_stored = struct.unpack_from("<I", entry, 4)[0]
    key_raw = entry[8:24]
    data_raw = entry[24:32]

    key = key_raw.split(b"\x00", 1)[0].decode(
        "utf-8",
        errors="replace",
    )

    crc_calculated = crc32_esp32(entry[8:32])

    return {
        "namespace_index": namespace_index,
        "type_raw": f"0x{entry_type:02X}",
        "type_name": NVS_TYPES.get(
            entry_type,
            f"unknown (0x{entry_type:02X})",
        ),
        "span": span,
        "chunk_index": chunk_index,
        "crc_stored": f"0x{crc_stored:08X}",
        "crc_calculated": f"0x{crc_calculated:08X}",
        "crc_match": crc_stored == crc_calculated,
        "key": key,
        "key_hex": key_raw.hex(),
        "data_hex": data_raw.hex(),
        "raw_hex": entry.hex(),
    }


def analyze_page(data, page_index):
    page_offset = page_index * PAGE_SIZE
    page = data[page_offset:page_offset + PAGE_SIZE]

    if len(page) < PAGE_SIZE:
        return {
            "page_index": page_index,
            "offset": f"0x{page_offset:05X}",
            "valid_size": False,
        }

    header = page[:HEADER_SIZE]
    bitmap = page[HEADER_SIZE:ENTRIES_OFFSET]

    state = struct.unpack_from("<I", header, 0)[0]
    sequence = struct.unpack_from("<I", header, 4)[0]
    version = header[8]

    stored_crc = struct.unpack_from("<I", header, 28)[0]
    calculated_crc = crc32_esp32(header[4:28])

    entries = []

    for index in range(ENTRY_COUNT):
        entry_offset = ENTRIES_OFFSET + index * ENTRY_SIZE
        entry = page[entry_offset:entry_offset + ENTRY_SIZE]

        entry_state = decode_entry_state(bitmap, index)

        item = {
            "index": index,
            "offset": f"0x{page_offset + entry_offset:05X}",
            "state": entry_state,
        }

        if entry_state["name"] == "written":
            item["decoded"] = decode_entry(entry)

        entries.append(item)

    written_count = sum(
        1 for item in entries
        if item["state"]["name"] == "written"
    )

    erased_count = sum(
        1 for item in entries
        if item["state"]["name"] == "erased"
    )

    empty_count = sum(
        1 for item in entries
        if item["state"]["name"] == "empty"
    )

    return {
        "page_index": page_index,
        "offset": f"0x{page_offset:05X}",
        "valid_size": True,
        "state_raw": f"0x{state:08X}",
        "state_name": decode_page_state(state),
        "sequence": sequence,
        "version": f"0x{version:02X}",
        "header_crc_stored": f"0x{stored_crc:08X}",
        "header_crc_calculated": f"0x{calculated_crc:08X}",
        "header_crc_match": stored_crc == calculated_crc,
        "bitmap_hex": bitmap.hex(),
        "entry_counts": {
            "written": written_count,
            "erased": erased_count,
            "empty": empty_count,
            "total": ENTRY_COUNT,
        },
        "entries": entries,
    }


def main():
    if len(sys.argv) != 2:
        print(
            f"Usage: {sys.argv[0]} "
            "data/analysis/raw/nvs_s3.bin"
        )
        return 1

    input_path = Path(sys.argv[1])

    if not input_path.is_file():
        print(f"[ERREUR] Fichier introuvable : {input_path}")
        return 1

    data = input_path.read_bytes()

    page_count = len(data) // PAGE_SIZE

    result = {
        "file": str(input_path),
        "size_bytes": len(data),
        "page_size_bytes": PAGE_SIZE,
        "page_count": page_count,
        "pages": [],
        "limitations": [
            "Les valeurs string/blob et les entrées multi-slots "
            "ne sont pas reconstituées automatiquement.",
            "Un CRC valide indique une cohérence de la zone contrôlée, "
            "pas l'absence de corruption logique.",
            "Les entrées peuvent être chiffrées dans une configuration "
            "NVS chiffrée.",
        ],
    }

    for page_index in range(page_count):
        result["pages"].append(
            analyze_page(data, page_index)
        )

    output_path = Path(
        "data/analysis/reports/nvs_structure_analysis.json"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(
            result,
            indent=4,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(json.dumps(
        result,
        indent=4,
        ensure_ascii=False,
    ))

    print(f"\nRapport enregistré : {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
