#!/usr/bin/env python3

import json
import struct
from pathlib import Path


INPUT = Path("data/analysis/raw/sfdp_s3.bin")
OUTPUT = Path("data/analysis/reports/sfdp_s3_analysis.json")


def decode_parameter_header(data, offset):
    if offset + 8 > len(data):
        return None

    parameter_id_lsb = data[offset]
    minor_revision = data[offset + 1]
    major_revision = data[offset + 2]
    length_dw = data[offset + 3]

    parameter_pointer = int.from_bytes(
        data[offset + 4:offset + 7],
        byteorder="little",
    )

    parameter_id_msb = data[offset + 7]

    parameter_id = (
        parameter_id_msb << 8
    ) | parameter_id_lsb

    return {
        "offset": f"0x{offset:02X}",
        "parameter_id": f"0x{parameter_id:04X}",
        "minor_revision": minor_revision,
        "major_revision": major_revision,
        "length_dwords": length_dw,
        "length_bytes": length_dw * 4,
        "parameter_pointer": f"0x{parameter_pointer:06X}",
    }


def main():
    if not INPUT.exists():
        raise SystemExit(f"Fichier absent : {INPUT}")

    data = INPUT.read_bytes()

    report = {
        "file": str(INPUT),
        "size_bytes": len(data),
        "signature": data[:4].decode("ascii", errors="replace"),
        "valid_signature": data[:4] == b"SFDP",
        "header": {},
        "parameter_headers": [],
        "tables": [],
        "raw_hex": data.hex(" "),
        "limitations": [],
    }

    if len(data) < 9:
        report["limitations"].append(
            "Données insuffisantes pour analyser l'en-tête SFDP."
        )
    else:
        report["header"] = {
            "minor_revision": data[4],
            "major_revision": data[5],
            "number_of_parameter_headers": data[6] + 1,
            "access_protocol": f"0x{data[7]:02X}",
        }

        count = report["header"]["number_of_parameter_headers"]

        for index in range(count):
            offset = 8 + (index * 8)
            header = decode_parameter_header(data, offset)

            if header is None:
                report["limitations"].append(
                    f"En-tête incomplet à l'offset 0x{offset:02X}."
                )
                continue

            report["parameter_headers"].append(header)

            pointer = int(header["parameter_pointer"], 16)
            size = header["length_bytes"]
            end = pointer + size

            table = {
                "parameter_id": header["parameter_id"],
                "start": header["parameter_pointer"],
                "length_bytes": size,
                "available_in_capture": end <= len(data),
            }

            if end <= len(data):
                table["data_hex"] = data[pointer:end].hex(" ")
            else:
                table["data_hex"] = data[pointer:].hex(" ")
                report["limitations"].append(
                    f"Table {header['parameter_id']} tronquée "
                    f"(offset 0x{pointer:X}, longueur {size} octets)."
                )

            report["tables"].append(table)

    if not report["valid_signature"]:
        report["limitations"].append(
            "Signature SFDP invalide ou absente."
        )

    if len(data) < 256:
        report["limitations"].append(
            "La capture contient moins de 256 octets."
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(report, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )

    print(json.dumps(report, indent=4, ensure_ascii=False))
    print()
    print(f"Rapport enregistré : {OUTPUT}")


if __name__ == "__main__":
    main()
