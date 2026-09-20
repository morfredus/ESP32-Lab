#!/usr/bin/env python3

import json
import struct
from pathlib import Path

SOURCE = Path("data/analysis/reports/nvs_semantic_analysis.json")
OUTPUT = Path("data/analysis/reports/nvs_reconstructed_values.json")


def printable(data):
    return all(
        byte in (9, 10, 13) or 32 <= byte <= 126
        for byte in data
    )


def decode_scalar(entry):
    data = bytes.fromhex(entry.get("data_hex", ""))

    if entry.get("type_name") == "i8" and data:
        return struct.unpack("<b", data[:1])[0]

    if entry.get("type_name") == "u16" and len(data) >= 2:
        return struct.unpack("<H", data[:2])[0]

    if entry.get("type_name") == "u32" and len(data) >= 4:
        return struct.unpack("<I", data[:4])[0]

    if entry["key"] == "WIFI_STA_DEF" and len(data) >= 4:
        ip = ".".join(str(x) for x in data[:4])
        return ip

    if entry["key"] == "bl_crash_count" and len(data) >= 4:
        return struct.unpack("<I", data[:4])[0]

    return None


def main():
    with SOURCE.open(encoding="utf-8") as handle:
        report = json.load(handle)

    entries = report.get("valid_entries", [])
    entries = sorted(
        entries,
        key=lambda item: (
            item["page_index"],
            item["entry_index"],
        ),
    )

    results = []
    consumed = set()

    for index, entry in enumerate(entries):
        identity = (
            entry["page_index"],
            entry["entry_index"],
        )

        if identity in consumed:
            continue

        value = decode_scalar(entry)

        if value is not None:
            results.append({
                "page_index": entry["page_index"],
                "entry_index": entry["entry_index"],
                "key": entry["key"],
                "kind": "scalar",
                "value": value,
            })
            consumed.add(identity)
            continue

        span = entry.get("span", 1)

        if span <= 1:
            results.append({
                "page_index": entry["page_index"],
                "entry_index": entry["entry_index"],
                "key": entry["key"],
                "kind": "binary",
                "span": span,
                "data_hex": entry.get("data_hex"),
            })
            consumed.add(identity)
            continue

        chunks = []
        current_page = entry["page_index"]
        current_entry = entry["entry_index"]

        for candidate in entries[index:]:
            if candidate["page_index"] != current_page:
                continue

            candidate_index = candidate["entry_index"]

            if candidate_index < current_entry:
                continue

            if candidate_index >= current_entry + span:
                break

            if candidate["key"] != entry["key"]:
                continue

            raw = bytes.fromhex(candidate.get("data_hex", ""))
            chunks.append(raw)

        combined = b"".join(chunks)

        result = {
            "page_index": current_page,
            "entry_index": current_entry,
            "key": entry["key"],
            "kind": "multislot",
            "span": span,
            "data_hex": combined.hex(),
            "length": len(combined),
        }

        try:
            text = combined.decode("utf-8").rstrip("\x00\xff")
            if text and printable(text.encode("utf-8")):
                result["text"] = text
        except UnicodeDecodeError:
            pass

        results.append(result)

        for offset in range(span):
            consumed.add((current_page, current_entry + offset))

    output = {
        "source": str(SOURCE),
        "summary": {
            "values": len(results),
            "scalar_values": sum(
                1 for item in results
                if item["kind"] == "scalar"
            ),
            "multislot_values": sum(
                1 for item in results
                if item["kind"] == "multislot"
            ),
        },
        "values": results,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2, ensure_ascii=False)

    print(json.dumps(output["summary"], indent=2))
    print(f"[OK] Rapport écrit : {OUTPUT}")


if __name__ == "__main__":
    main()
