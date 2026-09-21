"""
Bilan de securite d'un ESP32, a partir de la posture eFuse.

Transforme les indicateurs bruts (`build_security_posture` dans
``esp32_efuse.py``) en une checklist honnete et pedagogique : chaque protection
est expliquee, avec un conseil « en production ». Le ton est **non alarmiste** :
sur une carte de developpement, une protection desactivee est NORMALE (niveau
``info``, jamais une alerte). La posture globale resume l'ensemble.
"""


POSTURE_LABELS = {
    "development": "Developpement",
    "partial": "Durcissement partiel",
    "hardened": "Durcie",
}


def _item(item_id, label, status, on_summary, off_summary, advice):
    """Construit un item : ``ok`` si active, ``info`` sinon (jamais alarmiste)."""

    return {
        "id": item_id,
        "label": label,
        "status": bool(status),
        "level": "ok" if status else "info",
        "summary": on_summary if status else off_summary,
        "advice": advice,
    }


def assess_security(security):
    """
    Retourne le bilan de securite (items + posture globale) a partir du dict
    ``security`` produit par ``esp32_efuse.build_security_posture``.
    """

    security = security or {}

    secure_boot = bool(security.get("secure_boot"))
    flash_encryption = bool(security.get("flash_encryption"))
    secure_version = security.get("secure_version") or 0
    try:
        secure_version = int(secure_version)
    except (TypeError, ValueError):
        secure_version = 0
    keys_used = security.get("keys_used") or []

    items = [
        _item(
            "secure_boot", "Secure Boot", secure_boot,
            "Le firmware est verifie (signature) au demarrage.",
            "Non active (normal en developpement).",
            "En production, l'activer empeche l'execution d'un firmware non "
            "signe. Operation irreversible.",
        ),
        _item(
            "flash_encryption", "Chiffrement Flash", flash_encryption,
            "Le contenu de la Flash est chiffre.",
            "Non active (normal en developpement).",
            "En production, protege le firmware et les donnees contre la "
            "lecture. Irreversible.",
        ),
        _item(
            "usb_jtag_disabled", "USB-JTAG desactive",
            security.get("usb_jtag_disabled"),
            "Le debogage materiel USB-JTAG est bloque.",
            "USB-JTAG accessible (pratique en developpement).",
            "A desactiver en production pour limiter le debogage materiel.",
        ),
        _item(
            "download_mode_disabled", "Mode telechargement desactive",
            security.get("download_mode_disabled"),
            "Le reflashage par mode download est bloque.",
            "Mode download accessible (normal).",
            "A envisager en production pour empecher le reflashage.",
        ),
        _item(
            "secure_download", "Telechargement securise",
            security.get("secure_download"),
            "Le mode download est restreint (UART securise).",
            "Mode download non restreint.",
            "Alternative moins stricte que la desactivation complete du mode "
            "download.",
        ),
        _item(
            "anti_rollback", "Anti-rollback", secure_version > 0,
            f"Compteur anti-rollback a {secure_version}.",
            "Anti-rollback non utilise (compteur a 0).",
            "Empeche de revenir a une version de firmware plus ancienne "
            "(necessite Secure Boot).",
        ),
        _item(
            "keys_provisioned", "Cles provisionnees", len(keys_used) > 0,
            f"{len(keys_used)} emplacement(s) de cles utilise(s).",
            "Aucune cle provisionnee.",
            "Les cles servent au Secure Boot et au chiffrement Flash.",
        ),
    ]

    if secure_boot and flash_encryption:
        posture = "hardened"
    elif secure_boot or flash_encryption:
        posture = "partial"
    else:
        posture = "development"

    activated = sum(1 for entry in items if entry["status"])

    return {
        "items": items,
        "posture": posture,
        "posture_label": POSTURE_LABELS[posture],
        "activated": activated,
        "total": len(items),
    }
