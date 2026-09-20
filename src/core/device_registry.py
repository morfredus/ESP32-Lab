"""
Registre des cartes ESP32.

Conservé pour compatibilité : délègue désormais à la base SQLite
(``core.database``). Les signatures publiques restent inchangées.
"""

from core import database


def get_device(mac):
    """Retourne les informations associées à une adresse MAC."""

    return database.get_device(mac)


def get_devices():
    """Retourne toutes les cartes enregistrées (dict indexé par MAC)."""

    return database.get_devices()


def update_device(mac, name="", note="", location=""):
    """Crée ou met à jour les informations personnalisées d'une carte."""

    return database.update_device(
        mac=mac, name=name, note=note, location=location
    )


def update_device_from_inventory(inventory):
    """Actualise les informations techniques d'une carte."""

    return database.update_device_from_inventory(inventory)


if __name__ == "__main__":
    import json

    database.init_db()
    print(json.dumps(get_devices(), indent=4, ensure_ascii=False))
