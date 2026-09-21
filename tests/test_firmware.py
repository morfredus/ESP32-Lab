"""
Tests des parseurs firmware / OTA (sans materiel).

Verifie le decodage de ``esp_app_desc_t``, des entrees ``otadata`` et la regle
de selection du slot de boot.
"""

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.esp32_firmware import (
    APP_DESC_MAGIC,
    parse_app_desc,
    parse_ota_entry,
    select_boot_slot,
    _ota_crc,
)


def _app_desc(project="meteo", version="1.2.3", idf="v5.2.1",
              date="2026-09-21", secure=3):
    raw = bytearray(176)
    struct.pack_into("<I", raw, 0, APP_DESC_MAGIC)
    struct.pack_into("<I", raw, 4, secure)
    raw[16:16 + len(version)] = version.encode()
    raw[48:48 + len(project)] = project.encode()
    raw[80:80 + 8] = b"12:00:00"
    raw[96:96 + len(date)] = date.encode()
    raw[112:112 + len(idf)] = idf.encode()
    raw[144:176] = bytes(range(32))
    return bytes(raw)


def _ota_entry(seq, state=2):
    raw = bytearray(32)
    struct.pack_into("<I", raw, 0, seq)
    struct.pack_into("<I", raw, 24, state)
    struct.pack_into("<I", raw, 28, _ota_crc(seq))
    return bytes(raw)


BLANK = b"\xff" * 32


def test_parse_app_desc_champs():
    desc = parse_app_desc(_app_desc())
    assert desc["magic_ok"] is True
    assert desc["project_name"] == "meteo"
    assert desc["version"] == "1.2.3"
    assert desc["idf_ver"] == "v5.2.1"
    assert desc["date"] == "2026-09-21"
    assert desc["secure_version"] == 3
    assert desc["elf_sha256"] == bytes(range(32)).hex()


def test_parse_app_desc_sans_magic():
    assert parse_app_desc(bytes(176))["magic_ok"] is False
    assert parse_app_desc(b"\x00" * 10)["magic_ok"] is False


def test_parse_ota_entry_valide():
    entry = parse_ota_entry(_ota_entry(2, state=2))
    assert entry["ota_seq"] == 2
    assert entry["ota_state_name"] == "VALID"
    assert entry["crc_ok"] is True
    assert entry["blank"] is False


def test_parse_ota_entry_vierge():
    entry = parse_ota_entry(BLANK)
    assert entry["blank"] is True
    assert entry["crc_ok"] is False


def test_parse_ota_entry_crc_faux():
    raw = bytearray(_ota_entry(5))
    struct.pack_into("<I", raw, 28, 0x12345678)   # CRC casse
    assert parse_ota_entry(bytes(raw))["crc_ok"] is False


def test_select_boot_slot():
    blank = parse_ota_entry(BLANK)
    e1 = parse_ota_entry(_ota_entry(1))
    e2 = parse_ota_entry(_ota_entry(2))
    e3 = parse_ota_entry(_ota_entry(3))

    assert select_boot_slot([blank, blank], 2) == (None, "factory")
    assert select_boot_slot([e1, blank], 2) == (0, "ota_0")
    assert select_boot_slot([e1, e2], 2) == (1, "ota_1")
    # seq=3, 2 slots -> (3-1) % 2 = 0
    assert select_boot_slot([e3, blank], 2) == (0, "ota_0")


def test_select_boot_slot_ignore_crc_invalide():
    raw = bytearray(_ota_entry(2))
    struct.pack_into("<I", raw, 28, 0)   # CRC invalide -> entree ignoree
    bad = parse_ota_entry(bytes(raw))
    assert select_boot_slot([bad, parse_ota_entry(BLANK)], 2) == (None, "factory")
