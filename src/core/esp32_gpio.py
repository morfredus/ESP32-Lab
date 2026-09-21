"""
Cartographie GPIO d'une puce ESP32 (lecture seule, niveau puce).

A partir de la famille exacte detectee (esp32 / esp32s3 / esp32c3...), calcule
pour chaque broche sa classification (strapping, entree seule, reserve
Flash/PSRAM, USB-JTAG, ADC, DAC), un statut d'usage et des avertissements de
boot. Les donnees proviennent de la base de references locale
(``espressif_dataset``), curee sur les sources officielles Espressif.

Important : ce module raisonne au niveau de la PUCE. L'exposition reelle des
broches sur une carte donnee (bouton BOOT, LED, ecran, USB natif du fabricant)
depend du profil de la carte et ne peut pas se deduire des eFuses : elle est donc
signalee comme inconnue (``board_exposure: "unknown"``).
"""

from core import espressif_dataset


# Avertissements affiches en tete des sections a developper.
WARNINGS = {
    "strapping": (
        "Broches de strapping : leur niveau est lu au reset et fixe le mode de "
        "boot. Un niveau impose au demarrage peut empecher le demarrage ou le "
        "flashage. A utiliser avec precaution."
    ),
    "flash_psram": (
        "Broches reservees ou potentiellement reservees selon la configuration "
        "materielle Flash / PSRAM du module. Ne pas les reaffecter sans connaitre "
        "le montage, meme si elles apparaissent techniquement dans la liste des "
        "GPIO."
    ),
    "system": (
        "Broches utilisees par des interfaces systeme (UART console, USB-JTAG). "
        "Les reaffecter desactive la fonction correspondante."
    ),
}


def _to_int_map(raw):
    """Convertit un mapping JSON {"3": 0} en {3: 0}."""

    result = {}
    for key, value in (raw or {}).items():
        try:
            result[int(key)] = value
        except (TypeError, ValueError):
            continue
    return result


def compute_gpio_map(chip):
    """
    Construit la cartographie GPIO pour une famille de puce.

    Retourne un dict pret a serialiser. ``status`` vaut ``error`` si la famille
    est absente (chip vide), ``ok`` sinon avec ``family_supported`` a ``False``
    quand la famille n'est pas couverte par la base.
    """

    normalized = espressif_dataset.normalize_family(chip)

    if not normalized:
        return {
            "status": "error",
            "message": "La famille de puce est requise (parametre chip).",
        }

    family = espressif_dataset.load_family(normalized)
    meta = espressif_dataset.metadata() or {}
    source = meta.get("source")
    dataset_version = meta.get("dataset_version")

    if family is None:
        return {
            "status": "ok",
            "chip_family": normalized,
            "family_supported": False,
            "gpio_count": 0,
            "source": source,
            "dataset_version": dataset_version,
            "board_exposure": "unknown",
            "pins": [],
            "summary": {"available": 0, "restricted": 0, "avoid": 0},
            "warnings": {},
            "message": (
                "Profil GPIO non disponible pour cette famille dans la base "
                "locale. Les familles couvertes sont ESP32, ESP32-S3 et ESP32-C3."
            ),
        }

    present = sorted(set(family.get("pins_present", [])))
    strapping = set(family.get("strapping", []))
    input_only = set(family.get("input_only", []))
    flash = set(family.get("flash_psram", []))
    octal = set(family.get("flash_psram_octal", []))
    usb = set(family.get("usb_jtag", []))
    dac = set(family.get("dac", []))
    adc1 = _to_int_map(family.get("adc1"))
    adc2 = _to_int_map(family.get("adc2"))
    notes = {}
    for key, value in (family.get("notes") or {}).items():
        try:
            notes[int(key)] = value
        except (TypeError, ValueError):
            continue

    pins = []
    summary = {"available": 0, "restricted": 0, "avoid": 0}

    for gpio in present:
        adc = None
        if gpio in adc1:
            adc = f"ADC1_CH{adc1[gpio]}"
        elif gpio in adc2:
            adc = f"ADC2_CH{adc2[gpio]}"

        is_strap = gpio in strapping
        is_input_only = gpio in input_only
        is_flash = gpio in flash
        is_octal = gpio in octal
        is_usb = gpio in usb
        is_dac = gpio in dac

        functions = []
        if is_strap:
            functions.append("Strapping")
        if is_input_only:
            functions.append("Entree seule")
        if is_flash:
            functions.append("Flash/PSRAM")
        if is_octal:
            functions.append("Flash/PSRAM (Octal)")
        if is_usb:
            functions.append("USB-JTAG")
        if adc:
            functions.append(adc)
        if is_dac:
            functions.append("DAC")

        # Statut d'usage (au niveau puce) : 3 categories.
        if is_flash:
            status = "avoid"
            classification = "Reserve Flash/PSRAM"
        elif is_octal:
            status = "restricted"
            classification = "Reserve si Flash/PSRAM Octal"
        elif is_strap:
            status = "restricted"
            classification = "Strapping"
        elif is_input_only:
            status = "restricted"
            classification = "Entree seule"
        elif is_usb:
            status = "restricted"
            classification = "USB-JTAG"
        else:
            status = "available"
            classification = "Usage general"

        summary[status] += 1

        boot_caveat = None
        if is_strap:
            boot_caveat = (
                "Niveau lu au demarrage : influence le mode de boot. Eviter de "
                "forcer un etat au reset."
            )

        pins.append({
            "gpio": gpio,
            "classification": classification,
            "status": status,
            "functions": functions,
            "strapping": is_strap,
            "input_only": is_input_only,
            "flash_psram": is_flash or is_octal,
            "usb_jtag": is_usb,
            "adc": adc,
            "dac": is_dac,
            "note": notes.get(gpio),
            "boot_caveat": boot_caveat,
        })

    warnings = {}
    if strapping:
        warnings["strapping"] = WARNINGS["strapping"]
    if flash or octal:
        flash_warning = WARNINGS["flash_psram"]
        if octal:
            lo, hi = min(octal), max(octal)
            flash_warning += (
                f" En particulier, GPIO{lo} a GPIO{hi} ne sont reserves que si "
                "le module utilise une Flash ou une PSRAM Octal ; sinon ils sont "
                "disponibles."
            )
        warnings["flash_psram"] = flash_warning
    if usb:
        warnings["system"] = WARNINGS["system"]

    return {
        "status": "ok",
        "chip_family": family.get("family", normalized),
        "label": family.get("label"),
        "family_supported": True,
        "gpio_count": len(present),
        "source": source,
        "dataset_version": dataset_version,
        "board_exposure": "unknown",
        "board_exposure_note": (
            "L'exposition reelle des broches sur la carte (BOOT, LED, ecran, USB "
            "natif du fabricant) depend du profil de la carte et n'est pas "
            "deductible de la puce. A confirmer avec la documentation de la carte."
        ),
        "summary": summary,
        "pins": pins,
        "warnings": warnings,
    }
