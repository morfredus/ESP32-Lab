"""
Tests de l'analyse SFDP / identifiant unique de la puce Flash.

Les valeurs brutes proviennent d'une lecture réelle (ESP32-S3, Flash Boya
W25Q128).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.esp32_flash_sfdp import build_flash_report, parse_bfpt


# Capture réelle (sortie du script lecteur).
RAW = {
    "jedec": 1589352,  # 0x184068 : fabricant 0x68, type 0x40, capacité 0x18
    "unique_bytes": [0x50, 0x44, 0x73, 0x53, 0x58, 0x78, 0xB2, 0x0C],
    "header": [0x50444653, 0xFF010100],
    "param_headers": [[0x09010000, 0xFF000030], [0x03010068, 0xFF000060]],
    "bfpt_pointer": 48,
    "bfpt_length": 9,
    "bfpt": [
        0xFFF120E5, 0x07FFFFFF, 0x6B08EB44, 0xBB423B08, 0xFFFFFFEE,
        0xFF00FFFF, 0xFF00FFFF, 0x520F200C, 0xFF00D810,
    ],
}


def test_jedec_byte_order():
    report = build_flash_report(RAW)
    assert report["jedec"]["manufacturer_id"] == "68"
    assert report["jedec"]["device_id"] == "4018"
    assert report["jedec"]["raw"] == "0x684018"
    assert "W25Q128" in report["jedec"]["device_name"]
    assert "Boya" in report["jedec"]["manufacturer_name"]


def test_unique_id():
    report = build_flash_report(RAW)
    assert report["unique_id"]["hex"] == "50 44 73 53 58 78 B2 0C"
    assert report["unique_id"]["value"] == "0x504473535878B20C"


def test_sfdp_header():
    report = build_flash_report(RAW)
    sfdp = report["sfdp"]
    assert sfdp["signature_valid"] is True
    assert sfdp["revision"] == "1.0"
    assert sfdp["num_param_headers"] == 2


def test_bfpt_capacity_and_erase():
    flash = parse_bfpt(RAW["bfpt"])
    assert flash["capacity_bytes"] == 16 * 1024 * 1024
    assert flash["capacity_label"] == "16 Mio"
    assert flash["address_bytes"] == "3 octets"
    assert flash["erase_4kb"] is True
    assert flash["erase_4kb_opcode"] == "0x20"

    sizes = [erase["size"] for erase in flash["erase_types"]]
    assert sizes == [4096, 32768, 65536]


def test_bfpt_fast_read_modes():
    flash = parse_bfpt(RAW["bfpt"])
    fast = flash["fast_read"]
    assert fast["1-1-2"] is True
    assert fast["1-2-2"] is True
    assert fast["1-1-4"] is True
    assert fast["1-4-4"] is True
    assert fast["dtr"] is False


if __name__ == "__main__":
    test_jedec_byte_order()
    test_unique_id()
    test_sfdp_header()
    test_bfpt_capacity_and_erase()
    test_bfpt_fast_read_modes()
    print("Tous les tests SFDP sont réussis.")
