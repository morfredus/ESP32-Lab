#!/usr/bin/env python3

import argparse
import json
from collections import Counter
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Analyse les composants retrouvés dans une image"
    )

    parser.add_argument("input_file", type=Path)

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(
            "data/analysis/inventory_candidates_report.json"
        ),
    )

    args = parser.parse_args()

    source = json.loads(
        args.input_file.read_text(encoding="utf-8")
    )

    components = [
        entry
        for entry in source.get("entries", [])
        if entry.get("category") == "component"
    ]

    locations = [
        entry
        for entry in source.get("entries", [])
        if entry.get("category") == "location"
    ]

    by_reference = Counter(
        item.get("reference")
        for item in components
        if item.get("reference")
    )

    by_location = Counter(
        str(item.get("locationId"))
        for item in components
        if item.get("locationId") is not None
    )

    total_quantity = sum(
        item.get("quantity", 0) or 0
        for item in components
    )

    duplicate_references = {
        reference: count
        for reference, count in by_reference.items()
        if count > 1
    }

    report = {
        "source_file": source.get("source_file"),
        "component_count": len(components),
        "location_count": len(locations),
        "total_quantity": total_quantity,
        "quantities_zero": [
            {
                "name": item.get("name"),
                "reference": item.get("reference"),
                "offset": item.get("offset"),
            }
            for item in components
            if (item.get("quantity") or 0) == 0
        ],
        "duplicate_references": duplicate_references,
        "components_by_location": dict(by_location),
        "components": sorted(
            components,
            key=lambda item: item.get("offset") or 0
        ),
        "limitations": [
            "Analyse basée sur les candidats JSON extraits",
            "Les candidats ne représentent pas nécessairement des fichiers",
            "Les quantités sont celles rapportées dans les structures retrouvées",
            "Les données peuvent provenir de versions historiques",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)

    args.output.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("[OK] Rapport écrit dans :", args.output)
    print()
    print("Composants :", len(components))
    print("Emplacements :", len(locations))
    print("Quantité totale :", total_quantity)
    print("Références dupliquées :", len(duplicate_references))
    print("Composants avec quantité zéro :", len(
        report["quantities_zero"]
    ))


if __name__ == "__main__":
    main()
