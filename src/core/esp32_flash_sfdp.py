"""
Lecture bas niveau de la puce Flash SPI : SFDP et identifiant unique.

Ces informations sont rarement exposées :
- **SFDP** (JESD216, « Serial Flash Discoverable Parameters ») : table gravée
  par le fabricant décrivant les capacités réelles de la puce (densité,
  granularités d'effacement, modes de lecture rapide, adressage) ;
- **Identifiant unique** (commande 0x4B) : numéro de série 64 bits propre à
  chaque puce Flash.

La lecture utilise l'API Python d'esptool sur **une seule connexion** (via un
sous-processus lancé avec l'interpréteur qui dispose d'esptool). Tout est en
**lecture seule** : envoi de commandes SPI de lecture uniquement (0x9F, 0x4B,
0x5A/SFDP), aucune écriture.
"""

import json
import subprocess

from core import flash_catalog
from core.esptool_runner import resolved_python


SFDP_SIGNATURE = 0x50444653   # « SFDP » en little-endian


# Script exécuté par l'interpréteur disposant d'esptool. Il ouvre une seule
# connexion, lit les valeurs brutes et les imprime en JSON (préfixe marqueur).
READER_SCRIPT = r'''
import sys, json, esptool

port = sys.argv[1]
chip = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else None

esp = esptool.detect_chip(port)
esp = esp.run_stub()

def sfdp(addr):
    return esp.read_spiflash_sfdp(addr, 32)

def le_bytes(word, count):
    # Octets dans l'ordre du fil (premier reçu = poids faible de l'entier).
    return [(word >> (8 * i)) & 0xFF for i in range(count)]

jedec = esp.run_spiflash_command(0x9F, read_bits=24)
uid_hi = esp.run_spiflash_command(0x4B, read_bits=32, dummy_len=32)
uid_lo = esp.run_spiflash_command(0x4B, read_bits=32, dummy_len=64)
unique_bytes = le_bytes(uid_hi, 4) + le_bytes(uid_lo, 4)

w0 = sfdp(0)
w1 = sfdp(4)
nph = ((w1 >> 16) & 0xFF) + 1

headers = []
for i in range(nph):
    base = 8 + i * 8
    headers.append([sfdp(base), sfdp(base + 4)])

bfpt_ptr = None
bfpt_len = 0
for hw0, hw1 in headers:
    id_lsb = hw0 & 0xFF
    id_msb = (hw1 >> 24) & 0xFF
    if id_lsb == 0x00 and id_msb == 0xFF:
        bfpt_len = (hw0 >> 24) & 0xFF
        bfpt_ptr = hw1 & 0xFFFFFF
        break

bfpt = []
if bfpt_ptr is not None:
    for i in range(bfpt_len):
        bfpt.append(sfdp(bfpt_ptr + i * 4))

try:
    esp.hard_reset()
except Exception:
    pass

print("###JSON###" + json.dumps({
    "jedec": jedec,
    "unique_bytes": unique_bytes,
    "header": [w0, w1],
    "param_headers": headers,
    "bfpt_pointer": bfpt_ptr,
    "bfpt_length": bfpt_len,
    "bfpt": bfpt,
}))
'''


def _size_label(num_bytes):
    """Formate une taille en Ko / Mo (base 1024)."""

    if num_bytes >= 1024 * 1024:
        return f"{num_bytes // (1024 * 1024)} Mio"
    if num_bytes >= 1024:
        return f"{num_bytes // 1024} Kio"
    return f"{num_bytes} o"


def parse_sfdp_header(header, param_headers):
    """Analyse l'entête SFDP et les entêtes de tables de paramètres."""

    word0, word1 = header[0], header[1]

    parsed_headers = []
    for hw0, hw1 in param_headers:
        parsed_headers.append({
            "id": f"0x{((hw1 >> 24) & 0xFF):02X}{(hw0 & 0xFF):02X}",
            "major": (hw0 >> 16) & 0xFF,
            "minor": (hw0 >> 8) & 0xFF,
            "length_dwords": (hw0 >> 24) & 0xFF,
            "pointer": hw1 & 0xFFFFFF,
        })

    return {
        "signature_valid": word0 == SFDP_SIGNATURE,
        "revision": f"{(word1 >> 8) & 0xFF}.{word1 & 0xFF}",
        "num_param_headers": ((word1 >> 16) & 0xFF) + 1,
        "param_headers": parsed_headers,
    }


