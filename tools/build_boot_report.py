#!/usr/bin/env python3

import argparse
import json
import re
from pathlib import Path


WIFI_PATTERN = re.compile(
    r'Connecté à "([^"]+)"\s+— IP ([0-9.]+)'
    r'\s+— RSSI (-?[0-9]+) dBm'
)

STORAGE_PATTERN = re.compile(
    r'LittleFS prêt — ([0-9]+)\/([0-9]+) octets utilisés'
)

INVENTORY_PATTERN = re.compile(
    r'Démarré — ([0-9]+) composant\(s\), ([0-9]+) emplacement\(s\)'
)

RESET_PATTERN = re.compile(
    r'Raison du dernier reset : (.+?) — boot #([0-9]+), '
    r'crash #([0-9]+), ([0-9.]+) °C'
)


def parse_wifi(raw_line):
    match = WIFI_PATTERN.search(raw_line)

    if not match:
        return None

    return {
        "ssid": match.group(1),
        "ip": match.group(2),
        "rssi_dbm": int(match.group(3)),
    }


def parse_storage(message):
    match = STORAGE_PATTERN.search(message)

    if not match:
        return None

    return {
        "used_bytes": int(match.group(1)),
        "total_bytes": int(match.group(2)),
    }


def parse_inventory(message):
    match = INVENTORY_PATTERN.search(message)

    if not match:
        return None

    return {
        "components": int(match.group(1)),
        "locations": int(match.group(2)),
    }


def parse_reset(message):
    match = RESET_PATTERN.search(message)

    if not match:
        return None

    return {
        "reset_reason": match.group(1),
        "previous_boot_count": int(match.group(2)),
        "previous_crash_count": int(match.group(3)),
        "temperature_c": float(match.group(4)),
    }


def analyze_entry(entry):
    data = entry.get("data", {})

    report = {
        "source_offset": entry.get("offset"),
        "source_size": entry.get("size"),
        "boot_count": data.get("bootCount"),
        "reset_reason": data.get("resetReason"),
        "temperature_c": data.get("temperature"),
        "boot_ms": data.get("bootMs"),
        "uptime_at_reset_ms": data.get("uptimeAtResetMs"),
        "wifi": {},
        "filesystem": None,
        "inventory": None,
        "modules": [],
        "services": [],
        "invalid_lines": 0,
        "recovered_lines": 0,
        "raw_line_count": len(data.get("lines", [])),
    }

    for raw_line in data.get("lines", []):
        try:
            line = json.loads(raw_line)
            message = line.get("msg", "")
            tag = line.get("tag", "")

            reset = parse_reset(message)
            if reset:
                report.update(reset)

            storage = parse_storage(message)
            if storage:
                report["filesystem"] = storage

            inventory = parse_inventory(message)
            if inventory:
                report["inventory"] = inventory

            if tag == "App" and "modules actifs" in message:
                report["modules"].append(message)

            if tag in ("mDNS", "OTA", "Time", "Web"):
                report["services"].append(message)

        except json.JSONDecodeError:
            report["invalid_lines"] += 1

            wifi = parse_wifi(raw_line)

            if wifi:
                report["wifi"] = wifi
                report["recovered_lines"] += 1

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Construit un rapport JSON normalisé des boots ESP32"
    )

    parser.add_argument("input_file", type=Path)
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("data/analysis/boot_report.json"),
    )

    args = parser.parse_args()

    source = json.loads(
        args.input_file.read_text(encoding="utf-8")
    )

    entries = source.get("groups", {}).get(
        "bootlog_complete", []
    )

    reports = [
        analyze_entry(entry)
        for entry in entries
    ]

    output = {
        "source_file": str(args.input_file),
        "journal_count": len(reports),
        "journals": reports,
        "limitations": [
            "Les lignes Wi-Fi malformées sont récupérées par expression régulière.",
            "Les valeurs absentes ne sont pas déduites.",
            "Les données proviennent de journaux applicatifs extraits de la Flash.",
            "Ce rapport ne prouve pas la cause matérielle des resets.",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)

    args.output.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"[OK] Journaux analysés : {len(reports)}")
    print(f"[OK] Rapport écrit : {args.output}")

    for index, report in enumerate(reports, 1):
        print()
        print(
            f"Journal {index} | "
            f"boot={report.get('boot_count')} | "
            f"reset={report.get('reset_reason')} | "
            f"invalides={report.get('invalid_lines')} | "
            f"récupérées={report.get('recovered_lines')}"
        )

        print("  Wi-Fi :", report.get("wifi") or "non disponible")
        print("  Flash :", report.get("filesystem") or "non disponible")
        print("  Inventaire :", report.get("inventory") or "non disponible")


if __name__ == "__main__":
    main()
