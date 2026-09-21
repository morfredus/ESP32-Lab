"""
Lecture et analyse de la partition NVS d'un ESP32.

La NVS (Non-Volatile Storage) est organisée en **pages** de 4096 octets :
- en-tête de page (32 octets) : état, numéro de séquence, version, CRC ;
- table d'état des entrées (32 octets) : 2 bits par entrée ;
- 126 entrées de 32 octets : namespace, type, span, chunk, CRC, clé, données.

Ce module lit la partition NVS de la carte (lecture seule, via
``esptool read-flash``) et produit un rapport structuré compatible avec
l'affichage NVS existant, puis le sauvegarde dans
``data/analysis/reports/nvs_structure_analysis.json``.
"""

import json
import subprocess
import tempfile
import zlib
from pathlib import Path

from core.esp32_partitions import read_partition_table
from core.esptool_runner import run_esptool


PROJECT_ROOT = Path(__file__).resolve().parents[2]
NVS_REPORT_PATH = (
    PROJECT_ROOT / "data" / "analysis" / "reports"
    / "nvs_structure_analysis.json"
)

PAGE_SIZE = 4096
ENTRY_SIZE = 32
ENTRIES_PER_PAGE = 126
HEADER_SIZE = 32
BITMAP_SIZE = 32

# États de page (uint32 little-endian).
PAGE_STATES = {
    0xFFFFFFFF: "empty_or_uninitialized",
    0xFFFFFFFE: "active",
    0xFFFFFFFC: "full",
    0xFFFFFFF8: "freeing",
    0xFFFFFFF0: "corrupt",
}

# États d'entrée (2 bits).
ENTRY_STATES = {
    0b11: "empty",
    0b10: "written",
    0b00: "erased",
    0b01: "illegal",
}

# Types NVS ESP-IDF.
NVS_TYPES = {
    0x01: "u8", 0x11: "i8", 0x02: "u16", 0x12: "i16",
    0x04: "u32", 0x14: "i32", 0x08: "u64", 0x18: "i64",
    0x21: "str", 0x41: "blob", 0x42: "blob_data", 0x48: "blob_idx",
}


def _esp_crc32(crc, data):
    """
    Équivalent d'``esp_rom_crc32_le`` tel qu'utilisé par la NVS : CRC-32
    réfléchi chaîné, initialisé à 0xFFFFFFFF, sans inversion finale
    (``zlib.crc32(data, crc)``).
    """

    return zlib.crc32(data, crc) & 0xFFFFFFFF


def _type_name(type_raw):
    return NVS_TYPES.get(type_raw, f"unknown (0x{type_raw:02X})")


def _decode_entry(entry):
    """Décode une entrée NVS de 32 octets."""

    namespace_index = entry[0]
    type_raw = entry[1]
    span = entry[2]
    chunk_index = entry[3]
    crc_stored = int.from_bytes(entry[4:8], "little")
    key = entry[8:24].split(b"\x00", 1)[0].decode("ascii", errors="replace")
    data = entry[24:32]

    crc_calculated = _esp_crc32(
        _esp_crc32(0xFFFFFFFF, entry[0:4]), entry[8:32]
    )

    return {
        "namespace_index": namespace_index,
        "type_raw": f"0x{type_raw:02X}",
        "type_name": _type_name(type_raw),
        "span": span,
        "chunk_index": chunk_index,
        "crc_stored": f"0x{crc_stored:08X}",
        "crc_calculated": f"0x{crc_calculated:08X}",
        "crc_match": crc_stored == crc_calculated,
        "key": key,
        "key_hex": entry[8:24].hex(),
        "data_hex": data.hex(),
        "raw_hex": entry.hex(),
    }


