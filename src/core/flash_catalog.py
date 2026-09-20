"""
Catalogue de correspondance des puces Flash SPI (identifiants JEDEC).

Les valeurs proviennent des identifiants JEDEC standard renvoyés par la
commande ``flash-id`` d'esptool :

- l'octet fabricant (JEDEC ID, premier octet) ;
- les deux octets d'identifiant mémoire (type + capacité).

Le troisième octet de l'identifiant mémoire code la capacité :
``2 ^ octet`` octets (0x14 = 1 Mo, 0x15 = 2 Mo, ... 0x18 = 16 Mo).
"""


# Fabricants JEDEC les plus courants sur les modules ESP32.
FLASH_MANUFACTURERS = {
    "EF": "Winbond",
    "C8": "GigaDevice",
    "68": "Boya (BoHong)",
    "20": "XMC / Micron",
    "5E": "Zbit",
    "0B": "XTX",
    "85": "Puya",
    "1C": "EON",
    "C2": "Macronix",
    "9D": "ISSI",
    "A1": "Fudan (FM)",
    "51": "GigaDevice",
    "D8": "GigaDevice",
    "CD": "TH (Taiwan)",
}


# Références précises connues (identifiant mémoire complet, 2 octets).
FLASH_DEVICES = {
    "4014": "W25Q80 / équivalent (1 Mo)",
    "4015": "W25Q16 / équivalent (2 Mo)",
    "4016": "W25Q32 / équivalent (4 Mo)",
    "4017": "W25Q64 / équivalent (8 Mo)",
    "4018": "W25Q128 / BY25Q128 (16 Mo)",
    "4019": "W25Q256 / équivalent (32 Mo)",
    "7018": "GD25Q128 (16 Mo)",
}


def normalize_flash_id(value):
    """Normalise un identifiant Flash en hexadécimal majuscule sans préfixe."""

    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .upper()
        .replace("0X", "")
    )


def manufacturer_name(value):
    """Retourne le nom du fabricant Flash, ou None si inconnu."""

    identifier = normalize_flash_id(value)

    if not identifier:
        return None

    return FLASH_MANUFACTURERS.get(identifier)


def device_name(value):
    """Retourne la référence Flash connue, ou None si inconnue."""

    identifier = normalize_flash_id(value)

    if not identifier:
        return None

    return FLASH_DEVICES.get(identifier)


def capacity_mb_from_device(value):
    """Déduit la capacité (en Mo) à partir de l'octet de capacité JEDEC."""

    identifier = normalize_flash_id(value)

    if len(identifier) < 2:
        return None

    try:
        capacity_byte = int(identifier[-2:], 16)
    except ValueError:
        return None

    # Bornes réalistes pour de la Flash SPI (256 Ko à 256 Mo).
    if capacity_byte < 0x12 or capacity_byte > 0x1C:
        return None

    return (2 ** capacity_byte) // (1024 * 1024)


def describe_manufacturer(value):
    """Description lisible du fabricant, avec l'identifiant brut."""

    identifier = normalize_flash_id(value)

    if not identifier:
        return None

    name = manufacturer_name(identifier)

    if name:
        return f"{name} (ID {identifier})"

    return f"Inconnu (ID {identifier})"


def describe_device(value):
    """Description lisible de la référence Flash, avec l'identifiant brut."""

    identifier = normalize_flash_id(value)

    if not identifier:
        return None

    name = device_name(identifier)

    if name:
        return f"{name} (ID {identifier})"

    return f"Inconnu (ID {identifier})"
