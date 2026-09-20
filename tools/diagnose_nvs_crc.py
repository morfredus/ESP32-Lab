import json
import struct
import zlib
from pathlib import Path

INPUT = Path("data/analysis/reports/nvs_structure_analysis.json")


def crc_standard(data):
    return zlib.crc32(data) & 0xFFFFFFFF


def crc_esp32(data):
    return zlib.crc32(data, 0xFFFFFFFF) & 0xFFFFFFFF


def crc_variants(raw):
    # Entrée NVS : 32 octets
    # CRC stocké : octets 4 à 7
    stored = struct.unpack("<I", raw[4:8])[0]

    variants = {
        "standard_0_4": crc_standard(raw[0:4]),
        "standard_8_32": crc_standard(raw[8:32]),
        "standard_combined": crc_standard(raw[0:4] + raw[8:32]),
        "esp32_0_4": crc_esp32(raw[0:4]),
        "esp32_8_32": crc_esp32(raw[8:32]),
        "esp32_combined": crc_esp32(raw[0:4] + raw[8:32]),
        "standard_full_without_crc": crc_standard(raw[0:4] + raw[8:32]),
        "esp32_full_without_crc": crc_esp32(raw[0:4] + raw[8:32]),
    }

    return stored, variants


def main():
    report = json.loads(INPUT.read_text(encoding="utf-8"))
    tested = 0

    for page in report.get("pages", []):
        for entry in page.get("entries", []):
            if entry.get("state", {}).get("name") != "written":
                continue

            decoded = entry.get("decoded", {})
            raw_hex = decoded.get("raw_hex")

            if not raw_hex:
                continue

            raw = bytes.fromhex(raw_hex)

            if len(raw) != 32:
                continue

            stored, variants = crc_variants(raw)

            print(
                f"page={page['page_index']} "
                f"entry={entry['index']} "
                f"key={decoded.get('key')!r}"
            )
            print(f"  stored=0x{stored:08X}")

            for name, value in variants.items():
                marker = " MATCH" if value == stored else ""
                print(f"  {name}=0x{value:08X}{marker}")

            print()

            tested += 1

            if tested >= 10:
                return


if __name__ == "__main__":
    main()