def _parse_page(page_bytes, page_index):
    """Analyse une page NVS de 4096 octets."""

    state_value = int.from_bytes(page_bytes[0:4], "little")
    state_name = PAGE_STATES.get(state_value, f"0x{state_value:08X}")
    sequence = int.from_bytes(page_bytes[4:8], "little")
    header_crc_stored = int.from_bytes(page_bytes[28:32], "little")
    header_crc_calculated = _esp_crc32(0xFFFFFFFF, page_bytes[4:28])

    uninitialized = state_name == "empty_or_uninitialized"

    bitmap = page_bytes[HEADER_SIZE:HEADER_SIZE + BITMAP_SIZE]

    entries = []
    counts = {"written": 0, "erased": 0, "empty": 0, "illegal": 0}

    for index in range(ENTRIES_PER_PAGE):
        raw_state = (bitmap[index // 4] >> ((index % 4) * 2)) & 0x3
        state_label = ENTRY_STATES.get(raw_state, "empty")
        counts[state_label] = counts.get(state_label, 0) + 1

        start = HEADER_SIZE + BITMAP_SIZE + index * ENTRY_SIZE
        entry_bytes = page_bytes[start:start + ENTRY_SIZE]

        entry = {
            "index": index,
            "offset": f"0x{start:05X}",
            "state": {"raw": f"0b{raw_state:02b}", "name": state_label},
        }

        if state_label == "written" and len(entry_bytes) == ENTRY_SIZE:
            entry["decoded"] = _decode_entry(entry_bytes)

        entries.append(entry)

    return {
        "page_index": page_index,
        "offset": f"0x{page_index * PAGE_SIZE:06X}",
        "state_raw": f"0x{state_value:08X}",
        "state_name": state_name,
        "sequence": sequence,
        "version": page_bytes[8],
        "header_crc_stored": f"0x{header_crc_stored:08X}",
        "header_crc_calculated": f"0x{header_crc_calculated:08X}",
        "header_crc_match": (
            None if uninitialized
            else header_crc_stored == header_crc_calculated
        ),
        "entry_counts": {
            "written": counts["written"],
            "erased": counts["erased"],
            "empty": counts["empty"],
        },
        "entries": entries,
    }


def analyze_nvs_dump(raw_bytes, source_name="nvs.bin"):
    """Analyse un dump binaire NVS et retourne le rapport structuré."""

    page_count = len(raw_bytes) // PAGE_SIZE
    pages = []

    for page_index in range(page_count):
        start = page_index * PAGE_SIZE
        page_bytes = raw_bytes[start:start + PAGE_SIZE]
        pages.append(_parse_page(page_bytes, page_index))

    return {
        "file": source_name,
        "size_bytes": len(raw_bytes),
        "page_size_bytes": PAGE_SIZE,
        "page_count": page_count,
        "pages": pages,
        "limitations": [
            "Les valeurs string/blob multi-slots sont reconstituées côté "
            "interface, pas dans ce rapport brut.",
            "Un CRC valide indique la cohérence de la zone contrôlée, pas "
            "l'absence de corruption logique.",
            "Les entrées peuvent être chiffrées dans une configuration NVS "
            "chiffrée.",
        ],
    }


def _find_nvs_partition(port, chip):
    """Localise la partition NVS via la table de partitions (offset, taille)."""

    result = read_partition_table(port, chip=chip)
    if result.get("status") != "ok":
        return None

    for partition in result.get("partitions", []):
        if partition.get("subtype") == "nvs":
            return partition.get("offset"), partition.get("size")

    return None


def read_and_analyze_nvs(port, chip=None, offset=None, size=None, timeout=90):
    """
    Lit la partition NVS de la carte, l'analyse et sauvegarde le rapport.

    Retourne ``{"status": "ok", "report": ...}`` ou une erreur.
    """

    # Localise la NVS si l'offset/taille ne sont pas fournis.
    if offset is None or size is None:
        located = _find_nvs_partition(port, chip)
        if located:
            offset, size = located
        else:
            # Valeurs par défaut ESP-IDF (nvs à 0x9000, 20 Kio).
            offset, size = 0x9000, 0x5000

    with tempfile.TemporaryDirectory() as directory:
        dump_path = Path(directory) / "nvs.bin"

        arguments = ["--port", port]
        if chip:
            arguments += ["--chip", chip]
        arguments += ["read-flash", hex(offset), hex(size), str(dump_path)]

        try:
            result = run_esptool(arguments, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            return {
                "status": "error",
                "message": f"Délai dépassé lors de la lecture NVS : {error}",
            }

        if result.returncode != 0 or not dump_path.exists():
            return {
                "status": "error",
                "message": (
                    "Lecture de la partition NVS impossible : "
                    + (result.stderr.strip() or "erreur esptool")
                ),
            }

        raw_bytes = dump_path.read_bytes()

    report = analyze_nvs_dump(raw_bytes)
    save_nvs_report(report)

    return {"status": "ok", "report": report}


def save_nvs_report(report):
    """Sauvegarde le rapport NVS dans le dossier d'analyse."""

    NVS_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    NVS_REPORT_PATH.write_text(
        json.dumps(report, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
    return NVS_REPORT_PATH
