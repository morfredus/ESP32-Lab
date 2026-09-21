"""
Tests du bilan de securite (posture eFuse -> checklist).

Verifie le ton non alarmiste (jamais de niveau d'alerte pour une carte de
developpement) et le calcul de la posture globale.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.security_posture import assess_security


def _item(assessment, item_id):
    return next(it for it in assessment["items"] if it["id"] == item_id)


def test_tout_desactive_posture_developpement():
    result = assess_security({
        "secure_boot": False, "flash_encryption": False,
        "secure_version": 0, "keys_used": [],
    })
    assert result["posture"] == "development"
    assert result["activated"] == 0
    # Ton non alarmiste : aucun item en niveau d'alerte.
    assert all(it["level"] in {"ok", "info"} for it in result["items"])
    assert all(it["level"] == "info" for it in result["items"])
    # Chaque item porte un conseil.
    assert all(it["advice"] for it in result["items"])


def test_secure_boot_et_chiffrement_durcie():
    result = assess_security({
        "secure_boot": True, "flash_encryption": True,
        "secure_version": 0, "keys_used": [],
    })
    assert result["posture"] == "hardened"
    assert _item(result, "secure_boot")["level"] == "ok"
    assert _item(result, "flash_encryption")["status"] is True


def test_un_seul_durcissement_partiel():
    assert assess_security({"secure_boot": True})["posture"] == "partial"
    assert assess_security({"flash_encryption": True})["posture"] == "partial"


def test_anti_rollback_actif_si_version_positive():
    on = assess_security({"secure_version": 3})
    assert _item(on, "anti_rollback")["status"] is True
    assert "3" in _item(on, "anti_rollback")["summary"]

    off = assess_security({"secure_version": 0})
    assert _item(off, "anti_rollback")["status"] is False


def test_cles_provisionnees():
    result = assess_security({"keys_used": [{"slot": 0}, {"slot": 1}]})
    assert _item(result, "keys_provisioned")["status"] is True


def test_etats_directs_sans_double_negation():
    # Tout desactive : chaque etat decrit la realite en clair (pas de « non actif »
    # ambigu pour USB-JTAG / mode download).
    states = {it["id"]: it["state"] for it in assess_security({})["items"]}
    assert states["secure_boot"] == "Desactive"
    assert states["flash_encryption"] == "Desactive"
    assert states["usb_jtag"] == "Accessible"
    assert states["download_mode"] == "Accessible"
    assert states["anti_rollback"] == "Non configure"

    on = assess_security({"secure_boot": True, "usb_jtag_disabled": True})
    on_states = {it["id"]: it["state"] for it in on["items"]}
    assert on_states["secure_boot"] == "Actif"
    assert "bloque" in on_states["usb_jtag"].lower()


def test_entree_vide_ne_plante_pas():
    result = assess_security(None)
    assert result["posture"] == "development"
    assert result["total"] == 7
