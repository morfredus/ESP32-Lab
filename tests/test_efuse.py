"""
Tests de l'analyse des eFuses.

Utilise une capture réelle de ``espefuse summary --format json`` (ESP32-S3)
comme fixture.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.esp32_efuse import (
    build_efuse_report,
    build_security_posture,
    derive_mac_addresses,
    parse_efuse_summary,
)


FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "efuse_summary_s3.txt"
)


def _load_report():
    raw = FIXTURE.read_text(encoding="utf-8")
    return build_efuse_report(parse_efuse_summary(raw))


def test_parse_and_count():
    report = _load_report()
    assert report["status"] == "ok"
    assert report["count"] == 112


def test_identity():
    identity = _load_report()["identity"]
    assert identity["revision"] == "v0.2"
    assert identity["psram_cap"] == "8M"
    # Identifiant unique 128 bits présent et non nul.
    assert identity["optional_unique_id"]
    assert identity["optional_unique_id"].startswith("96 ce 7f 3d")


def test_security_posture():
    security = _load_report()["security"]
    assert security["secure_boot"] is False
    assert security["flash_encryption"] is False
    assert security["flash_encryption_state"] == "Disable"
    assert security["keys_used"] == []


def test_derived_macs():
    macs = derive_mac_addresses("80:b5:4e:d9:63:4c (OK)")
    assert macs["wifi_sta"] == "80:b5:4e:d9:63:4c"
    assert macs["wifi_ap"] == "80:b5:4e:d9:63:4d"
    assert macs["bluetooth"] == "80:b5:4e:d9:63:4e"
    assert macs["ethernet"] == "80:b5:4e:d9:63:4f"


def test_derived_macs_carry():
    # Report sur l'octet suivant lorsque le dernier vaut 0xFF.
    macs = derive_mac_addresses("aa:bb:cc:dd:ee:ff")
    assert macs["wifi_ap"] == "aa:bb:cc:dd:ef:00"


def test_categories_grouping():
    categories = _load_report()["categories"]
    assert "identity" in categories
    assert "security" in categories
    # L'identité est listée avant la sécurité (ordre imposé).
    keys = list(categories.keys())
    assert keys.index("identity") < keys.index("security")


def test_security_posture_detects_keys():
    efuses = {
        "KEY_PURPOSE_0": {"value": "XTS_AES_128_KEY"},
        "SECURE_BOOT_EN": {"value": "True"},
        "SPI_BOOT_CRYPT_CNT": {"value": "Enable"},
    }
    posture = build_security_posture(efuses)
    assert posture["secure_boot"] is True
    assert posture["flash_encryption"] is True
    assert posture["keys_used"] == [{"slot": 0, "purpose": "XTS_AES_128_KEY"}]


if __name__ == "__main__":
    test_parse_and_count()
    test_identity()
    test_security_posture()
    test_derived_macs()
    test_derived_macs_carry()
    test_categories_grouping()
    test_security_posture_detects_keys()
    print("Tous les tests eFuse sont réussis.")
