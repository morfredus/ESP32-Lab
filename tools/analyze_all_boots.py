#!/usr/bin/env python3

import argparse
import json
from collections import Counter
from pathlib import Path


def get_boot_count(entry):
    data = entry.get("data", {})
    return data.get("bootCount")


def get_reset_reason(entry):
    data = entry.get("data", {})
    return data.get("resetReason")


def get_temperature(entry):
    data = entry.get("data", {})
    return data.get("temperature")


def get_boot_time(entry):
    data = entry.get("data", {})
    return data.get("bootMs")


def analyze(source):
    groups = source.get("groups", {})

    summaries = groups.get("bootlog_summary", [])
    complete_logs = groups.get("bootlog_complete", [])

    all_entries = []

    for entry in summaries:
        data = entry.get("data", {})

        all_entries.append({
            "source_type": "summary",
            "source_offset": entry.get("offset"),
            "boot_count": data.get("bootCount"),
            "reset_reason": data.get("resetReason"),
            "temperature_c": data.get("temperature"),
            "boot_ms": data.get("bootMs"),
            "crash_count": data.get("crashCount"),
        })

    for entry in complete_logs:
        data = entry.get("data", {})

        all_entries.append({
            "source_type": "complete",
            "source_offset": entry.get("offset"),
            "boot_count": data.get("bootCount"),
            "reset_reason": data.get("resetReason"),
            "temperature_c": data.get("temperature"),
            "boot_ms": data.get("bootMs"),
            "crash_count": data.get("crashCount"),
        })

    # Un seul enregistrement par numéro de boot.
    # En cas de doublon, le journal complet est privilégié.
    by_boot = {}

    for entry in all_entries:
        boot_count = entry.get("boot_count")

        if boot_count is None:
            continue

        existing = by_boot.get(boot_count)

        if existing is None:
            by_boot[boot_count] = entry
            continue

        if (
            entry["source_type"] == "complete"
            and existing["source_type"] != "complete"
        ):
            by_boot[boot_count] = entry

    ordered_boots = [
        by_boot[boot]
        for boot in sorted(by_boot)
    ]

    boot_numbers = sorted(by_boot)

    missing_boots = []

    if boot_numbers:
        expected_range = range(
            min(boot_numbers),
            max(boot_numbers) + 1,
        )

        missing_boots = [
            boot
            for boot in expected_range
            if boot not in by_boot
        ]

    reset_counter = Counter(
        entry.get("reset_reason") or "Inconnu"
        for entry in ordered_boots
    )

    complete_count = sum(
        1
        for entry in ordered_boots
        if entry["source_type"] == "complete"
    )

    summary_count = sum(
        1
        for entry in ordered_boots
        if entry["source_type"] == "summary"
    )

    temperatures = [
        entry["temperature_c"]
        for entry in ordered_boots
        if isinstance(entry.get("temperature_c"), (int, float))
    ]

    boot_times = [
        entry["boot_ms"]
        for entry in ordered_boots
        if isinstance(entry.get("boot_ms"), (int, float))
    ]

    crash_counts = [
        entry["crash_count"]
        for entry in ordered_boots
        if isinstance(entry.get("crash_count"), (int, float))
    ]

    result = {
        "source": {
            "summary_entries": len(summaries),
            "complete_entries": len(complete_logs),
            "total_entries": len(all_entries),
        },

        "deduplication": {
            "unique_boots": len(ordered_boots),
            "duplicate_boot_numbers_removed": (
                len(all_entries) - len(ordered_boots)
            ),
            "complete_logs_preferred": True,
        },

        "boot_range": {
            "first_known_boot": min(boot_numbers)
            if boot_numbers else None,
            "last_known_boot": max(boot_numbers)
            if boot_numbers else None,
            "missing_boot_numbers": missing_boots,
        },

        "source_distribution": {
            "summary": summary_count,
            "complete": complete_count,
        },

        "reset_reasons": dict(reset_counter),

        "temperature": {
            "count": len(temperatures),
            "minimum_c": min(temperatures)
            if temperatures else None,
            "maximum_c": max(temperatures)
            if temperatures else None,
            "average_c": round(
                sum(temperatures) / len(temperatures),
                2,
            )
            if temperatures else None,
        },

        "boot_time": {
            "count": len(boot_times),
            "minimum_ms": min(boot_times)
            if boot_times else None,
            "maximum_ms": max(boot_times)
            if boot_times else None,
            "average_ms": round(
                sum(boot_times) / len(boot_times),
                2,
            )
            if boot_times else None,
        },

        "crash_count": {
            "count": len(crash_counts),
            "maximum": max(crash_counts)
            if crash_counts else None,
            "non_zero_entries": sum(
                1
                for count in crash_counts
                if count != 0
            ),
        },

        "boots": ordered_boots,

        "limitations": [
            "Les journaux résumés ne contiennent pas nécessairement "
            "toutes les informations des journaux complets.",
            "Les numéros de boot manquants ne sont pas reconstruits.",
            "La présence d'un numéro de boot ne garantit pas "
            "la conservation de son journal complet.",
            "L'ordre des entrées dans la Flash n'est pas considéré "
            "comme une chronologie fiable.",
            "Les statistiques sont calculées uniquement sur les "
            "valeurs réellement présentes.",
            "Les raisons de reset ne permettent pas à elles seules "
            "de déterminer la cause matérielle.",
        ],
    }

    return result


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Analyse tous les journaux de boot ESP32 "
            "résumés et complets"
        )
    )

    parser.add_argument(
        "input_file",
        type=Path,
        help="Fichier json_candidates_summary.json",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(
            "data/analysis/all_boots_report.json"
        ),
        help="Fichier JSON de sortie",
    )

    args = parser.parse_args()

    if not args.input_file.exists():
        raise SystemExit(
            f"[ERREUR] Fichier introuvable : {args.input_file}"
        )

    try:
        source = json.loads(
            args.input_file.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as error:
        raise SystemExit(
            f"[ERREUR] JSON invalide : {error}"
        )

    result = analyze(source)

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.output.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        "[OK] Entrées résumées :",
        result["source"]["summary_entries"],
    )

    print(
        "[OK] Entrées complètes :",
        result["source"]["complete_entries"],
    )

    print(
        "[OK] Boots uniques :",
        result["deduplication"]["unique_boots"],
    )

    print(
        "[OK] Première valeur boot :",
        result["boot_range"]["first_known_boot"],
    )

    print(
        "[OK] Dernière valeur boot :",
        result["boot_range"]["last_known_boot"],
    )

    print(
        "[OK] Boots manquants :",
        result["boot_range"]["missing_boot_numbers"],
    )

    print(
        "[OK] Raisons de reset :",
        result["reset_reasons"],
    )

    print(
        "[OK] Température :",
        result["temperature"],
    )

    print(
        "[OK] Temps de démarrage :",
        result["boot_time"],
    )

    print(
        "[OK] Rapport écrit :",
        args.output,
    )


if __name__ == "__main__":
    main()
