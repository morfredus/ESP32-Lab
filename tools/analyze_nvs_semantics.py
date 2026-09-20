"""
Analyse sémantique du rapport NVS déjà extrait.
Lecture seule : aucune modification de la mémoire Flash.
"""

import json
import sys
from collections import Counter
from pathlib import Path


INPUT_FILE = Path(
    "data/analysis/reports/nvs_structure_analysis.json"
)

OUTPUT_FILE = Path(
    "data/analysis/reports/nvs_semantic_analysis.json"
)


def is_printable_text(value):
    if not isinstance(value, str) or not value:
        return False

    try:
        raw = bytes.fromhex(value)
        decoded = raw.rstrip(b"\x00").decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return False

    return bool(decoded) and all(
        character.isprintable() or character.isspace()
        for character in decoded
    )


def decode_hex_text(value):
    try:
        raw = bytes.fromhex(value)
        return raw.rstrip(b"\x00").decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None


def main():
    if not INPUT_FILE.exists():
        raise SystemExit(
            f"[ERREUR] Fichier absent : {INPUT_FILE}"
        )

    report = json.loads(
        INPUT_FILE.read_text(encoding="utf-8")
    )

    pages_summary = []
    entries_summary = []
    key_counter = Counter()
    crc_errors = []
    readable_values = []
    binary_values = []

    for page in report.get("pages", []):
        page_index = page.get("page_index")
        state_name = page.get("state_name")

        page_entry_count = 0

        for entry in page.get("entries", []):
            if entry.get("state", {}).get("name") != "written":
                continue

            decoded = entry.get("decoded", {})
            key = decoded.get("key")
            data_hex = decoded.get("data_hex", "")
            crc_match = decoded.get("crc_match")

            page_entry_count += 1

            if key:
                key_counter[key] += 1

            item = {
                "page_index": page_index,
                "entry_index": entry.get("index"),
                "offset": entry.get("offset"),
                "key": key,
                "type_name": decoded.get("type_name"),
                "span": decoded.get("span"),
                "chunk_index": decoded.get("chunk_index"),
                "crc_match": crc_match,
                "data_hex": data_hex,
            }

            decoded_text = decode_hex_text(data_hex)

            if is_printable_text(data_hex):
                item["value_class"] = "text"
                item["decoded_text"] = decoded_text
                readable_values.append(item)
            else:
                item["value_class"] = "binary"
                binary_values.append(item)

            entries_summary.append(item)

            if crc_match is False:
                crc_errors.append({
                    "page_index": page_index,
                    "entry_index": entry.get("index"),
                    "offset": entry.get("offset"),
                    "key": key,
                    "stored_crc": decoded.get("crc_stored"),
                    "calculated_crc": decoded.get("crc_calculated"),
                })

        pages_summary.append({
            "page_index": page_index,
            "state_name": state_name,
            "sequence": page.get("sequence"),
            "written_entries": page_entry_count,
        })

    duplicate_keys = {
        key: count
        for key, count in key_counter.items()
        if count > 1
    }

    result = {
        "source": str(INPUT_FILE),
        "summary": {
            "pages": len(report.get("pages", [])),
            "written_entries": len(entries_summary),
            "unique_keys": len(key_counter),
            "duplicate_keys": len(duplicate_keys),
            "crc_errors": len(crc_errors),
            "readable_text_values": len(readable_values),
            "binary_values": len(binary_values),
        },
        "pages": pages_summary,
        "keys": dict(sorted(key_counter.items())),
        "duplicate_keys": duplicate_keys,
        "crc_errors": crc_errors,
        "readable_values": readable_values,
        "binary_values": binary_values,
        "limitations": [
            "Les valeurs multi-slots ne sont pas reconstituées.",
            "Les données binaires ne sont pas interprétées automatiquement.",
            "Un CRC incohérent ne prouve pas à lui seul une corruption.",
            "Les données potentiellement chiffrées ne sont pas déchiffrées.",
        ],
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(result, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"[OK] Rapport créé : {OUTPUT_FILE}")
    print(
        f"[INFO] Entrées écrites : "
        f"{result['summary']['written_entries']}"
    )
    print(
        f"[INFO] Clés uniques : "
        f"{result['summary']['unique_keys']}"
    )
    print(
        f"[INFO] CRC incohérents : "
        f"{result['summary']['crc_errors']}"
    )
    print(
        f"[INFO] Valeurs texte : "
        f"{result['summary']['readable_text_values']}"
    )
    print(
        f"[INFO] Valeurs binaires : "
        f"{result['summary']['binary_values']}"
    )


if __name__ == "__main__":
    main()
