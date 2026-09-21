"""
Tests de la rédaction des secrets avant stockage.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core import install_key
from core.secret_redaction import (
    REDACTED,
    is_sensitive_nvs_key,
    sanitize_efuse_for_storage,
    sanitize_nvs_for_storage,
)

# Clé fixe pour des empreintes déterministes (évite d'écrire un fichier clé).
install_key._cached_key = b"0123456789abcdef0123456789abcdef"


def _nvs_report():
    return {
        "status": "ok",
        "report": {
            "pages": [
                {"entries": [
                    {"index": 0, "decoded": {
                        "key": "sta.ssid", "data_hex": "aa",
                        "raw_hex": "1111", "span": 1, "crc_match": True}},
                    {"index": 1, "decoded": {
                        "key": "sta.pswd", "data_hex": "2400ffff",
                        "raw_hex": "dead", "span": 2, "crc_match": True}},
                    {"index": 2, "decoded": {
                        "key": "un1frgrv", "data_hex": "cafe",
                        "raw_hex": "beef", "crc_match": False}},
                ]},
            ],
        },
    }


def test_sensitive_key_detection():
    assert is_sensitive_nvs_key("sta.pswd")
    assert is_sensitive_nvs_key("ap.passwd")
    assert is_sensitive_nvs_key("ap.pmk_info")
    assert not is_sensitive_nvs_key("sta.ssid")
    assert not is_sensitive_nvs_key("cal_data")


def test_nvs_redaction_and_fingerprint():
    original = _nvs_report()
    clone = sanitize_nvs_for_storage(original)

    entries = clone["report"]["pages"][0]["entries"]

    # Aucun octet brut NVS n'est conservé : tout dump hex est caviardé, même
    # pour les entrées non sensibles (élimine les copies résiduelles de secrets).
    assert entries[0]["decoded"]["raw_hex"] == REDACTED
    assert entries[0]["decoded"]["data_hex"] == REDACTED
    # La clé d'une entrée valide (CRC OK) reste lisible : c'est de la structure.
    assert entries[0]["decoded"]["key"] == "sta.ssid"

    # Le mot de passe est caviardé, avec empreinte et key_id.
    pswd = entries[1]["decoded"]
    assert pswd["data_hex"] == REDACTED
    assert pswd["raw_hex"] == REDACTED
    assert pswd["redacted"] is True
    assert len(pswd["fingerprint"]) == 64        # HMAC-SHA-256 hex
    assert "fingerprint_key_id" in pswd

    # Le slot de données (CRC invalide) est caviardé, et sa « clé » (des octets
    # de secret lus comme une clé) est neutralisée.
    assert entries[2]["decoded"]["raw_hex"] == REDACTED
    assert entries[2]["decoded"]["key"] == REDACTED


def test_original_not_mutated():
    original = _nvs_report()
    sanitize_nvs_for_storage(original)
    # L'objet d'origine (affiché en direct) garde ses secrets.
    assert original["report"]["pages"][0]["entries"][1]["decoded"]["raw_hex"] == "dead"


def test_fingerprint_is_stable_and_distinct():
    a = sanitize_nvs_for_storage(_nvs_report())
    b = sanitize_nvs_for_storage(_nvs_report())
    fp_a = a["report"]["pages"][0]["entries"][1]["decoded"]["fingerprint"]
    fp_b = b["report"]["pages"][0]["entries"][1]["decoded"]["fingerprint"]
    assert fp_a == fp_b       # même secret -> même empreinte (détection stable)

    changed = _nvs_report()
    changed["report"]["pages"][0]["entries"][1]["decoded"]["raw_hex"] = "0bad"
    fp_c = sanitize_nvs_for_storage(changed)["report"]["pages"][0]["entries"][1]["decoded"]["fingerprint"]
    assert fp_c != fp_a       # secret différent -> empreinte différente


def test_sanitize_is_idempotent():
    once = sanitize_nvs_for_storage(_nvs_report())
    twice = sanitize_nvs_for_storage(once)
    d1 = once["report"]["pages"][0]["entries"][1]["decoded"]
    d2 = twice["report"]["pages"][0]["entries"][1]["decoded"]
    # Ré-assainir ne doit pas ré-empreinter la valeur déjà cachée.
    assert d1["fingerprint"] == d2["fingerprint"]
    assert d2["raw_hex"] == REDACTED


def test_efuse_redaction():
    result = {
        "status": "ok",
        "categories": {
            "security": [
                {"name": "BLOCK_KEY0", "value": "de ad be ef",
                 "raw_value": "0xdeadbeef"},
                {"name": "BLOCK_KEY1", "value": "00 00 00 00",
                 "raw_value": "0x00000000"},
                {"name": "SECURE_BOOT_EN", "value": "False"},
            ],
        },
    }
    clone = sanitize_efuse_for_storage(result)
    fields = {f["name"]: f for f in clone["categories"]["security"]}

    # Clé provisionnée -> caviardée + empreinte.
    assert fields["BLOCK_KEY0"]["value"] == REDACTED
    assert fields["BLOCK_KEY0"]["present"] is True
    assert "fingerprint" in fields["BLOCK_KEY0"]

    # Emplacement vide -> conservé tel quel.
    assert fields["BLOCK_KEY1"]["value"] == "00 00 00 00"
    assert "fingerprint" not in fields["BLOCK_KEY1"]

    # Autre champ -> intact.
    assert fields["SECURE_BOOT_EN"]["value"] == "False"


if __name__ == "__main__":
    test_sensitive_key_detection()
    test_nvs_redaction_and_fingerprint()
    test_original_not_mutated()
    test_fingerprint_is_stable_and_distinct()
    test_sanitize_is_idempotent()
    test_efuse_redaction()
    print("Tous les tests de rédaction des secrets sont réussis.")
