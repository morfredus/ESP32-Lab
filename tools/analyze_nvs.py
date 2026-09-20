#!/usr/bin/env python3

import json
from pathlib import Path


INPUT = Path("data/analysis/raw/nvs_s3.bin")
OUTPUT = Path("data/analysis/reports/nvs_s3_analysis.json")

PAGE_SIZE = 4096


def analyze_page(data, offset):
    page = data[offset:offset + PAGE_SIZE]

    ff_count = page.count(0xFF)
    zero_count = page.count(0x00)

    return {
        "offset": f"0x{offset:05X}",
        "size_bytes": len(page),
        "ff_bytes": ff_count,
        "zero_bytes": zero_count,
        "non_ff_bytes": len(page) - ff_count,
        "is_blank": ff_count == len(page),
        "first_32_bytes": page[:32].hex(" "),
    }


def main():
    if not INPUT.exists():
        raise SystemExit(f"Fichier absent : {INPUT}")

    data = INPUT.read_bytes()

    pages = []

    for offset in range(0, len(data), PAGE_SIZE):
        pages.append(analyze_page(data, offset))

    report = {
        "file": str(INPUT),
        "size_bytes": len(data),
        "page_size_bytes": PAGE_SIZE,
        "page_count": len(pages),
        "pages": pages,
        "limitations": [
            "Cette analyse ne décode pas les entrées NVS.",
            "La présence d'octets non vierges ne prouve pas "
            "qu'une donnée utilisateur est exploitable.",
            "Les valeurs NVS ne sont pas extraites dans cette étape.",
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
