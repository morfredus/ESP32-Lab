"""
Lecture et analyse de la table de partitions d'un ESP32.

La table de partitions est stockée en Flash à l'adresse 0x8000 (taille
maximale 0xC00 = 3072 octets, soit 95 entrées + une signature MD5).

Chaque entrée fait 32 octets (little-endian) :

    magic (2)  type (1)  subtype (1)  offset (4)  size (4)  label (16)  flags (4)

- magic entrée standard : 0xAA 0x50
- magic entrée MD5       : 0xEB 0xEB

La lecture se fait en mode **lecture seule** via ``esptool read-flash`` :
aucune écriture, aucune modification de la carte.
"""

import struct
import subprocess
import tempfile
from pathlib import Path

from core.esptool_runner import run_esptool


PARTITION_TABLE_OFFSET = 0x8000
PARTITION_TABLE_SIZE = 0x0C00
PARTITION_ENTRY_SIZE = 32

MAGIC_ENTRY = 0x50AA
MAGIC_MD5 = 0xEBEB


# Types principaux.
PARTITION_TYPES = {
    0x00: "app",
    0x01: "data",
}

# Sous-types d'application.
APP_SUBTYPES = {
    0x00: "factory",
    0x20: "test",
    **{0x10 + index: f"ota_{index}" for index in range(16)},
}

# Sous-types de données.
DATA_SUBTYPES = {
    0x00: "ota",
    0x01: "phy",
    0x02: "nvs",
    0x03: "coredump",
    0x04: "nvs_keys",
    0x05: "efuse_em",
    0x06: "undefined",
    0x80: "esphttpd",
    0x81: "fat",
    0x82: "spiffs",
    0x83: "littlefs",
}


def _type_name(type_id):
    """Nom lisible d'un type de partition."""

    return PARTITION_TYPES.get(type_id, f"0x{type_id:02x}")


def _subtype_name(type_id, subtype_id):
    """Nom lisible d'un sous-type de partition."""

    if type_id == 0x00:
        return APP_SUBTYPES.get(subtype_id, f"0x{subtype_id:02x}")

    if type_id == 0x01:
        return DATA_SUBTYPES.get(subtype_id, f"0x{subtype_id:02x}")

    return f"0x{subtype_id:02x}"


def parse_partition_table(raw_bytes):
    """
    Analyse les octets bruts de la table de partitions.

    Retourne la liste des partitions détectées, chacune décrite par un
    dictionnaire. La lecture s'arrête à la première entrée invalide
    (fin de table ou zone non initialisée).
    """

    partitions = []

    for offset in range(0, len(raw_bytes), PARTITION_ENTRY_SIZE):
        entry = raw_bytes[offset:offset + PARTITION_ENTRY_SIZE]

        if len(entry) < PARTITION_ENTRY_SIZE:
            break

        magic = struct.unpack("<H", entry[0:2])[0]

        # Entrée de signature MD5 : on ignore et on continue.
        if magic == MAGIC_MD5:
            continue

        # Toute autre valeur que le magic standard marque la fin utile.
        if magic != MAGIC_ENTRY:
            break

        type_id = entry[2]
        subtype_id = entry[3]
        part_offset = struct.unpack("<I", entry[4:8])[0]
        part_size = struct.unpack("<I", entry[8:12])[0]
        label = entry[12:28].split(b"\x00", 1)[0].decode(
            "ascii", errors="replace"
        )
        flags = struct.unpack("<I", entry[28:32])[0]

        # Une taille nulle signale une entrée non exploitable.
        if part_size == 0:
            continue

        partitions.append({
            "label": label,
            "type": _type_name(type_id),
            "type_id": type_id,
            "subtype": _subtype_name(type_id, subtype_id),
            "subtype_id": subtype_id,
            "offset": part_offset,
            "size": part_size,
            "end": part_offset + part_size,
            "encrypted": bool(flags & 0x1),
        })

    return partitions


def read_partition_table(port, chip=None, timeout=60):
    """
    Lit la table de partitions réelle de la carte (lecture seule).

    Retourne un dictionnaire ``{"status": "ok", "partitions": [...], ...}``
    ou ``{"status": "error", "message": ...}`` en cas d'échec.
    """

    with tempfile.TemporaryDirectory() as directory:
        dump_path = Path(directory) / "partition_table.bin"

        arguments = ["--port", port]

        if chip:
            arguments += ["--chip", chip]

        arguments += [
            "read-flash",
            hex(PARTITION_TABLE_OFFSET),
            hex(PARTITION_TABLE_SIZE),
            str(dump_path),
        ]

        try:
            result = run_esptool(arguments, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            return {
                "status": "error",
                "message": f"Délai dépassé lors de la lecture Flash : {error}",
            }
        except FileNotFoundError as error:
            return {
                "status": "error",
                "message": f"esptool introuvable : {error}",
            }

        if result.returncode != 0 or not dump_path.exists():
            return {
                "status": "error",
                "message": (
                    "Lecture de la table de partitions impossible : "
                    + (result.stderr.strip() or "erreur esptool")
                ),
            }

        raw_bytes = dump_path.read_bytes()

    partitions = parse_partition_table(raw_bytes)

    if not partitions:
        return {
            "status": "error",
            "message": "Aucune partition valide détectée à l'adresse 0x8000.",
        }

    return {
        "status": "ok",
        "source": "device",
        "table_offset": PARTITION_TABLE_OFFSET,
        "partitions": partitions,
    }
