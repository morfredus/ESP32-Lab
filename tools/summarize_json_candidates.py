#!/usr/bin/env python3

import argparse
import json
from collections import Counter
from pathlib import Path


def classify(data):
    if not isinstance(data, dict):
        return "other"

    keys = set(data.keys())

    if "items" in keys and "nextId" in keys:
        return "inventory_collection"

    if {"kind", "name", "reference"}.issubset(keys):
        return "component"

    if {"bootMs", "resetReason", "bootCount"}.issubset(keys):
        if "lines" in keys and data.get("lines"):
            return "bootlog_complete"
        return "bootlog_summary"

    if {"uptime", "freeHeap", "largestBlock"}.issubset(keys):
        return "statistics"

    if {"id", "name", "parentId"}.issubset(keys):
        return "location"

    return "other"


def main():
    parser = argparse.ArgumentParser(
        description="Classe les candidats JSON extraits d'une image"
    )

    parser.add_argument(
        "input_file",
        type=Path,
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(
            "data/analysis/json_candidates_summary.json"
        ),
    )

    args = parser.parse_args()

    data = json.loads(args.input_file.read_text(encoding="utf-8"))

    candidates = data.get("candidates", [])

    groups = {}
    counter = Counter()

    for candidate in candidates:
        category = classify(candidate.get("data", {}))

        counter[category] += 1
        groups.setdefault(category, []).append({
            "offset": candidate.get("offset"),
            "end_offset": candidate.get("end_offset"),
            "size_bytes": candidate.get("size_bytes"),
            "data": candidate.get("data"),
        })

    result = {
        "source_file": data.get("source_file"),
        "source_size_bytes": data.get("source_size_bytes"),
        "candidate_count": len(candidates),
        "categories": dict(counter),
        "groups": groups,
        "limitations": [
            "Classification basée sur les clés JSON présentes",
            "Un candidat peut être un objet interne d'un fichier plus grand",
            "Les catégories ne représentent pas nécessairement les fichiers LittleFS",
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

    print("[OK] Résumé écrit dans :", args.output)
    print()
    print("Répartition :")

    for category, count in sorted(counter.items()):
        print(f"  {category:24s} : {count}")


if __name__ == "__main__":
    main()
