"""
Registre persistant des cartes ESP32 identifiées par leur adresse MAC.
"""

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_FILE = PROJECT_ROOT / "data" / "device_registry.json"


TECHNICAL_FIELDS = (
    "chip",
    "revision",
    "features",
    "cpu_frequency_mhz",
    "psram",
    "psram_size_mb",
    "crystal_frequency_mhz",
    "flash_manufacturer",
    "flash_device",
    "flash_size_mb",
    "flash_type",
    "flash_voltage",
    "port",
)


def load_registry():
    """Charge le registre des cartes."""

    if not REGISTRY_FILE.exists():
        return {}

    with REGISTRY_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_registry(registry):
    """Sauvegarde le registre."""

    REGISTRY_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with REGISTRY_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            registry,
            file,
            indent=4,
            ensure_ascii=False,
        )


def get_device(mac):
    """Retourne les informations associées à une adresse MAC."""

    if not mac:
        return None

    registry = load_registry()
    return registry.get(mac.lower())


def update_device(mac, name="", note="", location=""):
    """Crée ou met à jour les informations personnalisées d'une carte."""

    if not mac:
        raise ValueError("L'adresse MAC est obligatoire.")

    mac = mac.lower()
    registry = load_registry()

    current = registry.get(mac, {})

    updated_device = dict(current)

    updated_device.update({
        "mac": mac,
        "name": name.strip(),
        "note": note.strip(),
        "location": location.strip(),
    })

    registry[mac] = updated_device

    save_registry(registry)

    return registry[mac]


def update_device_from_inventory(inventory):
    """Actualise les informations techniques d'une carte."""

    identification = inventory.get("identification", {})
    mac = identification.get("mac")

    if not mac:
        return None

    mac = mac.lower()
    registry = load_registry()
    current = registry.get(mac, {})

    updated_device = dict(current)

    updated_device.update({
        "mac": mac,
        "name": current.get("name", ""),
        "note": current.get("note", ""),
        "location": current.get("location", ""),
        "last_seen": inventory.get("timestamp"),
        "port": inventory.get("port"),
    })

    for field in TECHNICAL_FIELDS:
        if field in identification:
            updated_device[field] = identification.get(field)

    registry[mac] = updated_device

    save_registry(registry)

    return registry[mac]


def get_devices():
    """Retourne toutes les cartes enregistrées."""

    return load_registry()


if __name__ == "__main__":
    print(json.dumps(
        get_devices(),
        indent=4,
        ensure_ascii=False,
    ))
