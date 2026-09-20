"""
Tests du parseur d'identification ESP32.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.esp32_identification import parse_identification


SAMPLE_OUTPUT = """
Chip type:          ESP32-S3 (QFN56) (revision v0.2)
Features:           Wi-Fi, BT 5 (LE), Dual Core + LP Core, 240MHz, Embedded PSRAM 8MB (AP_3v3)
Crystal frequency:  40MHz
MAC:                80:b5:4e:d9:63:4c

Flash Memory Information:
=========================
Manufacturer: 68
Device: 4018
Detected flash size: 16MB
Flash type set in eFuse: quad (4 data lines)
Flash voltage set by eFuse: 3.3V
"""


def test_parse_identification():
    info = parse_identification(SAMPLE_OUTPUT)

    assert info["chip"] == "ESP32-S3 (QFN56)"
    assert info["revision"] == "v0.2"
    assert info["cpu_frequency_mhz"] == 240
    assert info["psram"] == "Embedded PSRAM 8MB"
    assert info["psram_size_mb"] == 8
    assert info["crystal_frequency_mhz"] == 40
    assert info["mac"] == "80:b5:4e:d9:63:4c"
    assert info["flash_size_mb"] == 16
    assert info["flash_type"] == "quad (4 data lines)"
    assert info["flash_voltage"] == "3.3V"


if __name__ == "__main__":
    test_parse_identification()
    print("Tous les tests sont réussis.")
