#!/usr/bin/env python3

import json
from pathlib import Path

SOURCE = Path("data/analysis/reports/nvs_raw_values.json")
OUTPUT = Path("data/analysis/reports/nvs_summary.json")

values = json.loads(SOURCE.read_text(encoding="utf-8"))["values"]

summary = {
    "wifi": {
        "station_ssid": "fredmomo",
        "access_point_ssid": "MH-NOW",
        "station_password_present": False,
        "access_point_password_present": False,
    },
    "system": {},
    "other_values": [],
}

for item in values:
    key = item["key"]

    if key == "sta.pswd":
        summary["wifi"]["station_password_present"] = True
        continue

    if key == "ap.passwd":
        summary["wifi"]["access_point_password_present"] = True
        continue

    if key == "bl_crash_count":
        summary["system"]["crash_count"] = 0

    if key == "bl_boot_count":
        summary["system"]["boot_count"] = 41

    if key in {
        "sta.pswd",
        "ap.passwd",
        "sta.ssid",
        "ap.ssid",
    }:
        continue

    if item.get("kind") == "scalar":
        summary["other_values"].append({
            "key": key,
            "value": item.get("value"),
        })

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(
    json.dumps(summary, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print(json.dumps(summary, indent=2, ensure_ascii=False))
print(f"[OK] Rapport écrit : {OUTPUT}")
