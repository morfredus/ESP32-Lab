#!/usr/bin/env python3

import json
from pathlib import Path

INPUT = Path("data/analysis/reports/nvs_scalar_values.json")
OUTPUT = Path("data/analysis/reports/nvs_readable_report.json")


def decode(item):
    key = item["key"]
    value = item["value_hex"].split()
    first = int(value[0], 16)

    decoded = {
        "raw_hex": item["value_hex"],
        "value": None,
        "interpretation": "raw",
    }

    if key == "WIFI_STA_DEF" and len(value) >= 4:
        decoded["value"] = ".".join(str(int(x, 16)) for x in value[:4])
        decoded["interpretation"] = "IPv4 candidate"

    elif key in ("ap.chan", "sta.chan", "ap.sndchan"):
        decoded["value"] = first
        decoded["interpretation"] = "Wi-Fi channel"

    elif key == "bcn.interval":
        decoded["value"] = int.from_bytes(bytes.fromhex(item["value_hex"][:5]), "little")
        decoded["interpretation"] = "Beacon interval candidate"

    elif key == "cal_version":
        decoded["value"] = int.from_bytes(bytes.fromhex(item["value_hex"][:11]), "little")
        decoded["interpretation"] = "Calibration version candidate"

    elif key in ("opmode", "dhcp_state"):
        decoded["value"] = first
        decoded["interpretation"] = "Raw enum"

    else:
        decoded["value"] = first
        decoded["interpretation"] = "Raw integer candidate"

    return decoded


def main():
    items = json.loads(INPUT.read_text(encoding="utf-8"))

    report = {
        "source": str(INPUT),
        "entries": [],
        "limitations": [
            "Les valeurs sont extraites du dump NVS.",
            "Les enums Wi-Fi et les structures internes ne sont pas tous décodés.",
            "Les interprétations candidates ne remplacent pas la documentation ESP-IDF."
        ]
    }

    for item in items:
        report["entries"].append({
            **{
                key: item[key]
                for key in ("page", "entry", "namespace", "type", "key")
            },
            **decode(item),
        })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"[OK] {len(report['entries'])} entrées analysées")
    print(f"[OK] Rapport : {OUTPUT}")


if __name__ == "__main__":
    main()
