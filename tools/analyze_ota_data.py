#!/usr/bin/env python3

import json
import struct
import sys
import zlib
from pathlib import Path


SECTOR_SIZE = 4096
ENTRY_SIZE = 32


def crc32_standard(data):
    return zlib.crc32(data) & 0xFFFFFFFF


def crc32_esp32(data):
    return zlib.crc32(data, 0xFFFFFFFF) & 0xFFFFFFFF


def decode_state(state):
    states = {
        0: "NEW",
        1: "PENDING_VERIFY",
        2: "VALID",
        3: "INVALID",
        4: "ABORTED",
        0xFFFFFFFF: "UNDEFINED_OR_ERASED",
    }

    return states.get(
        state,
        f"UNKNOWN (0x{state:08X})"
    )


def decode_entry(data, offset):
    entry = data[offset:offset + ENTRY_SIZE]

    if len(entry) < ENTRY_SIZE:
        return {
            "offset": f"0x{offset:04X}",
            "valid_length": False,
            "reason": "Entrée incomplète",
        }

    ota_seq = struct.unpack_from("<I", entry, 0)[0]
    seq_label = entry[4:24]
    ota_state = struct.unpack_from("<I", entry, 24)[0]
    stored_crc = struct.unpack_from("<I", entry, 28)[0]

    crc_first_4_standard = crc32_standard(entry[:4])
    crc_first_4_esp32 = crc32_esp32(entry[:4])
    crc_first_28_standard = crc32_standard(entry[:28])
    crc_first_28_esp32 = crc32_esp32(entry[:28])

    erased = all(value == 0xFF for value in entry)

    return {
        "offset": f"0x{offset:04X}",
        "valid_length": True,
        "erased": erased,
        "ota_seq": ota_seq,
        "sequence_label_hex": seq_label.hex(),
        "ota_state_raw": f"0x{ota_state:08X}",
        "ota_state_name": decode_state(ota_state),
        "stored_crc": f"0x{stored_crc:08X}",
        "crc_candidates": {
            "first_4_standard": f"0x{crc_first_4_standard:08X}",
            "first_4_esp32_init_ff": f"0x{crc_first_4_esp32:08X}",
            "first_28_standard": f"0x{crc_first_28_standard:08X}",
            "first_28_esp32_init_ff": f"0x{crc_first_28_esp32:08X}",
        },
        "crc_matches": {
            "first_4_standard": stored_crc == crc_first_4_standard,
            "first_4_esp32_init_ff": stored_crc == crc_first_4_esp32,
            "first_28_standard": stored_crc == crc_first_28_standard,
            "first_28_esp32_init_ff": stored_crc == crc_first_28_esp32,
        },
        "raw_hex": entry.hex(),
    }


def main():
    if len(sys.argv) != 2:
        print(
            f"Usage: {sys.argv[0]} "
            "data/analysis/raw/otadata_s3.bin"
        )
        return 1

    input_path = Path(sys.argv[1])

    if not input_path.is_file():
        print(f"[ERREUR] Fichier introuvable : {input_path}")
        return 1

    data = input_path.read_bytes()

    result = {
        "file": str(input_path),
        "size_bytes": len(data),
        "expected_size_bytes": SECTOR_SIZE * 2,
        "entries": [],
        "warnings": [],
        "limitations": [
            "Les variantes CRC sont affichées à titre de comparaison.",
            "Le format exact du CRC doit être confirmé avec "
            "l'implémentation ESP-IDF correspondant à la version du firmware.",
            "Une entrée OTA valide ne prouve pas seule le firmware actuellement exécuté.",
        ],
    }

    if len(data) < SECTOR_SIZE * 2:
        result["warnings"].append(
            "Le fichier est plus petit que les deux secteurs OTA attendus."
        )

    for sector in range(2):
        offset = sector * SECTOR_SIZE

        result["entries"].append({
            "sector": sector,
            "sector_offset": f"0x{offset:04X}",
            "entry": decode_entry(data, offset),
        })

    output_path = Path(
        "data/analysis/reports/ota_data_analysis.json"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(
            result,
            indent=4,
            ensure_ascii=False
        ),
        encoding="utf-8",
    )

    print(json.dumps(
        result,
        indent=4,
        ensure_ascii=False
    ))

    print(f"\nRapport enregistré : {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
