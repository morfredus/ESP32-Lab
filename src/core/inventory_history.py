"""
Historique des inventaires ESP32.

Conservé pour compatibilité : délègue à la base SQLite (``core.database``).
"""

from core import database


def save_history(inventory):
    """Ajoute un inventaire à l'historique (base SQLite)."""

    identification = inventory.get("identification", {})
    mac = identification.get("mac")

    if not mac:
        return None

    return database.save_reading(
        mac,
        "inventory",
        inventory,
        port=inventory.get("port"),
        recorded_at=inventory.get("timestamp"),
    )


def get_history():
    """Retourne l'historique des inventaires (liste {recorded_at, inventory})."""

    return database.get_inventory_history()


if __name__ == "__main__":
    import json

    database.init_db()
    print(json.dumps(get_history(), indent=4, ensure_ascii=False))
