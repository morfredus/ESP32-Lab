"""
Tests du parseur de table de partitions ESP32.
"""

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.esp32_partitions import (
    MAGIC_ENTRY,
    MAGIC_MD5,
    parse_partition_table,
)


def _entry(magic, type_id, subtype_id, offset, size, label):
    return (
        struct.pack("<H", magic)
        + bytes([type_id, subtype_id])
        + struct.pack("<I", offset)
        + struct.pack("<I", size)
        + label.encode("ascii").ljust(16, b"\x00")
        + struct.pack("<I", 0)
    )


def _sample_table():
    raw = b""
    raw += _entry(MAGIC_ENTRY, 0x01, 0x02, 0x9000, 0x5000, "nvs")
    raw += _entry(MAGIC_ENTRY, 0x01, 0x00, 0xE000, 0x2000, "otadata")
    raw += _entry(MAGIC_ENTRY, 0x00, 0x10, 0x10000, 0x640000, "app0")
    raw += _entry(MAGIC_ENTRY, 0x00, 0x11, 0x650000, 0x640000, "app1")
    raw += _entry(MAGIC_ENTRY, 0x01, 0x82, 0xC90000, 0x360000, "spiffs")
    raw += _entry(MAGIC_MD5, 0, 0, 0, 0, "")   # signature MD5 ignorée
    raw += b"\xff" * 32                         # zone non initialisée = fin
    return raw


def test_parse_partition_table_counts():
    partitions = parse_partition_table(_sample_table())
    assert len(partitions) == 5


def test_parse_partition_table_fields():
    partitions = parse_partition_table(_sample_table())

    nvs = partitions[0]
    assert nvs["label"] == "nvs"
    assert nvs["type"] == "data"
    assert nvs["subtype"] == "nvs"
    assert nvs["offset"] == 0x9000
    assert nvs["size"] == 0x5000
    assert nvs["end"] == 0xE000
    assert nvs["encrypted"] is False

    app0 = partitions[2]
    assert app0["type"] == "app"
    assert app0["subtype"] == "ota_0"


def test_parse_partition_table_stops_on_terminator():
    # Un octet 0xFF juste après une entrée valide marque la fin.
    raw = _entry(MAGIC_ENTRY, 0x01, 0x02, 0x9000, 0x5000, "nvs")
    raw += b"\xff" * 32
    raw += _entry(MAGIC_ENTRY, 0x00, 0x00, 0x10000, 0x100000, "ignored")

    partitions = parse_partition_table(raw)
    assert len(partitions) == 1
    assert partitions[0]["label"] == "nvs"


def test_encrypted_flag():
    raw = (
        struct.pack("<H", MAGIC_ENTRY)
        + bytes([0x00, 0x00])
        + struct.pack("<I", 0x10000)
        + struct.pack("<I", 0x100000)
        + b"factory".ljust(16, b"\x00")
        + struct.pack("<I", 0x1)   # flag « encrypted »
    )

    partitions = parse_partition_table(raw)
    assert partitions[0]["encrypted"] is True


if __name__ == "__main__":
    test_parse_partition_table_counts()
    test_parse_partition_table_fields()
    test_parse_partition_table_stops_on_terminator()
    test_encrypted_flag()
    print("Tous les tests de partitions sont réussis.")
