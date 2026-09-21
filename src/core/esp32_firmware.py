"""
Identite du firmware present et etat OTA d'un ESP32 (lecture seule).

Deux informations extraites de la Flash, sans jamais ecrire sur la carte :

- **Identite de chaque application** via la structure ``esp_app_desc_t``, placee
  a l'offset ``0x20`` du debut de chaque partition applicative (apres
  ``esp_image_header`` + ``esp_image_segment_header``), magic ``0xABCD5432`` :
  nom du projet, version, version ESP-IDF, date et heure de compilation, compteur
  anti-rollback (``secure_version``), sha256 de l'ELF.
- **Etat OTA** via la partition ``otadata`` : deux entrees de 32 octets
  (``esp_ota_select_entry_t``) dont on deduit le slot **selectionne au demarrage**.

Note d'honnetete : ``otadata`` indique le slot que le bootloader choisira au
prochain demarrage, pas necessairement le firmware **en cours d'execution** (non
deductible sans interroger la carte en fonctionnement).
"""

import struct
import subprocess
import tempfile
import zlib
from pathlib import Path

from core.esp32_partitions import read_partition_table
from core.esptool_runner import run_esptool


APP_DESC_OFFSET = 0x20
APP_DESC_MAGIC = 0xABCD5432
APP_DESC_SIZE = 176            # jusqu'a la fin de app_elf_sha256

OTA_ENTRY_SIZE = 32
OTA_SECTOR = 0x1000           # la 2e entree otadata est un secteur plus loin
OTADATA_READ_SIZE = 0x2000    # deux secteurs

OTA_STATES = {
    0x00000000: "NEW",
    0x00000001: "PENDING_VERIFY",
    0x00000002: "VALID",
    0x00000003: "INVALID",
    0x00000004: "ABORTED",
    0xFFFFFFFF: "UNDEFINED",
}


def _string(raw, offset, length):
    """Chaine ASCII coupee au premier NUL."""

    chunk = raw[offset:offset + length]
    return chunk.split(b"\x00", 1)[0].decode("ascii", errors="replace")


def parse_app_desc(raw):
    """
    Decode un ``esp_app_desc_t``. ``raw`` commence au debut de la structure.

    Retourne ``{"magic_ok": False}`` si le magic est absent (slot vide ou image
    chiffree), sinon les champs d'identite.
    """

    if len(raw) < APP_DESC_SIZE:
        return {"magic_ok": False}

    magic = struct.unpack_from("<I", raw, 0)[0]
    if magic != APP_DESC_MAGIC:
        return {"magic_ok": False}

    return {
        "magic_ok": True,
        "secure_version": struct.unpack_from("<I", raw, 4)[0],
        "version": _string(raw, 16, 32),
        "project_name": _string(raw, 48, 32),
        "time": _string(raw, 80, 16),
        "date": _string(raw, 96, 16),
        "idf_ver": _string(raw, 112, 32),
        "elf_sha256": raw[144:176].hex(),
    }


def _ota_crc(ota_seq):
    """CRC otadata (formule ESP-IDF : crc32 du seq, init 0xFFFFFFFF)."""

    return zlib.crc32(struct.pack("<I", ota_seq), 0xFFFFFFFF) & 0xFFFFFFFF


def parse_ota_entry(raw):
    """Decode une entree ``esp_ota_select_entry_t`` (32 octets)."""

    if len(raw) < OTA_ENTRY_SIZE:
        return None

    ota_seq = struct.unpack_from("<I", raw, 0)[0]
    # seq_label est souvent non initialise (0xFF) : on ne garde que l'ASCII
    # imprimable pour eviter du charabia dans la charge JSON.
    seq_label = "".join(
        chr(byte) for byte in raw[4:24] if 32 <= byte < 127
    )
    ota_state = struct.unpack_from("<I", raw, 24)[0]
    crc = struct.unpack_from("<I", raw, 28)[0]

    # Une entree vierge (0xFFFFFFFF) n'a pas de CRC valide : ce n'est pas une erreur.
    blank = ota_seq == 0xFFFFFFFF

    return {
        "ota_seq": ota_seq,
        "seq_label": seq_label,
        "ota_state": ota_state,
        "ota_state_name": OTA_STATES.get(ota_state, f"0x{ota_state:08x}"),
        "crc": crc,
        "crc_ok": (not blank) and _ota_crc(ota_seq) == crc,
        "blank": blank,
    }


