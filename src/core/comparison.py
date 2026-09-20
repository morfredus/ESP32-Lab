"""
Comparaison riche entre deux cartes ESP32 à partir de la base de données.

Rassemble, pour chaque carte, la dernière lecture de chaque section
(identification, eFuses, SFDP, partitions) et produit un comparatif structuré
par groupe de caractéristiques, avec repérage des différences.
"""

from core import database


NOT_CAPTURED = "Non capturé"


def _get(dictionary, *path, default=None):
    """Accès imbriqué sûr : _get(d, 'a', 'b') == d['a']['b'] ou default."""

    current = dictionary
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def _extract_identity(sections):
    inventory = sections.get("inventory") or {}
    info = inventory.get("identification", {})
    return [
        ("Puce", info.get("chip")),
        ("Révision", info.get("revision")),
        ("CPU (MHz)", info.get("cpu_frequency_mhz")),
        ("Quartz (MHz)", info.get("crystal_frequency_mhz")),
        ("PSRAM (Mo)", info.get("psram_size_mb")),
        ("Flash (Mo)", info.get("flash_size_mb")),
        ("Fabricant Flash", info.get("flash_manufacturer_name")
            or info.get("flash_manufacturer")),
        ("Référence Flash", info.get("flash_device_name")
            or info.get("flash_device")),
        ("Type Flash", info.get("flash_type")),
        ("Tension Flash", info.get("flash_voltage")),
    ]


def _extract_efuse(sections):
    efuse = sections.get("efuse") or {}
    identity = efuse.get("identity", {})
    security = efuse.get("security", {})
    return [
        ("Révision silicium", identity.get("revision")),
        ("Version package", identity.get("pkg_version")),
        ("ID unique 128 bits", identity.get("optional_unique_id")),
        ("Calibration temp. (°C)", identity.get("temp_calib")),
        ("PSRAM (eFuse)", identity.get("psram_cap")),
        ("Secure Boot", _yes_no(security.get("secure_boot"))),
        ("Chiffrement Flash", _yes_no(security.get("flash_encryption"))),
        ("USB-JTAG désactivé", _yes_no(security.get("usb_jtag_disabled"))),
        ("Version sécurisée", security.get("secure_version")),
        ("Clés provisionnées",
            len(security["keys_used"]) if security.get("keys_used") is not None
            else None),
    ]


def _extract_sfdp(sections):
    sfdp = sections.get("sfdp") or {}
    flash = sfdp.get("flash", {})
    fast_read = flash.get("fast_read", {})
    erase = ", ".join(
        e.get("size_label", "") for e in flash.get("erase_types", [])
    ) or None
    return [
        ("JEDEC", _get(sfdp, "jedec", "raw")),
        ("Référence (SFDP)", _get(sfdp, "jedec", "device_name")),
        ("ID unique Flash 64 bits", _get(sfdp, "unique_id", "hex")),
        ("Densité (SFDP)", flash.get("capacity_label")),
        ("Adressage", flash.get("address_bytes")),
        ("Révision SFDP", sfdp.get("revision")),
        ("Effacements", erase),
        ("Quad (1-4-4)", _yes_no(fast_read.get("1-4-4"))),
    ]


def _extract_partitions(sections):
    partitions = sections.get("partitions") or {}
    parts = partitions.get("partitions") or []

    layout = " | ".join(p.get("label", "?") for p in parts) or None
    total = sum(p.get("size", 0) for p in parts) if parts else None

    return [
        ("Nombre de partitions", len(parts) if parts else None),
        ("Disposition", layout),
        ("Taille totale (octets)", total),
    ]


def _yes_no(value):
    if value is None:
        return None
    return "Oui" if value else "Non"


def _normalize(value):
    if value is None or value == "":
        return NOT_CAPTURED
    return str(value)


def _build_group(title, rows_a, rows_b):
    rows = []
    same = 0
    different = 0

    for (label, value_a), (_, value_b) in zip(rows_a, rows_b):
        text_a = _normalize(value_a)
        text_b = _normalize(value_b)

        # On ne compte pas comme « différent » ce qui n'a pas été capturé.
        both_captured = (
            text_a != NOT_CAPTURED and text_b != NOT_CAPTURED
        )
        is_same = text_a == text_b

        if both_captured:
            if is_same:
                same += 1
            else:
                different += 1

        rows.append({
            "label": label,
            "a": text_a,
            "b": text_b,
            "same": is_same,
            "comparable": both_captured,
        })

    return {"title": title, "rows": rows, "same": same, "different": different}


def compare_devices(mac_a, mac_b):
    """Compare deux cartes et renvoie un comparatif structuré."""

    if not mac_a or not mac_b:
        return {"status": "error", "message": "Deux adresses MAC sont requises."}

    dossier_a = database.get_device_dossier(mac_a)
    dossier_b = database.get_device_dossier(mac_b)

    if not dossier_a or not dossier_b:
        return {"status": "error", "message": "Carte introuvable."}

    sections_a = dossier_a["sections"]
    sections_b = dossier_b["sections"]

    extractors = [
        ("Identité", _extract_identity),
        ("eFuses / Sécurité", _extract_efuse),
        ("Flash (SFDP)", _extract_sfdp),
        ("Partitions", _extract_partitions),
    ]

    groups = []
    total_same = 0
    total_different = 0

    for title, extractor in extractors:
        group = _build_group(title, extractor(sections_a), extractor(sections_b))
        groups.append(group)
        total_same += group["same"]
        total_different += group["different"]

    return {
        "status": "ok",
        "a": {"mac": dossier_a["device"]["mac"],
              "name": dossier_a["device"].get("name") or dossier_a["device"]["mac"],
              "captured": dossier_a["captured"]},
        "b": {"mac": dossier_b["device"]["mac"],
              "name": dossier_b["device"].get("name") or dossier_b["device"]["mac"],
              "captured": dossier_b["captured"]},
        "groups": groups,
        "summary": {"same": total_same, "different": total_different},
    }
