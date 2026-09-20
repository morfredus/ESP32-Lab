#!/usr/bin/env python3

import argparse
import json
import re
from pathlib import Path


WIFI_PATTERN = re.compile(
    r"Connecté à [\"']?([^\"']+)[\"']?"
    r"\s+— IP ([0-9.]+)"
    r"\s+— RSSI (-?[0-9]+) dBm"
)


def parse_line(raw_line):
    try:
        return {
            "valid_json": True,
            "data": json.loads(raw_line),
        }
    except json.JSONDecodeError:
        match = WIFI_PATTERN.search(raw_line)

        result = {
            "valid_json": False,
            "raw": raw_line,
        }

        if match:
            result["recovered_type"] = "wifi"
            result["wifi_ssid"] = match.group(1)
            result["wifi_ip"] = match.group(2)
            result["wifi_rssi"] = int(match.group(3))

        return result


def main():
    parser = argparse.ArgumentParser(
        description="Analyse tolérante des lignes de boot"
    )

    parser.add_argument("input_file", type=Path)

    args = parser.parse_args()

    source = json.loads(
        args.input_file.read_text(encoding="utf-8")
    )

    entries = source.get("groups", {}).get(
        "bootlog_complete", []
    )

    for index, entry in enumerate(entries, 1):
        data = entry.get("data", {})

        print()
        print(
            f"=== Journal {index} | "
            f"boot={data.get('bootCount')} ==="
        )

        invalid_count = 0

        for raw_line in data.get("lines", []):
            result = parse_line(raw_line)

            if result["valid_json"]:
                line = result["data"]

                print(
                    f"[OK] {line.get('tag', '?'):10s} | "
                    f"{line.get('msg', '')}"
                )
            else:
                invalid_count += 1

                if result.get("recovered_type") == "wifi":
                    print(
                        "[RECUPERE] Wi-Fi | "
                        f"SSID={result['wifi_ssid']} | "
                        f"IP={result['wifi_ip']} | "
                        f"RSSI={result['wifi_rssi']} dBm"
                    )
                else:
                    print("[INVALIDE]", raw_line)

        print("Lignes invalides :", invalid_count)


if __name__ == "__main__":
    main()