def select_boot_slot(entries, ota_count):
    """
    Reproduit la selection du bootloader : le plus grand ``ota_seq`` valide
    pointe le slot ``ota_(seq-1) % ota_count``. Sans entree valide, la carte
    demarre sur ``factory``.

    Retourne ``(index_ota, label)`` ; ``index_ota`` vaut ``None`` pour factory.
    """

    best = 0
    for entry in entries:
        if not entry or entry["blank"] or not entry["crc_ok"]:
            continue
        if entry["ota_seq"] > best:
            best = entry["ota_seq"]

    if best == 0 or not ota_count:
        return None, "factory"

    index = (best - 1) % ota_count
    return index, f"ota_{index}"


def _read_flash(port, chip, offset, size, timeout=60):
    """Lit une zone Flash (lecture seule) et renvoie ses octets, ou None."""

    with tempfile.TemporaryDirectory() as directory:
        dump_path = Path(directory) / "flash.bin"

        arguments = ["--port", port]
        if chip:
            arguments += ["--chip", chip]
        arguments += ["read-flash", hex(offset), hex(size), str(dump_path)]

        try:
            result = run_esptool(arguments, timeout=timeout)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

        if result.returncode != 0 or not dump_path.exists():
            return None

        return dump_path.read_bytes()


def read_firmware(port, chip=None):
    """
    Lit l'identite firmware de chaque application et l'etat OTA (lecture seule).

    Retourne ``{"status": "ok", ...}`` ou ``{"status": "error", "message": ...}``.
    """

    table = read_partition_table(port, chip=chip)
    if table.get("status") != "ok":
        return table

    partitions = table.get("partitions", [])
    app_parts = [p for p in partitions if p.get("type") == "app"]
    ota_parts = [p for p in app_parts if p.get("subtype", "").startswith("ota_")]
    otadata = next(
        (p for p in partitions
         if p.get("type") == "data" and p.get("subtype") == "ota"),
        None,
    )

    apps = []
    for part in app_parts:
        raw = _read_flash(
            port, chip, part["offset"], APP_DESC_OFFSET + APP_DESC_SIZE)

        entry = {
            "label": part.get("label"),
            "subtype": part.get("subtype"),
            "offset": part.get("offset"),
            "size": part.get("size"),
            "encrypted": part.get("encrypted", False),
            "app_desc": None,
            "empty": True,
        }

        if raw is not None and len(raw) >= APP_DESC_OFFSET + APP_DESC_SIZE:
            desc = parse_app_desc(raw[APP_DESC_OFFSET:])
            if desc.get("magic_ok"):
                entry["app_desc"] = desc
                entry["empty"] = False

        apps.append(entry)

    ota = {"present": False}
    if otadata:
        raw = _read_flash(
            port, chip, otadata["offset"],
            min(otadata["size"], OTADATA_READ_SIZE))
        if raw is not None and len(raw) >= OTA_SECTOR + OTA_ENTRY_SIZE:
            entries = [
                parse_ota_entry(raw[0:OTA_ENTRY_SIZE]),
                parse_ota_entry(raw[OTA_SECTOR:OTA_SECTOR + OTA_ENTRY_SIZE]),
            ]
            _, boot_label = select_boot_slot(entries, len(ota_parts))
            ota = {
                "present": True,
                "entries": entries,
                "ota_count": len(ota_parts),
                "boot_label": boot_label,
            }

    if not apps:
        return {
            "status": "error",
            "message": "Aucune partition applicative dans la table.",
        }

    return {
        "status": "ok",
        "source": "device",
        "apps": apps,
        "ota": ota,
    }
