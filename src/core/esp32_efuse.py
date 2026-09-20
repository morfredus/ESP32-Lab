"""
Lecture et analyse des eFuses d'un ESP32 via espefuse.

Les eFuses contiennent les informations les plus profondes du silicium :
révision exacte de la puce, identifiant unique, état de sécurité (secure
boot, chiffrement Flash), calibration ADC/température, configuration SPI/USB…

La lecture se fait via ``espefuse summary --format json`` : commande de
**synthèse en lecture seule**, aucune écriture, aucune modification d'eFuse.
"""

import json

from core.esptool_runner import run_espefuse


# Ordre et libellés lisibles des catégories renvoyées par espefuse.
CATEGORY_LABELS = {
    "identity": "Identité du silicium",
    "MAC": "Adresses MAC",
    "security": "Sécurité",
    "calibration": "Calibration",
    "flash": "Flash",
    "config": "Configuration",
    "spi pad": "Broches SPI",
    "usb": "USB",
    "jtag": "JTAG",
    "vdd": "Alimentation (VDD)",
    "wdt": "Watchdog",
}

CATEGORY_ORDER = [
    "identity",
    "MAC",
    "security",
    "calibration",
    "flash",
    "config",
    "spi pad",
    "usb",
    "jtag",
    "vdd",
    "wdt",
]


def parse_efuse_summary(raw_text):
    """
    Extrait le dictionnaire JSON de la sortie d'``espefuse summary``.

    La sortie contient un préambule texte (« Connecting... », etc.) avant le
    JSON : on isole le premier objet JSON complet.
    """

    start = raw_text.find("{")
    end = raw_text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError("Aucun objet JSON trouvé dans la sortie espefuse.")

    return json.loads(raw_text[start:end + 1])


def _as_bool(value):
    """Convertit une valeur espefuse (« True »/« False »/bool) en booléen."""

    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in {"true", "1", "yes"}


def _field_value(efuses, name, default=None):
    """Retourne la valeur lisible d'un eFuse, ou une valeur par défaut."""

    entry = efuses.get(name)
    if not entry:
        return default

    return entry.get("value", default)


def derive_mac_addresses(base_mac):
    """
    Déduit les adresses MAC universelles à partir de la MAC de base.

    Convention ESP-IDF : Wi-Fi STA = base, Wi-Fi AP = base+1,
    Bluetooth = base+2, Ethernet = base+3 (incrément sur les 48 bits).
    """

    if not base_mac:
        return {}

    # Nettoie une éventuelle mention « (OK) » et espaces.
    cleaned = base_mac.split("(")[0].strip()

    try:
        octets = [int(part, 16) for part in cleaned.split(":")]
    except ValueError:
        return {}

    if len(octets) != 6:
        return {}

    base_value = int.from_bytes(bytes(octets), "big")

    def to_mac(value):
        raw = value.to_bytes(6, "big")
        return ":".join(f"{byte:02x}" for byte in raw)

    return {
        "wifi_sta": to_mac(base_value),
        "wifi_ap": to_mac(base_value + 1),
        "bluetooth": to_mac(base_value + 2),
        "ethernet": to_mac(base_value + 3),
    }


def build_security_posture(efuses):
    """Construit un résumé lisible de l'état de sécurité de la puce."""

    flash_crypt = _field_value(efuses, "SPI_BOOT_CRYPT_CNT", "Disable")

    keys_used = []
    for slot in range(6):
        purpose = _field_value(efuses, f"KEY_PURPOSE_{slot}", "USER")
        if purpose and str(purpose).upper() != "USER":
            keys_used.append({"slot": slot, "purpose": purpose})

    return {
        "secure_boot": _as_bool(_field_value(efuses, "SECURE_BOOT_EN", False)),
        "flash_encryption": str(flash_crypt).lower() not in {"disable", "0"},
        "flash_encryption_state": flash_crypt,
        "usb_jtag_disabled": _as_bool(_field_value(efuses, "DIS_USB_JTAG", False)),
        "download_mode_disabled": _as_bool(
            _field_value(efuses, "DIS_DOWNLOAD_MODE", False)
        ),
        "secure_download": _as_bool(
            _field_value(efuses, "ENABLE_SECURITY_DOWNLOAD", False)
        ),
        "secure_version": _field_value(efuses, "SECURE_VERSION", 0),
        "keys_used": keys_used,
    }


