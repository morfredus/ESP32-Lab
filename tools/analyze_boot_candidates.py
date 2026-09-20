#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Analyse les candidats JSON de type boot"
    )

    parser.add_argument("input_file", type=Path)

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(
            "data/analysis/boot_candidates_report.json"
        ),
    )

    args = parser.parse_args()

    source = json.loads(
        args.input_file.read_text(encoding="utf-8")
    )

    boots = [
        entry
        for entry in source.get("entries", [])
        if entry.get("category") in (
            "bootlog_summary",
            "bootlog_complete",
        )
    ]

    boots.sort(
        key=lambda item: (
            item.get("bootCount") is None,
            item.get("bootCount") or 0,
            item.get("offset") or 0,
        )
    )

    report = {
        "source_file": source.get("source_file"),
        "boot_count": len(boots),
        "entries": boots,
        "limitations": [
            "Analyse basée sur les candidats JSON extraits",
            "Les entrées peuvent provenir de versions historiques",
            "Les numéros de boot ne prouvent pas à eux seuls une continuité complète",
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
    print("[INFO] Boots analysés :", len(boots))

    print()
    print("=== RÉSUMÉ DES BOOTS ===")

    for boot in boots:
        print(
            f'boot={boot.get("bootCount", "?"):>3} | '
            f'{boot.get("category", "?"):18s} | '
            f'reset={boot.get("resetReason", "?")} | '
            f'temp={boot.get("temperature", "?")} | '
            f'offset={boot.get("offset", "?")}'
        )


if __name__ == "__main__":
    main()
