"""
Lecture du dernier inventaire ESP32.

Conservé pour compatibilité : délègue à la base SQLite (``core.database``).
"""

from core import database


def load_last_inventory():
    """
    Charge le dernier inventaire enregistré, ou ``None`` si aucun.
    """

    return database.get_last_inventory()


if __name__ == "__main__":
    import json

    database.init_db()
    print(json.dumps(load_last_inventory(), indent=4, ensure_ascii=False))
