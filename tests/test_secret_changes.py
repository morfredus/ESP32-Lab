"""
Tests de la détection de changement de secrets (empreintes HMAC).

Vérifie que la comparaison d'empreintes distingue correctement : inchangé,
changé, nouveau, disparu et indéterminable (clés d'installation différentes).
Aucun secret n'intervient : on ne manipule que des empreintes.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core import secret_changes
from core.secret_changes import (
    ADDED,
    CHANGED,
    INDETERMINABLE,
    REMOVED,
    UNCHANGED,
    _diff_fingerprints,
    _efuse_fingerprints,
    _nvs_fingerprints,
    detect_changes,
)


def _fp(fingerprint, key="sta.pswd", key_id="k1"):
    return {"key": key, "fingerprint": fingerprint, "key_id": key_id}


def _status(changes, key):
    for change in changes:
        if change["key"] == key:
            return change["status"]
    return None


def test_diff_detects_unchanged_and_changed():
    old = {"ns1/sta.pswd": _fp("AAAA")}
    new = {"ns1/sta.pswd": _fp("AAAA")}
    assert _status(_diff_fingerprints(old, new), "sta.pswd") == UNCHANGED

    new_changed = {"ns1/sta.pswd": _fp("BBBB")}
    assert _status(_diff_fingerprints(old, new_changed), "sta.pswd") == CHANGED


def test_diff_detects_added_and_removed():
    old = {}
    new = {"ns1/sta.pswd": _fp("AAAA")}
    assert _status(_diff_fingerprints(old, new), "sta.pswd") == ADDED
    assert _status(_diff_fingerprints(new, old), "sta.pswd") == REMOVED


def test_diff_indeterminable_when_key_ids_differ():
    old = {"ns1/sta.pswd": _fp("AAAA", key_id="poste-A")}
    new = {"ns1/sta.pswd": _fp("BBBB", key_id="poste-B")}
    # Empreintes différentes mais clés d'installation différentes : on ne peut
    # pas conclure à un changement.
    assert _status(_diff_fingerprints(old, new), "sta.pswd") == INDETERMINABLE


def test_diff_orders_changes_first():
    old = {"ns1/a.pswd": _fp("AAAA", key="a.pswd"),
           "ns1/b.pswd": _fp("BBBB", key="b.pswd")}
    new = {"ns1/a.pswd": _fp("AAAA", key="a.pswd"),
           "ns1/b.pswd": _fp("CCCC", key="b.pswd")}
    changes = _diff_fingerprints(old, new)
    # Le secret changé passe avant l'inchangé.
    assert changes[0]["status"] == CHANGED
    assert changes[0]["key"] == "b.pswd"


def test_nvs_fingerprints_only_redacted_sensitive():
    payload = {"report": {"pages": [{"entries": [
        {"decoded": {"key": "sta.ssid", "redacted": False}},
        {"decoded": {"key": "sta.pswd", "redacted": True,
                     "fingerprint": "F1", "fingerprint_key_id": "k1",
                     "namespace_index": 3}},
    ]}]}}
    found = _nvs_fingerprints(payload)
    assert list(found) == ["ns3/sta.pswd"]
    assert found["ns3/sta.pswd"]["fingerprint"] == "F1"
    assert found["ns3/sta.pswd"]["key_id"] == "k1"


def test_efuse_fingerprints_only_redacted():
    payload = {"categories": {"Clés": [
        {"name": "BLOCK_KEY0", "redacted": True,
         "fingerprint": "E1", "fingerprint_key_id": "k1"},
        {"name": "BLOCK_KEY1"},   # emplacement vide, non caviardé
    ]}}
    found = _efuse_fingerprints(payload)
    assert list(found) == ["BLOCK_KEY0"]
    assert found["BLOCK_KEY0"]["fingerprint"] == "E1"


def test_detect_changes_needs_two_scans(monkeypatch):
    monkeypatch.setattr(secret_changes.database, "get_device",
                        lambda mac: {"mac": mac, "name": "Test"})
    monkeypatch.setattr(secret_changes.database, "get_readings",
                        lambda mac, section: [])   # aucune lecture

    result = detect_changes("aa:bb")
    assert result["status"] == "ok"
    for section in result["sections"]:
        assert section["available"] is False


def test_detect_changes_reports_a_change(monkeypatch):
    nvs_new = {"payload": {"report": {"pages": [{"entries": [
        {"decoded": {"key": "sta.pswd", "redacted": True,
                     "fingerprint": "NEW", "fingerprint_key_id": "k1",
                     "namespace_index": 1}}]}]}},
        "recorded_at": "2026-09-21T10:00:00Z"}
    nvs_old = {"payload": {"report": {"pages": [{"entries": [
        {"decoded": {"key": "sta.pswd", "redacted": True,
                     "fingerprint": "OLD", "fingerprint_key_id": "k1",
                     "namespace_index": 1}}]}]}},
        "recorded_at": "2026-09-20T10:00:00Z"}

    def fake_readings(mac, section):
        return [nvs_new, nvs_old] if section == "nvs" else []

    monkeypatch.setattr(secret_changes.database, "get_device",
                        lambda mac: {"mac": mac, "name": "Test"})
    monkeypatch.setattr(secret_changes.database, "get_readings",
                        fake_readings)

    result = detect_changes("aa:bb")
    assert result["totals"][CHANGED] == 1
    nvs_section = next(s for s in result["sections"] if s["section"] == "nvs")
    assert _status(nvs_section["changes"], "sta.pswd") == CHANGED
