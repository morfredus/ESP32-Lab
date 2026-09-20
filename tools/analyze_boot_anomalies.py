#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


def difference(first, second):
    """Retourne la différence entre deux valeurs numériques."""
    if first is None or second is None:
        return None

    return second - first


def analyze(journals):
    """
    Analyse les différences entre les journaux de boot.

    Les journaux sont triés par numéro de boot.
    Ce tri ne garantit pas leur ordre chronologique réel.
    """

    anomalies = []
    comparisons = []

    # Tri par numéro de boot, indépendamment de l'ordre
    # dans lequel les candidats ont été extraits de la Flash.
    ordered_journals = sorted(
        journals,
        key=lambda journal: (
            journal.get("boot_count") is None,
            journal.get("boot_count") or 0,
        ),
    )

    for index in range(1, len(ordered_journals)):
        previous = ordered_journals[index - 1]
        current = ordered_journals[index]

        previous_wifi = previous.get("wifi") or {}
        current_wifi = current.get("wifi") or {}

        previous_filesystem = previous.get("filesystem") or {}
        current_filesystem = current.get("filesystem") or {}

        previous_inventory = previous.get("inventory") or {}
        current_inventory = current.get("inventory") or {}

        comparison = {
            "from_boot": previous.get("boot_count"),
            "to_boot": current.get("boot_count"),

            "temperature_delta_c": difference(
                previous.get("temperature_c"),
                current.get("temperature_c"),
            ),

            "boot_time_delta_ms": difference(
                previous.get("boot_ms"),
                current.get("boot_ms"),
            ),

            # Non comparable sans chronologie réelle fiable.
            "uptime_at_reset_delta_ms": None,

            "rssi_delta_dbm": difference(
                previous_wifi.get("rssi_dbm"),
                current_wifi.get("rssi_dbm"),
            ),

            "filesystem_used_delta_bytes": difference(
                previous_filesystem.get("used_bytes"),
                current_filesystem.get("used_bytes"),
            ),

            "inventory_components_delta": difference(
                previous_inventory.get("components"),
                current_inventory.get("components"),
            ),

            "inventory_locations_delta": difference(
                previous_inventory.get("locations"),
                current_inventory.get("locations"),
            ),

            "reset_reason_changed": (
                previous.get("reset_reason")
                != current.get("reset_reason")
            ),

            "inventory_changed": (
                previous.get("inventory")
                != current.get("inventory")
            ),
        }

        comparisons.append(comparison)

        # ---------------------------------------------------------
        # Changement de raison de reset
        # ---------------------------------------------------------

        if comparison["reset_reason_changed"]:
            anomalies.append({
                "type": "reset_reason_change",
                "from_boot": previous.get("boot_count"),
                "to_boot": current.get("boot_count"),
                "details": {
                    "previous": previous.get("reset_reason"),
                    "current": current.get("reset_reason"),
                },
            })

        # ---------------------------------------------------------
        # Changement de contenu de l'inventaire
        # ---------------------------------------------------------

        if comparison["inventory_changed"]:
            anomalies.append({
                "type": "inventory_change",
                "from_boot": previous.get("boot_count"),
                "to_boot": current.get("boot_count"),
                "details": {
                    "previous": previous.get("inventory"),
                    "current": current.get("inventory"),
                },
            })

        # ---------------------------------------------------------
        # Variation de température importante
        # ---------------------------------------------------------

        temperature_delta = comparison["temperature_delta_c"]

        if temperature_delta is not None:
            if abs(temperature_delta) >= 5:
                anomalies.append({
                    "type": "temperature_variation",
                    "from_boot": previous.get("boot_count"),
                    "to_boot": current.get("boot_count"),
                    "delta_c": temperature_delta,
                })

        # ---------------------------------------------------------
        # Variation importante du signal Wi-Fi
        # ---------------------------------------------------------

        rssi_delta = comparison["rssi_delta_dbm"]

        if rssi_delta is not None:
            if abs(rssi_delta) >= 10:
                anomalies.append({
                    "type": "wifi_signal_variation",
                    "from_boot": previous.get("boot_count"),
                    "to_boot": current.get("boot_count"),
                    "delta_dbm": rssi_delta,
                })

        # ---------------------------------------------------------
        # Variation de l'espace LittleFS utilisé
        # ---------------------------------------------------------

        filesystem_delta = (
            comparison["filesystem_used_delta_bytes"]
        )

        if filesystem_delta is not None:
            if filesystem_delta != 0:
                anomalies.append({
                    "type": "filesystem_usage_change",
                    "from_boot": previous.get("boot_count"),
                    "to_boot": current.get("boot_count"),
                    "delta_bytes": filesystem_delta,
                })

    return {
        "journal_count": len(ordered_journals),

        "ordering": {
            "method": "boot_count_ascending",
            "chronology_guaranteed": False,
            "description": (
                "Les journaux sont triés par numéro de boot. "
                "L'ordre chronologique réel n'est pas garanti."
            ),
        },

        "comparisons": comparisons,

        "anomalies": anomalies,

        "limitations": [
            "Les journaux complets disponibles sont peu nombreux.",
            "Les différences ne prouvent pas une causalité matérielle.",
            "L'ordre chronologique réel n'est pas garanti.",
            "Les valeurs absentes ne sont pas déduites.",
            "Les variations de température et de RSSI sont descriptives.",
            "Les uptime_at_reset ne sont pas comparés.",
            "Les changements LittleFS peuvent refléter des écritures normales.",
            "Le changement d'inventaire ne prouve pas une perte de données.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Analyse les différences entre journaux de boot ESP32"
        )
    )

    parser.add_argument(
        "input_file",
        type=Path,
        help="Rapport JSON des boots normalisés",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(
            "data/analysis/boot_anomalies_report.json"
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

    journals = source.get("journals", [])

    if not isinstance(journals, list):
        raise SystemExit(
            "[ERREUR] Le champ 'journals' doit être une liste."
        )

    result = analyze(journals)

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
        f"[OK] Journaux analysés : "
        f"{result['journal_count']}"
    )

    print(
        f"[OK] Comparaisons : "
        f"{len(result['comparisons'])}"
    )

    print(
        f"[OK] Anomalies détectées : "
        f"{len(result['anomalies'])}"
    )

    print(
        f"[OK] Rapport écrit : "
        f"{args.output}"
    )

    for anomaly in result["anomalies"]:
        print()

        print(
            f"[ANOMALIE] {anomaly['type']} | "
            f"boot {anomaly.get('from_boot')} -> "
            f"{anomaly.get('to_boot')}"
        )

        details = anomaly.get(
            "details",
            anomaly,
        )

        print(" ", details)


if __name__ == "__main__":
    main()
