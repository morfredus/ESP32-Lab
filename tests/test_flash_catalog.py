"""
Tests du catalogue Flash (identifiants JEDEC).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core import flash_catalog


def test_known_manufacturer():
    assert flash_catalog.manufacturer_name("68") == "Boya (BoHong)"
    assert flash_catalog.describe_manufacturer("68") == "Boya (BoHong) (ID 68)"


def test_unknown_manufacturer():
    assert flash_catalog.manufacturer_name("AA") is None
    assert flash_catalog.describe_manufacturer("AA") == "Inconnu (ID AA)"


def test_known_device():
    assert "W25Q128" in flash_catalog.describe_device("4018")


def test_capacity_from_device():
    assert flash_catalog.capacity_mb_from_device("4018") == 16
    assert flash_catalog.capacity_mb_from_device("4016") == 4
    assert flash_catalog.capacity_mb_from_device("4014") == 1


def test_normalization():
    assert flash_catalog.normalize_flash_id("0x68") == "68"
    assert flash_catalog.normalize_flash_id(" 68 ") == "68"
    assert flash_catalog.describe_manufacturer(None) is None


if __name__ == "__main__":
    test_known_manufacturer()
    test_unknown_manufacturer()
    test_known_device()
    test_capacity_from_device()
    test_normalization()
    print("Tous les tests du catalogue Flash sont réussis.")
