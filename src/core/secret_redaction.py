"""
Rédaction des secrets avant enregistrement en base.

Objectif : ne jamais persister de secret (mot de passe Wi-Fi, PMK, token, clé
eFuse) tout en gardant une **empreinte HMAC** stable pour détecter un
changement d'un scan au suivant.

Ces fonctions renvoient une **copie assainie** : l'objet d'origine (affiché en
direct dans l'interface) n'est pas modifié.
"""

import copy

from core.install_key import fingerprint, key_id


REDACTED = "<redacted>"

# Sous-chaînes marquant une clé NVS sensible (insensible à la casse).
SENSITIVE_NVS_SUBSTRINGS = (
    "pswd", "passwd", "password", "psk", "pmk", "token", "secret",
)


def is_sensitive_nvs_key(key):
    """Indique si une clé NVS désigne un secret (mot de passe, token…)."""

    if not key:
        return False

    lowered = str(key).lower()
    return any(part in lowered for part in SENSITIVE_NVS_SUBSTRINGS)


def _fingerprint_hex(hex_string):
    """Empreinte HMAC des octets décrits par une chaîne hexadécimale."""

    try:
        data = bytes.fromhex(hex_string) if hex_string else b""
    except ValueError:
        data = (hex_string or "").encode("utf-8")
    return fingerprint(data)


def sanitize_nvs_for_storage(result):
    """
    Copie assainie d'un résultat d'analyse NVS : les entrées sensibles (et les
    slots de données du blob correspondant) sont caviardées et remplacées par
    une empreinte.
    """

    if not isinstance(result, dict) or not isinstance(result.get("report"), dict):
        return result

    clone = copy.deepcopy(result)
    pages = clone.get("report", {}).get("pages") or []

    # Liste ordonnée des entrées (références dans la copie).
    flat = []
    for page in pages:
        for entry in (page.get("entries") or []):
            flat.append(entry)

    total = len(flat)

    for index, entry in enumerate(flat):
        decoded = entry.get("decoded")
        if not decoded or not is_sensitive_nvs_key(decoded.get("key")):
            continue
        if decoded.get("redacted"):
            continue   # déjà caviardé : ne pas ré-empreinter la valeur cachée

        span = decoded.get("span") or 1
        try:
            span = int(span)
        except (TypeError, ValueError):
            span = 1
        span = max(span, 1)

        # Empreinte sur toute la zone du blob (descripteur + slots de données).
        blob_hex = ""
        for offset in range(index, min(index + span, total)):
            slot = flat[offset].get("decoded") or {}
            blob_hex += slot.get("raw_hex") or ""

        empreinte = _fingerprint_hex(blob_hex)

        # Caviardage de la zone.
        for offset in range(index, min(index + span, total)):
            slot = flat[offset].get("decoded")
            if slot:
                if "data_hex" in slot:
                    slot["data_hex"] = REDACTED
                if "raw_hex" in slot:
                    slot["raw_hex"] = REDACTED

        decoded["redacted"] = True
        decoded["fingerprint"] = empreinte
        decoded["fingerprint_key_id"] = key_id()

    # Aucun octet brut NVS n'est conserve en base. On supprime tout dump
    # hexadecimal de TOUTES les entrees (apres calcul des empreintes ci-dessus).
    # C'est la seule facon fiable d'eliminer, en plus du mot de passe "live",
    # ses COPIES RESIDUELLES : la NVS est un journal, et d'anciennes valeurs
    # (mots de passe, SSID) subsistent dans des slots effaces/orphelins dont la
    # cle est illisible (octets de donnees lus comme une cle). La lecture live
    # sur la carte, elle, reste complete (ce caviardage ne touche que la copie
    # stockee). Perte cote base : plus de reconstruction des valeurs/SSID.
    for entry in flat:
        decoded = entry.get("decoded")
        if not isinstance(decoded, dict):
            continue
        for field in ("raw_hex", "data_hex", "key_hex"):
            if decoded.get(field) and decoded[field] != REDACTED:
                decoded[field] = REDACTED
        # Slot efface/invalide (CRC non valide) : sa "cle" est en realite des
        # octets de donnees pouvant contenir un fragment de secret -> neutralise.
        if not decoded.get("crc_match") and decoded.get("key"):
            decoded["key"] = REDACTED

    return clone


def sanitize_efuse_for_storage(result):
    """
    Copie assainie d'un résultat eFuse : les clés provisionnées (BLOCK_KEYx non
    nulles) sont caviardées et remplacées par une empreinte. Les emplacements
    vides (tout à zéro) sont conservés tels quels (aucun secret).
    """

    if not isinstance(result, dict):
        return result

    clone = copy.deepcopy(result)
    categories = clone.get("categories") or {}

    for fields in categories.values():
        for field in fields:
            name = str(field.get("name", ""))
            if not name.startswith("BLOCK_KEY"):
                continue
            if field.get("redacted"):
                continue   # déjà caviardé

            value = str(field.get("value", ""))
            digits = value.replace(" ", "").replace("0x", "").lower()
            present = digits.strip("0") != ""   # au moins un octet non nul

            if not present:
                continue   # emplacement de clé vide : rien à cacher

            raw = str(field.get("raw_value") or value)
            field["value"] = REDACTED
            field["raw_value"] = REDACTED
            field["redacted"] = True
            field["present"] = True
            field["fingerprint"] = fingerprint(raw)
            field["fingerprint_key_id"] = key_id()

    return clone
