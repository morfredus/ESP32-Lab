#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


def is_json_start(byte_value: int) -> bool:
    return byte_value in (ord("{"), ord("["))


def extract_candidates(data: bytes):
    candidates = []
    size = len(data)

    for start in range(size):
        if not is_json_start(data[start]):
            continue

        opening = data[start]
        closing = ord("}") if opening == ord("{") else ord("[")

        depth = 0
        in_string = False
        escaped = False

        for pos in range(start, size):
            current = data[pos]

            if in_string:
                if escaped:
                    escaped = False
                elif current == ord("\\"):
                    escaped = True
                elif current == ord('"'):
                    in_string = False

                continue

            if current == ord('"'):
                in_string = True
                continue

            if current == opening:
                depth += 1

            elif current == closing:
                depth -= 1

                if depth == 0:
                    raw = data[start:pos + 1]

                    try:
                        decoded = raw.decode("utf-8")
                        parsed = json.loads(decoded)

                        candidates.append({
                            "offset": start,
                            "end_offset": pos,
                            "size_bytes": len(raw),
                            "root_type": type(parsed).__name__,
                            "valid": True,
                            "data": parsed,
                        })

                    except (UnicodeDecodeError, json.JSONDecodeError):
                        pass

                    break

    return candidates


def deduplicate_candidates(candidates):
    unique = []
    seen = set()

    for candidate in candidates:
        key = json.dumps(
            candidate["data"],
            ensure_ascii=False,
            sort_keys=True,
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(candidate)

    return unique


def main():
    parser = argparse.ArgumentParser(
        description="Extrait les candidats JSON d'une image binaire"
    )

    parser.add_argument(
        "input_file",
        type=Path,
        help="Image binaire à analyser",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Fichier JSON de sortie",
    )

    args = parser.parse_args()

    if not args.input_file.exists():
        raise SystemExit(
            f"[ERROR] Fichier introuvable : {args.input_file}"
        )

    data = args.input_file.read_bytes()

    print(f"[INFO] Fichier : {args.input_file}")
    print(f"[INFO] Taille : {len(data)} octets")

    candidates = extract_candidates(data)

    print(f"[INFO] Candidats JSON valides : {len(candidates)}")

    unique_candidates = deduplicate_candidates(candidates)

    print(
        "[INFO] Candidats uniques : "
        f"{len(unique_candidates)}"
    )

    result = {
        "source_file": str(args.input_file),
        "source_size_bytes": len(data),
        "candidate_count": len(candidates),
        "unique_count": len(unique_candidates),
        "candidates": unique_candidates,
        "limitations": [
            "Extraction basée sur les structures JSON visibles",
            "Les données fragmentées ou compressées ne sont pas reconstruites",
            "Les offsets correspondent à l'image binaire analysée",
        ],
    }

    output_file = args.output

    if output_file is None:
        output_file = (
            Path("data/analysis")
            / f"{args.input_file.stem}_json_candidates.json"
        )

    output_file.parent.mkdir(parents=True, exist_ok=True)

    output_file.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"[OK] Résultat écrit dans : {output_file}")

    for index, candidate in enumerate(unique_candidates, start=1):
        print(
            f"[{index:02d}] "
            f"offset=0x{candidate['offset']:06X} "
            f"size={candidate['size_bytes']} "
            f"type={candidate['root_type']}"
        )


if __name__ == "__main__":
    main()
