#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Crée un index compact des candidats JSON"
    )

    parser.add_argument("input_file", type=Path)

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(
            "data/analysis/json_candidates_index.json"
        ),
    )

    args = parser.parse_args()

    source = json.loads(
        args.input_file.read_text(encoding="utf-8")
    )

    index = []

    for category, entries in source.get("groups", {}).items():
        for entry in entries:
            data = entry.get("data", {})

            item = {
                "category": category,
                "offset": entry.get("offset"),
                "end_offset": entry.get("end_offset"),
                "size_bytes": entry.get("size_bytes"),
                "keys": list(data.keys())
                if isinstance(data, dict)
                else [],
            }

            if category == "bootlog_summary":
                item["bootCount"] = data.get("bootCount")
                item["resetReason"] = data.get("resetReason")
                item["temperature"] = data.get("temperature")

            elif category == "bootlog_complete":
                item["bootCount"] = data.get("bootCount")
                item["resetReason"] = data.get("resetReason")
                item["wifiIp"] = data.get("wifiIp")
                item["wifiRssi"] = data.get("wifiRssi")

            elif category == "component":
                item["id"] = data.get("id")
                item["name"] = data.get("name")
                item["reference"] = data.get("reference")
                item["quantity"] = data.get("quantity")
                item["locationId"] = data.get("locationId")

            elif category == "location":
                item["id"] = data.get("id")
                item["name"] = data.get("name")
                item["parentId"] = data.get("parentId")

            index.append(item)

    index.sort(
        key=lambda item: (
            item.get("offset") is None,
            item.get("offset") or 0,
        )
    )

    result = {
        "source_file": source.get("source_file"),
        "source_size_bytes": source.get("source_size_bytes"),
        "candidate_count": source.get("candidate_count"),
        "index_count": len(index),
        "entries": index,
        "limitations": [
            "Index basé sur les candidats JSON déjà extraits",
            "Les offsets sont relatifs à l'image de partition",
            "Les candidats ne correspondent pas nécessairement à des fichiers",
            "Les données peuvent être des versions historiques ou des doublons",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)

    args.output.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("[OK] Index écrit dans :", args.output)
    print("[INFO] Entrées indexées :", len(index))


if __name__ == "__main__":
    main()
