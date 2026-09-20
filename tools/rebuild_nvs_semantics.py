"""
Reconstruit une analyse NVS en filtrant les entrées dont le CRC
correspond au format ESP32 NVS.

Lecture seule.
"""

import json
import zlib
from collections import Counter
from pathlib import Path


INPUT_FILE = Path(
    "data/analysis/reports/nvs_structure_analysis.json"
)

OUTPUT_FILE = Path(
    "data/analysis/reports/nvs_semantic_analysis.json"
)


def crc_esp32(data):
    return zlib.crc32(data, 0xFFFFFFFF) & 0xFFFFFFFF


def crc_matches(raw_hex, stored_hex):
    try:
        raw = bytes.fromhex(raw_hex)
        stored = int(stored_hex, 16)
    except (ValueError, TypeError):
        return False

    if len(raw) != 32:
        return False

    calculated = crc_esp32(raw[0:4] + raw[8:32])
    return calculated == stored


def is_readable_key(key):
    if not isinstance(key, str) or not key:
        return False

    return all(
        character.isprintable()
        for character in key
    )


def main():
    report = json.loads(
        INPUT_FILE.read_text(encoding="utf-8")
    )

    valid_entries = []
    rejected_entries = []
    key_counter = Counter()

    for page in report.get("pages", []):
        for entry in page.get("entries", []):
            if entry.get("state", {}).get("name") != "written":
                continue

            decoded = entry.get("decoded", {})
            raw_hex = decoded.get("raw_hex")
            stored_crc = decoded.get("crc_stored")
            key = decoded.get("key")

            valid_crc = crc_matches(raw_hex, stored_crc)
            readable_key = is_readable_key(key)

            item = {
                "page_index": page.get("page_index"),
                "entry_index": entry.get("index"),
                "offset": entry.get("offset"),
                "key": key,
                "type_name": decoded.get("type_name"),
                "span": decoded.get("span"),
                "chunk_index": decoded.get("chunk_index"),
                "crc_stored": stored_crc,
                "crc_match": valid_crc,
                "data_hex": decoded.get("data_hex"),
                "raw_hex": raw_hex,
            }

            if valid_crc and readable_key:
                valid_entries.append(item)
                key_counter[key] += 1
            else:
                rejected_entries.append({
                    **item,
                    "reasons": [
                        reason
                        for reason, condition in (
                            ("crc_incoherent", not valid_crc),
                            ("key_non_printable", not readable_key),
                        )
                        if condition
                    ],
                })

    duplicates = {
        key: count
        for key, count in key_counter.items()
        if count > 1
    }

    result = {
        "source": str(INPUT_FILE),
        "summary": {
            "valid_entries": len(valid_entries),
            "rejected_entries": len(rejected_entries),
            "unique_keys": len(key_counter),
            "duplicate_keys": len(duplicates),
        },
        "keys": dict(sorted(key_counter.items())),
        "duplicate_keys": duplicates,
        "valid_entries": valid_entries,
        "rejected_entries": rejected_entries,
        "limitations": [
            "Le regroupement des entrées multi-slots doit encore "
            "être corrigé dans l'analyseur structurel.",
            "Les entrées rejetées sont conservées pour audit.",
            "Une clé lisible ne garantit pas que sa valeur soit décodée.",
        ],
    }

    OUTPUT_FILE.write_text(
        json.dumps(result, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"[OK] Rapport reconstruit : {OUTPUT_FILE}")
    print(f"[INFO] Entrées valides : {len(valid_entries)}")
    print(f"[INFO] Entrées rejetées : {len(rejected_entries)}")
    print(f"[INFO] Clés uniques : {len(key_counter)}")
    print(f"[INFO] Clés dupliquées : {len(duplicates)}")


if __name__ == "__main__":
    main()
