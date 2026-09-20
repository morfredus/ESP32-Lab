#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


def percentile_threshold(values, factor=1.5):
    """
    Calcule un seuil simple basé sur la moyenne et l'écart
    entre les valeurs minimale et maximale.

    Ce seuil est indicatif et ne constitue pas un diagnostic.
    """
    if not values:
        return None

    minimum = min(values)
    maximum = max(values)

    return minimum + ((maximum - minimum) * factor / 2)


def analyze(source):
    boots = source.get("boots", [])

    report = {
        "boot_count": len(boots),
        "long_boots": [],
        "hot_boots": [],
        "crash_boots": [],
        "unknown_reset_boots": [],
        "missing_values": [],
        "limitations": [
            "Les seuils sont indicatifs et ne constituent pas "
            "un diagnostic matériel.",
            "Les températures proviennent des données rapportées "
            "par le firmware.",
            "Les raisons de reset ne prouvent pas la cause réelle "
            "du redémarrage.",
            "Les journaux disponibles ne couvrent pas nécessairement "
            "tous les événements.",
        ],
    }

    boot_times = [
        boot.get("boot_ms")
        for boot in boots
        if isinstance(boot.get("boot_ms"), (int, float))
    ]

    temperatures = [
        boot.get("temperature_c")
        for boot in boots
        if isinstance(boot.get("temperature_c"), (int, float))
    ]

    if boot_times:
        average_boot_time = sum(boot_times) / len(boot_times)
        long_boot_threshold = average_boot_time * 1.5
    else:
        average_boot_time = None
        long_boot_threshold = None

    if temperatures:
        hot_temperature_threshold = 42.0
    else:
        hot_temperature_threshold = None

    for boot in boots:
        boot_count = boot.get("boot_count")
        boot_time = boot.get("boot_ms")
        temperature = boot.get("temperature_c")
        crash_count = boot.get("crash_count")
        reset_reason = boot.get("reset_reason")

        if (
            long_boot_threshold is not None
            and isinstance(boot_time, (int, float))
            and boot_time > long_boot_threshold
        ):
            report["long_boots"].append({
                "boot_count": boot_count,
                "boot_ms": boot_time,
                "threshold_ms": round(
                    long_boot_threshold,
                    2,
                ),
            })

        if (
            hot_temperature_threshold is not None
            and isinstance(temperature, (int, float))
            and temperature >= hot_temperature_threshold
        ):
            report["hot_boots"].append({
                "boot_count": boot_count,
                "temperature_c": temperature,
                "threshold_c": hot_temperature_threshold,
            })

        if (
            isinstance(crash_count, (int, float))
            and crash_count > 0
        ):
            report["crash_boots"].append({
                "boot_count": boot_count,
                "crash_count": crash_count,
            })

        if reset_reason in (None, "Inconnue", "Inconnue (0)"):
            report["unknown_reset_boots"].append({
                "boot_count": boot_count,
                "reset_reason": reset_reason,
            })

        missing = []

        for field in (
            "boot_count",
            "reset_reason",
            "temperature_c",
            "boot_ms",
            "crash_count",
        ):
            if boot.get(field) is None:
                missing.append(field)

        if missing:
            report["missing_values"].append({
                "boot_count": boot_count,
                "fields": missing,
            })

    report["thresholds"] = {
        "average_boot_time_ms": round(
            average_boot_time,
            2,
        ) if average_boot_time is not None else None,
        "long_boot_factor": 1.5,
        "long_boot_threshold_ms": round(
            long_boot_threshold,
            2,
        ) if long_boot_threshold is not None else None,
        "hot_temperature_threshold_c": hot_temperature_threshold,
    }

    report["summary"] = {
        "long_boot_count": len(report["long_boots"]),
        "hot_boot_count": len(report["hot_boots"]),
        "crash_boot_count": len(report["crash_boots"]),
        "unknown_reset_count": len(
            report["unknown_reset_boots"]
        ),
        "boots_with_missing_values": len(
            report["missing_values"]
        ),
    }

    return report


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Recherche les valeurs atypiques dans les boots ESP32"
        )
    )

    parser.add_argument(
        "input_file",
        type=Path,
        help="Rapport all_boots_report.json",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(
            "data/analysis/boot_outliers_report.json"
        ),
        help="Rapport JSON de sortie",
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
        "[OK] Boots analysés :",
        result["boot_count"],
    )

    print(
        "[OK] Démarrages longs :",
        result["summary"]["long_boot_count"],
    )

    print(
        "[OK] Boots chauds :",
        result["summary"]["hot_boot_count"],
    )

    print(
        "[OK] Boots avec crash :",
        result["summary"]["crash_boot_count"],
    )

    print(
        "[OK] Resets inconnus :",
        result["summary"]["unknown_reset_count"],
    )

    print(
        "[OK] Boots avec valeurs manquantes :",
        result["summary"]["boots_with_missing_values"],
    )

    print(
        "[OK] Rapport écrit :",
        args.output,
    )

    for boot in result["long_boots"]:
        print(
            "[BOOT LONG]",
            f"boot={boot['boot_count']}",
            f"durée={boot['boot_ms']} ms",
        )

    for boot in result["hot_boots"]:
        print(
            "[TEMPÉRATURE ÉLEVÉE]",
            f"boot={boot['boot_count']}",
            f"température={boot['temperature_c']} °C",
        )

    for boot in result["crash_boots"]:
        print(
            "[CRASH]",
            f"boot={boot['boot_count']}",
            f"crashCount={boot['crash_count']}",
        )

    for boot in result["unknown_reset_boots"]:
        print(
            "[RESET INCONNU]",
            f"boot={boot['boot_count']}",
            f"raison={boot['reset_reason']}",
        )


if __name__ == "__main__":
    main()
