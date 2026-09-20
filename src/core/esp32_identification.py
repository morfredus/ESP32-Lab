"""
Identification et analyse d'un ESP32 via esptool.
"""

import json
import re
import subprocess


def identify_esp32(port="/dev/ttyACM0"):
    """Récupère les informations brutes via esptool."""

    command = [
        ".venv/bin/python",
        "-m",
        "esptool",
        "--port",
        port,
        "flash-id",
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    return {
        "port": port,
        "return_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def parse_identification(raw_output):
    """Extrait et convertit les informations utiles."""

    info = {
        "chip": None,
        "revision": None,
        "features": None,
        "cpu_frequency_mhz": None,
        "psram": None,
        "psram_size_mb": None,
        "crystal_frequency_mhz": None,
        "mac": None,
        "flash_manufacturer": None,
        "flash_device": None,
        "flash_size_mb": None,
        "flash_type": None,
        "flash_voltage": None,
    }

    patterns = {
        "chip": r"Chip type:\s+(.+?)\s+\(revision",
        "revision": r"revision\s+(v[\d.]+)",
        "features": r"Features:\s+(.+)",
        "cpu_frequency_mhz": r",\s*(\d+)MHz,",
        "psram": r"(Embedded PSRAM\s+\S+)",
        "psram_size_mb": r"Embedded PSRAM\s+(\d+)MB",
        "crystal_frequency_mhz": r"Crystal frequency:\s+(\d+)MHz",
        "mac": r"MAC:\s+([0-9a-f:]{17})",
        "flash_manufacturer": r"Manufacturer:\s+(\S+)",
        "flash_device": r"Device:\s+(\S+)",
        "flash_size_mb": r"Detected flash size:\s+(\d+)MB",
        "flash_type": r"Flash type set in eFuse:\s+(.+)",
        "flash_voltage": r"Flash voltage set by eFuse:\s+(.+)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, raw_output, re.IGNORECASE)

        if match:
            value = match.group(1).strip()

            if key in {
                "cpu_frequency_mhz",
                "psram_size_mb",
                "crystal_frequency_mhz",
                "flash_size_mb",
            }:
                value = int(value)

            info[key] = value

    return info

if __name__ == "__main__":

    result = identify_esp32()

    print(f"Code retour : {result['return_code']}")

    if result["return_code"] != 0:
        print(result["stderr"])
        raise SystemExit(result["return_code"])

    parsed_info = parse_identification(result["stdout"])

    print(json.dumps(parsed_info, indent=4, ensure_ascii=False))
