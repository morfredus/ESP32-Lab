"""
Tests de l'analyseur de partition NVS.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.esp32_nvs import (
    ENTRY_SIZE,
    PAGE_SIZE,
    _esp_crc32,
    analyze_nvs_dump,
)


def _build_page():
    """Construit une page NVS « full » avec une entrée u8 écrite (clé misc)."""

    header = bytearray(32)
    header[0:4] = (0xFFFFFFFC).to_bytes(4, "little")  # état : full
    header[4:8] = (7).to_bytes(4, "little")           # séquence
    header[8] = 0xFF                                   # version
    header[9:28] = b"\xFF" * 19
    header_crc = _esp_crc32(0xFFFFFFFF, bytes(header[4:28]))
    header[28:32] = header_crc.to_bytes(4, "little")

    # Table d'état : entrée 0 « written » (0b10), les 3 suivantes « empty ».
    bitmap = bytearray(b"\xFF" * 32)
    bitmap[0] = 0b11111110

    entry = bytearray(32)
    entry[0] = 1              # namespace
    entry[1] = 0x01           # type u8
    entry[2] = 1              # span
    entry[3] = 0xFF           # chunk_index
    entry[8:24] = b"misc".ljust(16, b"\x00")
    entry[24:32] = bytes([0x2A]) + b"\xFF" * 7   # valeur 42
    entry_crc = _esp_crc32(
        _esp_crc32(0xFFFFFFFF, bytes(entry[0:4])), bytes(entry[8:32])
    )
    entry[4:8] = entry_crc.to_bytes(4, "little")

    padding = b"\xFF" * (PAGE_SIZE - 32 - 32 - ENTRY_SIZE)
    return bytes(header) + bytes(bitmap) + bytes(entry) + padding


def test_page_metadata():
    report = analyze_nvs_dump(_build_page())
    assert report["page_count"] == 1
    page = report["pages"][0]
    assert page["state_name"] == "full"
    assert page["sequence"] == 7
    assert page["header_crc_match"] is True
    assert page["entry_counts"]["written"] == 1


def test_written_entry_decoding():
    page = analyze_nvs_dump(_build_page())["pages"][0]
    written = [e for e in page["entries"] if e["state"]["name"] == "written"]
    assert len(written) == 1

    decoded = written[0]["decoded"]
    assert decoded["key"] == "misc"
    assert decoded["type_name"] == "u8"
    assert decoded["span"] == 1
    assert decoded["crc_match"] is True
    assert decoded["data_hex"].startswith("2a")


def test_empty_page():
    report = analyze_nvs_dump(b"\xFF" * PAGE_SIZE)
    page = report["pages"][0]
    assert page["state_name"] == "empty_or_uninitialized"
    assert page["header_crc_match"] is None
    assert page["entry_counts"]["written"] == 0


def test_i32_type_recognized():
    # 0x14 doit être reconnu comme i32 (le rapport historique le disait inconnu).
    header = bytearray(b"\xFF" * 32)
    header[0:4] = (0xFFFFFFFC).to_bytes(4, "little")
    header[4:8] = (1).to_bytes(4, "little")
    header[28:32] = _esp_crc32(
        0xFFFFFFFF, bytes(header[4:28])
    ).to_bytes(4, "little")
    bitmap = bytearray(b"\xFF" * 32)
    bitmap[0] = 0b11111110
    entry = bytearray(b"\xFF" * 32)
    entry[0] = 1
    entry[1] = 0x14
    entry[2] = 1
    entry[3] = 0xFF
    entry[8:24] = b"bl_boot_count".ljust(16, b"\x00")
    entry[24:32] = (41).to_bytes(4, "little") + b"\xFF" * 4
    entry[4:8] = _esp_crc32(
        _esp_crc32(0xFFFFFFFF, bytes(entry[0:4])), bytes(entry[8:32])
    ).to_bytes(4, "little")
    page = bytes(header) + bytes(bitmap) + bytes(entry) + b"\xFF" * (PAGE_SIZE - 96)

    decoded = analyze_nvs_dump(page)["pages"][0]["entries"][0]["decoded"]
    assert decoded["type_name"] == "i32"
    assert decoded["key"] == "bl_boot_count"


if __name__ == "__main__":
    test_page_metadata()
    test_written_entry_decoding()
    test_empty_page()
    test_i32_type_recognized()
    print("Tous les tests NVS sont réussis.")
