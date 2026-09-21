#!/usr/bin/env python3
"""
Regenere reference/espressif/metadata.json a partir des fichiers de familles.

A lancer apres avoir cree ou modifie un fichier de famille dans
reference/espressif/ (voir reference/espressif/README.md pour savoir ou trouver
les donnees chez Espressif). Le script :

- recalcule le sha256 de chaque fichier de famille present ;
- valide que chaque fichier a le bon schema_version et les cles attendues ;
- met a jour la version du jeu (date du jour par defaut, ou --version) ;
- conserve les autres champs (source, source_urls, channel) ;
- reecrit metadata.json.

Usage :
    python tools/build_espressif_metadata.py
    python tools/build_espressif_metadata.py --version 2026.10.01
"""

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path


SUPPORTED_SCHEMA = 1
DATASET_DIR = Path(__file__).resolve().parents[1] / "reference" / "espressif"
METADATA_FILE = "metadata.json"

# Cles attendues dans un fichier de famille (garde-fou avant publication).
REQUIRED_KEYS = (
    "schema_version", "family", "label", "pins_present", "strapping",
    "input_only", "flash_psram", "flash_psram_octal", "usb_jtag",
    "adc1", "adc2", "dac", "notes",
)


def family_files():
    """Liste triee des fichiers de familles (tout .json sauf metadata)."""

    return sorted(
        path for path in DATASET_DIR.glob("*.json")
        if path.name != METADATA_FILE
    )


def validate(path):
    """Verifie un fichier de famille. Retourne la liste des problemes."""

    problems = []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"illisible ou JSON invalide : {error}"]

    if data.get("schema_version") != SUPPORTED_SCHEMA:
        problems.append(
            f"schema_version = {data.get('schema_version')} "
            f"(attendu {SUPPORTED_SCHEMA})"
        )

    for key in REQUIRED_KEYS:
        if key not in data:
            problems.append(f"cle manquante : {key}")

    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version",
        default=date.today().strftime("%Y.%m.%d"),
        help="Version du jeu (defaut : date du jour, ex. 2026.10.01).",
    )
    args = parser.parse_args()

    meta_path = DATASET_DIR / METADATA_FILE
    metadata = {}
    if meta_path.exists():
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))

    files = family_files()
    if not files:
        raise SystemExit(f"Aucun fichier de famille trouve dans {DATASET_DIR}.")

    # Validation avant ecriture : on refuse de publier un jeu incoherent.
    errors = False
    checksums = {}
    for path in files:
        stem = path.stem
        problems = validate(path)
        if problems:
            errors = True
            print(f"[ERREUR] {path.name} :")
            for problem in problems:
                print(f"         - {problem}")
            continue

        checksums[stem] = {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()
        }
        print(f"[OK]     {path.name}  sha256={checksums[stem]['sha256'][:12]}...")

    if errors:
        raise SystemExit(
            "\nCorrige les erreurs ci-dessus avant de regenerer le metadata."
        )

    # Champs par defaut si le metadata n'existait pas encore.
    metadata.setdefault("schema_version", SUPPORTED_SCHEMA)
    metadata.setdefault(
        "source",
        "Espressif datasheets (Boot Configurations) + ESP-IDF GPIO reference",
    )
    metadata.setdefault("source_urls", [])
    metadata.setdefault("channel", "curated (ESP32-Lab)")
    metadata.setdefault("synced_at", None)

    metadata["dataset_version"] = args.version
    metadata["files"] = checksums

    meta_path.write_text(
        json.dumps(metadata, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(
        f"\nmetadata.json regenere : version {args.version}, "
        f"{len(checksums)} famille(s)."
    )


if __name__ == "__main__":
    main()
