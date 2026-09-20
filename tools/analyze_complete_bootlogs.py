#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Analyse les journaux de boot complets"
    )

    parser.add_argument("input_file", type=Path)

    args = parser.parse_args()

    source = json.loads(
        args.input_file.read_text(encoding="utf-8")
    )

    entries = source.get("groups", {}).get(
        "bootlog_complete", []
    )

    print("=== JOURNAUX COMPLETS ===")
    print("Nombre :", len(entries))

    for index, entry in enumerate(entries, 1):
        data = entry.get("data", {})

        print()
        print(f"--- Journal {index} ---")
        print("Offset :", entry.get("offset"))
        print("Taille :", entry.get("size_bytes"))
        print("Clés :", ", ".join(data.keys()))

        for key in (
            "bootCount",
            "resetReason",
            "uptimeAtReset",
            "freeHeapAtReset",
            "largestBlockAtReset",
            "wifiStatus",
            "wifiRssi",
            "wifiIp",
            "lastStats",
        ):
            if key in data:
                print(f"{key} :", data[key])

        print("Nombre de lignes :", len(
            data.get("lines", [])
        ))

        print()
        print("Données complètes :")
        print(json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ))


if __name__ == "__main__":
    main()
