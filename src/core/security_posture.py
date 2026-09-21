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


def _item(item_id, label, status, state_on, state_off,
          on_summary, off_summary, advice):
    """
    Construit un item. ``state`` decrit l'etat REEL en clair (pas de double
    negation) : la protection est nommee neutrement (« USB-JTAG ») et l'etat dit
    ce qui est vrai (« Accessible » ou « Desactive (bloque) »). ``ok`` si
    protege, ``info`` sinon (jamais alarmiste).
    """

    return {
        "id": item_id,
        "label": label,
        "status": bool(status),
        "level": "ok" if status else "info",
        "state": state_on if status else state_off,
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
            "Actif", "Desactive",
            "Le firmware est verifie (signature) au demarrage.",
            "Le firmware n'est pas verifie (normal en developpement).",
            "En production, l'activer empeche l'execution d'un firmware non "
            "signe. Operation irreversible.",
        ),
        _item(
            "flash_encryption", "Chiffrement Flash", flash_encryption,
            "Actif", "Desactive",
            "Le contenu de la Flash est chiffre.",
            "Le contenu de la Flash est en clair (normal en developpement).",
            "En production, protege le firmware et les donnees contre la "
            "lecture. Irreversible.",
        ),
        _item(
            "usb_jtag", "USB-JTAG",
            security.get("usb_jtag_disabled"),
            "Desactive (bloque)", "Accessible",
            "Le debogage materiel USB-JTAG est bloque.",
            "Le debogage materiel USB-JTAG est accessible (pratique en dev).",
            "A desactiver en production pour limiter le debogage materiel.",
        ),
        _item(
            "download_mode", "Mode telechargement",
            security.get("download_mode_disabled"),
            "Desactive (bloque)", "Accessible",
            "Le reflashage par mode download est bloque.",
            "Le reflashage par mode download est accessible (normal).",
            "A envisager en production pour empecher le reflashage.",
        ),
        _item(
            "secure_download", "Telechargement securise",
            security.get("secure_download"),
            "Actif", "Non actif",
            "Le mode download est restreint (UART securise).",
            "Le mode download n'est pas restreint.",
            "Alternative moins stricte que la desactivation complete du mode "
            "download.",
        ),
        _item(
            "anti_rollback", "Anti-rollback", secure_version > 0,
            f"Compteur a {secure_version}", "Non configure",
            f"Compteur anti-rollback a {secure_version}.",
            "Anti-rollback non utilise (compteur a 0).",
            "Empeche de revenir a une version de firmware plus ancienne "
            "(necessite Secure Boot).",
        ),
        _item(
            "keys_provisioned", "Cles provisionnees", len(keys_used) > 0,
            f"{len(keys_used)} cle(s)", "Aucune",
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
