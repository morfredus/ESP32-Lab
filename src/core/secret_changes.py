"""
Détection de changement de secrets entre deux scans d'une même carte.

Les secrets (mots de passe Wi-Fi, PMK, clés eFuse) ne sont **jamais** stockés :
seule une empreinte HMAC-SHA-256 à clé d'installation est conservée
(voir ``secret_redaction``). Ce module compare, pour une même clé (même entrée
NVS ou même bloc eFuse), l'empreinte d'un scan à celle du scan précédent, et
en déduit si le secret a changé — sans jamais connaître sa valeur.

Deux empreintes ne sont comparables que si elles ont été calculées avec la
**même clé d'installation** (``fingerprint_key_id``). Si les clés diffèrent
(scans faits sur deux postes distincts), le verdict est « indéterminable ».
"""

from core import database
from core.secret_redaction import is_sensitive_nvs_key


# Verdicts possibles pour une clé.
UNCHANGED = "unchanged"          # même empreinte, même clé d'installation
CHANGED = "changed"              # empreinte différente : le secret a changé
ADDED = "added"                  # présent seulement dans le scan récent
REMOVED = "removed"             # présent seulement dans le scan ancien
INDETERMINABLE = "indeterminable"   # empreintes non comparables (clés diff.)


def _nvs_fingerprints(payload):
    """
    Extrait les empreintes des entrées NVS sensibles d'une lecture.

    Retourne ``{identifiant: {"key", "fingerprint", "key_id"}}``.
    L'identifiant combine l'index de namespace et le nom de clé pour rester
    stable d'un scan à l'autre.
    """

    found = {}
    if not isinstance(payload, dict):
        return found

    pages = (payload.get("report") or {}).get("pages") or []
    for page in pages:
        for entry in (page.get("entries") or []):
            decoded = entry.get("decoded") or {}
            key = decoded.get("key")
            if not decoded.get("redacted") or not is_sensitive_nvs_key(key):
                continue
            fingerprint = decoded.get("fingerprint")
            if not fingerprint:
                continue
            namespace = decoded.get("namespace_index", "?")
            identifier = f"ns{namespace}/{key}"
            found[identifier] = {
                "key": key,
                "fingerprint": fingerprint,
                "key_id": decoded.get("fingerprint_key_id"),
            }

    return found


def _efuse_fingerprints(payload):
    """
    Extrait les empreintes des blocs eFuse provisionnés (BLOCK_KEYx caviardés).

    Retourne ``{nom: {"key", "fingerprint", "key_id"}}``.
    """

    found = {}
    if not isinstance(payload, dict):
        return found

    for fields in (payload.get("categories") or {}).values():
        for field in fields:
            if not field.get("redacted"):
                continue
            fingerprint = field.get("fingerprint")
            if not fingerprint:
                continue
            name = str(field.get("name", ""))
            found[name] = {
                "key": name,
                "fingerprint": fingerprint,
                "key_id": field.get("fingerprint_key_id"),
            }

    return found


def _diff_fingerprints(old, new):
    """
    Compare deux jeux d'empreintes ``{identifiant: {...}}`` (ancien vs récent)
    et renvoie la liste des changements, les changements d'abord.
    """

    changes = []
    for identifier in sorted(set(old) | set(new)):
        before = old.get(identifier)
        after = new.get(identifier)
        label = (after or before).get("key") or identifier

        if before and after:
            if before.get("key_id") != after.get("key_id"):
                status = INDETERMINABLE
            elif before["fingerprint"] == after["fingerprint"]:
                status = UNCHANGED
            else:
                status = CHANGED
        elif after:
            status = ADDED
        else:
            status = REMOVED

        changes.append({"key": label, "status": status})

    # Changements d'abord, puis par nom de clé.
    priority = {CHANGED: 0, ADDED: 1, REMOVED: 2, INDETERMINABLE: 3, UNCHANGED: 4}
    changes.sort(key=lambda item: (priority.get(item["status"], 9), item["key"]))
    return changes


def _summarize(changes):
    summary = {CHANGED: 0, ADDED: 0, REMOVED: 0, INDETERMINABLE: 0, UNCHANGED: 0}
    for change in changes:
        summary[change["status"]] = summary.get(change["status"], 0) + 1
    return summary


_EXTRACTORS = {
    "nvs": _nvs_fingerprints,
    "efuse": _efuse_fingerprints,
}

_SECTION_LABELS = {
    "nvs": "NVS (Wi-Fi, secrets)",
    "efuse": "eFuses (clés provisionnées)",
}


def _section_report(mac, section):
    """Compare les deux lectures les plus récentes d'une section."""

    readings = database.get_readings(mac, section)   # triées : récent d'abord
    report = {
        "section": section,
        "label": _SECTION_LABELS.get(section, section),
        "scans": len(readings),
    }

    if len(readings) < 2:
        report["available"] = False
        report["message"] = (
            "Au moins deux analyses sont nécessaires pour détecter un "
            "changement."
        )
        report["changes"] = []
        report["summary"] = _summarize([])
        return report

    extract = _EXTRACTORS[section]
    new_reading, old_reading = readings[0], readings[1]
    changes = _diff_fingerprints(
        extract(old_reading["payload"]),
        extract(new_reading["payload"]),
    )

    report["available"] = True
    report["old"] = {"recorded_at": old_reading["recorded_at"]}
    report["new"] = {"recorded_at": new_reading["recorded_at"]}
    report["changes"] = changes
    report["summary"] = _summarize(changes)
    return report


def detect_changes(mac):
    """
    Détecte les changements de secrets d'une carte entre ses deux scans les
    plus récents, section par section (NVS, eFuses).
    """

    if not mac:
        return {"status": "error", "message": "Une adresse MAC est requise."}

    device = database.get_device(mac)
    if not device:
        return {"status": "error", "message": "Carte introuvable."}

    sections = [_section_report(mac, section) for section in _EXTRACTORS]

    totals = {CHANGED: 0, ADDED: 0, REMOVED: 0, INDETERMINABLE: 0}
    for report in sections:
        for status in totals:
            totals[status] += report["summary"].get(status, 0)

    return {
        "status": "ok",
        "mac": device["mac"],
        "name": device.get("name") or device["mac"],
        "sections": sections,
        "totals": totals,
    }
