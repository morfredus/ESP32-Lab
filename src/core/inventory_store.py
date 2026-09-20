"""
Lecture des inventaires ESP32 sauvegardés.
"""

import json
from pathlib import Path


INVENTORY_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "last_inventory.json"
)


def load_last_inventory():
    """Charge le dernier inventaire enregistré."""

    if not INVENTORY_FILE.exists():
        raise FileNotFoundError(
            f"Inventaire introuvable : {INVENTORY_FILE}"
        )

    with INVENTORY_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


if __name__ == "__main__":

    inventory = load_last_inventory()

    print(json.dumps(
        inventory,
        indent=4,
        ensure_ascii=False,
    ))
