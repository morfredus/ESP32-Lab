#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Extrait les événements des journaux de boot complets"
    )

    parser.add_argument("input_file", type=Path)

    args = parser.parse_args()

    source = json.loads(
        args.input_file.read_text(encoding="utf-8")
    )

    entries = source.get("groups", {}).get(
        "bootlog_complete", []
    )

    print("=== ÉVÉNEMENTS DES JOURNAUX COMPLETS ===")

    for index, entry in enumerate(entries, 1):
        data = entry.get("data", {})

        print()
        print(
            f"--- Journal {index} | "
            f"boot={data.get('bootCount')} | "
            f"offset={entry.get('offset')} ---"
        )

        print(
            "Température :",
            data.get("temperature"),
            "| bootMs :",
            data.get("bootMs"),
            "| uptimeAtResetMs :",
            data.get("uptimeAtResetMs"),
        )

        for raw_line in data.get("lines", []):
            try:
                line = json.loads(raw_line)
            except (TypeError, json.JSONDecodeError):
                print("[WARN] Ligne non décodable :", raw_line)
                continue

            tag = line.get("tag")
            message = line.get("msg", "")

            if tag in (
                "BootLog",
                "Storage",
                "WiFi",
                "Inventory",
                "App",
            ):
                print(
                    f'[{line.get("t", "?"):>5}] '
                    f'{tag:10s} | {message}'
                )


if __name__ == "__main__":
    main()
