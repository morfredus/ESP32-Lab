"""
Création d'une fiche d'inventaire ESP32.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from core import flash_catalog
from core.esp32_identification import (
    identify_esp32,
    parse_identification,
)


def enrich_identification(information):
    """Ajoute les libellés lisibles du catalogue Flash à l'identification."""

    manufacturer = flash_catalog.describe_manufacturer(
        information.get("flash_manufacturer")
    )
    device = flash_catalog.describe_device(
        information.get("flash_device")
    )

    information["flash_manufacturer_name"] = manufacturer
    information["flash_device_name"] = device

    return information


def create_inventory(port="/dev/ttyACM0"):
    """Identifie l'ESP32 et construit sa fiche d'inventaire."""

    result = identify_esp32(port)

    if result["return_code"] != 0:
        raise RuntimeError(
            f"Échec de l'identification : {result['stderr'].strip()}"
        )

    information = enrich_identification(
        parse_identification(result["stdout"])
    )

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "port": port,
        "identification": information,
    }


def save_inventory(inventory):
    """Sauvegarde l'inventaire dans un fichier JSON."""

    output_directory = Path(__file__).resolve().parents[2] / "data"
    output_directory.mkdir(exist_ok=True)

    output_file = output_directory / "last_inventory.json"

    output_file.write_text(
        json.dumps(inventory, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )

    return output_file


if __name__ == "__main__":

    inventory = create_inventory()
    output_file = save_inventory(inventory)

    print(json.dumps(inventory, indent=4, ensure_ascii=False))
    print(f"\nInventaire sauvegardé dans : {output_file}")
