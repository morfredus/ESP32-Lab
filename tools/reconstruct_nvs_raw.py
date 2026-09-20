#!/usr/bin/env python3

import json
from pathlib import Path

RAW = Path("data/analysis/raw/nvs_s3.bin")
SOURCE = Path("data/analysis/reports/nvs_semantic_analysis.json")
OUTPUT = Path("data/analysis/reports/nvs_raw_values.json")

PAGE_SIZE = 4096
HEADER_SIZE = 0x40
ENTRY_SIZE = 32

TARGET_KEYS = {
    "sta.ssid",
    "sta.pswd",
    "ap.ssid",
    "ap.passwd",
}


def entry_offset(page_index, entry_index):
    return (
        page_index * PAGE_SIZE
        + HEADER_SIZE
        + entry_index * ENTRY_SIZE
    )


def reconstruct(raw, page_index, entry_index, span):
    offset = entry_offset(page_index, entry_index)
    first = raw[offset:offset + ENTRY_SIZE]

    if len(first) != ENTRY_SIZE:
        return None

    # Variable-length NVS data:
    # bytes 24-25 = length
    # bytes 26-27 = reserved
    # bytes 28-31 = first data bytes
    length = int.from_bytes(first[24:26], "little")

    data = bytearray(first[28:32])

    for slot in range(1, span):
        continuation_offset = offset + slot * ENTRY_SIZE
        continuation = raw[
            continuation_offset:continuation_offset + ENTRY_SIZE
        ]

        if len(continuation) != ENTRY_SIZE:
            return None

        data.extend(continuation[24:32])

    return bytes(data[:length])


def main():
    raw = RAW.read_bytes()
    report = json.loads(SOURCE.read_text(encoding="utf-8"))

    results = []

    for entry in report.get("valid_entries", []):
        key = entry.get("key")

        if key not in TARGET_KEYS:
            continue

        span = int(entry.get("span", 1))
        page_index = int(entry["page_index"])
        entry_index = int(entry["entry_index"])

        value = reconstruct(
            raw,
            page_index,
            entry_index,
            span,
        )

        result = {
            "page_index": page_index,
            "entry_index": entry_index,
            "key": key,
            "span": span,
            "length": len(value) if value is not None else None,
        }

        if value is None:
            result["error"] = "reconstruction_failed"
        else:
            result["data_hex"] = value.hex()

            try:
                text = value.rstrip(b"\x00").decode("utf-8")
                result["text"] = text
            except UnicodeDecodeError:
                result["text"] = None

        results.append(result)

    output = {
        "source": str(RAW),
        "values": results,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    for item in results:
        print(
            f"[page={item['page_index']} "
            f"entry={item['entry_index']}] "
            f"{item['key']} "
            f"span={item['span']} "
            f"length={item['length']} "
            f"text={item.get('text')!r}"
        )

    print(f"\n[OK] Rapport écrit : {OUTPUT}")


if __name__ == "__main__":
    main()