def parse_bfpt(bfpt):
    """
    Analyse la table de paramètres Flash de base (BFPT, JESD216).

    Retourne les capacités réelles de la puce : densité, adressage,
    granularités d'effacement, modes de lecture rapide.
    """

    if len(bfpt) < 2:
        return {}

    dw1 = bfpt[0]
    dw2 = bfpt[1]

    # Densité (DWORD 2).
    if dw2 & 0x80000000:
        capacity_bits = 1 << (dw2 & 0x7FFFFFFF)
    else:
        capacity_bits = dw2 + 1
    capacity_bytes = capacity_bits // 8

    # Adressage (DWORD 1, bits 18:17).
    address_modes = {0: "3 octets", 1: "3 ou 4 octets", 2: "4 octets"}
    address_bytes = address_modes.get((dw1 >> 17) & 0x3, "?")

    fast_read = {
        "1-1-2": bool((dw1 >> 16) & 1),
        "1-2-2": bool((dw1 >> 20) & 1),
        "1-1-4": bool((dw1 >> 22) & 1),
        "1-4-4": bool((dw1 >> 21) & 1),
        "dtr": bool((dw1 >> 19) & 1),
    }

    # Types d'effacement (DWORD 8 et 9).
    erase_types = []
    raw_types = []
    if len(bfpt) >= 8:
        dw8 = bfpt[7]
        raw_types.append((dw8 & 0xFF, (dw8 >> 8) & 0xFF))
        raw_types.append(((dw8 >> 16) & 0xFF, (dw8 >> 24) & 0xFF))
    if len(bfpt) >= 9:
        dw9 = bfpt[8]
        raw_types.append((dw9 & 0xFF, (dw9 >> 8) & 0xFF))
        raw_types.append(((dw9 >> 16) & 0xFF, (dw9 >> 24) & 0xFF))

    for exponent, opcode in raw_types:
        if exponent == 0:
            continue
        size = 1 << exponent
        erase_types.append({
            "size": size,
            "size_label": _size_label(size),
            "opcode": f"0x{opcode:02X}",
        })

    return {
        "capacity_bytes": capacity_bytes,
        "capacity_label": _size_label(capacity_bytes),
        "address_bytes": address_bytes,
        "erase_4kb": (dw1 & 0x3) == 0x01,
        "erase_4kb_opcode": f"0x{(dw1 >> 8) & 0xFF:02X}",
        "fast_read": fast_read,
        "erase_types": erase_types,
    }


def build_flash_report(raw):
    """Construit le rapport Flash complet à partir des valeurs brutes lues."""

    # Le JEDEC (commande 0x9F) revient dans l'ordre du fil : octet fabricant
    # en poids faible, puis type mémoire, puis capacité.
    jedec = raw.get("jedec", 0)
    manufacturer_byte = jedec & 0xFF
    memory_type = (jedec >> 8) & 0xFF
    capacity_code = (jedec >> 16) & 0xFF
    manufacturer_id = f"{manufacturer_byte:02X}"
    device_id = f"{memory_type:02X}{capacity_code:02X}"
    # Identifiant JEDEC dans l'ordre conventionnel fabricant-type-capacité.
    jedec_conventional = (manufacturer_byte << 16) | (memory_type << 8) | capacity_code

    unique_bytes = raw.get("unique_bytes") or []
    unique_hex = " ".join(f"{byte:02X}" for byte in unique_bytes)
    unique_value = "0x" + "".join(f"{byte:02X}" for byte in unique_bytes)

    header = raw.get("header") or [0, 0]
    sfdp = parse_sfdp_header(header, raw.get("param_headers", []))
    flash = parse_bfpt(raw.get("bfpt", []))

    return {
        "status": "ok",
        "jedec": {
            "raw": f"0x{jedec_conventional:06X}",
            "manufacturer_id": manufacturer_id,
            "manufacturer_name": flash_catalog.describe_manufacturer(manufacturer_id),
            "device_id": device_id,
            "device_name": flash_catalog.describe_device(device_id),
        },
        "unique_id": {
            "hex": unique_hex,
            "value": unique_value,
        },
        "sfdp": sfdp,
        "flash": flash,
    }


def read_flash_details(port, chip=None, timeout=60):
    """
    Lit le SFDP et l'identifiant unique de la puce Flash (lecture seule).

    Retourne le rapport, ou ``{"status": "error", "message": ...}``.
    """

    python = resolved_python()
    if not python:
        return {
            "status": "error",
            "message": "Interpréteur esptool introuvable pour la lecture SFDP.",
        }

    command = [python, "-c", READER_SCRIPT, port, chip or ""]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        return {
            "status": "error",
            "message": f"Délai dépassé lors de la lecture SFDP : {error}",
        }

    marker = "###JSON###"
    index = result.stdout.find(marker)

    if index == -1:
        return {
            "status": "error",
            "message": (
                "Lecture SFDP impossible : "
                + (result.stderr.strip().splitlines()[-1]
                   if result.stderr.strip() else "sortie inattendue")
            ),
        }

    try:
        raw = json.loads(result.stdout[index + len(marker):].strip())
    except json.JSONDecodeError as error:
        return {
            "status": "error",
            "message": f"Analyse de la sortie SFDP impossible : {error}",
        }

    return build_flash_report(raw)