def build_identity(efuses):
    """Construit un résumé de l'identité du silicium."""

    major = _field_value(efuses, "WAFER_VERSION_MAJOR")
    minor = _field_value(efuses, "WAFER_VERSION_MINOR")

    revision = None
    if major is not None and minor is not None:
        revision = f"v{major}.{minor}"

    base_mac = _field_value(efuses, "MAC")

    return {
        "wafer_version_major": major,
        "wafer_version_minor": minor,
        "revision": revision,
        "pkg_version": _field_value(efuses, "PKG_VERSION"),
        "blk_version_major": _field_value(efuses, "BLK_VERSION_MAJOR"),
        "blk_version_minor": _field_value(efuses, "BLK_VERSION_MINOR"),
        "optional_unique_id": _field_value(efuses, "OPTIONAL_UNIQUE_ID"),
        "mac": base_mac,
        "derived_macs": derive_mac_addresses(base_mac),
        "psram_cap": _field_value(efuses, "PSRAM_CAP"),
        "flash_cap": _field_value(efuses, "FLASH_CAP"),
        "temp_calib": _field_value(efuses, "TEMP_CALIB"),
    }


def group_by_category(efuses):
    """Regroupe les eFuses par catégorie, dans un ordre lisible."""

    grouped = {}

    for name, info in efuses.items():
        category = info.get("category", "autre")
        grouped.setdefault(category, []).append({
            "name": name,
            "value": info.get("value"),
            "readable": info.get("readable", True),
            "description": info.get("description", ""),
            "raw_value": info.get("raw_value"),
            "block": info.get("block"),
            "bit_len": info.get("bit_len"),
        })

    # Trie les champs par nom dans chaque catégorie.
    for fields in grouped.values():
        fields.sort(key=lambda item: item["name"])

    # Réordonne les catégories selon CATEGORY_ORDER, puis alphabétique.
    ordered = {}
    for category in CATEGORY_ORDER:
        if category in grouped:
            ordered[category] = grouped.pop(category)
    for category in sorted(grouped):
        ordered[category] = grouped[category]

    return ordered


def build_efuse_report(efuses):
    """Construit le rapport eFuse complet destiné à l'interface."""

    return {
        "status": "ok",
        "count": len(efuses),
        "identity": build_identity(efuses),
        "security": build_security_posture(efuses),
        "category_labels": CATEGORY_LABELS,
        "categories": group_by_category(efuses),
    }


def read_efuses(port, chip=None, timeout=90):
    """
    Lit et analyse les eFuses de la carte (lecture seule).

    Retourne le rapport eFuse, ou ``{"status": "error", "message": ...}``.
    """

    arguments = ["--port", port]

    if chip:
        arguments += ["--chip", chip]

    arguments += ["summary", "--format", "json"]

    try:
        result = run_espefuse(arguments, timeout=timeout)
    except Exception as error:  # noqa: BLE001 - on renvoie l'erreur telle quelle
        return {
            "status": "error",
            "message": f"Lecture des eFuses impossible : {error}",
        }

    if result.returncode != 0:
        return {
            "status": "error",
            "message": (
                "espefuse a échoué : "
                + (result.stderr.strip() or "erreur inconnue")
            ),
        }

    try:
        efuses = parse_efuse_summary(result.stdout)
    except (ValueError, json.JSONDecodeError) as error:
        return {
            "status": "error",
            "message": f"Analyse de la sortie espefuse impossible : {error}",
        }

    return build_efuse_report(efuses)
