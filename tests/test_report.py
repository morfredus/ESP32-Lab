"""
Tests du rapport exportable (assemblage + rendu HTML autonome).

Tourne sur une base SQLite temporaire isolee.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import core.database as database
from core.report import build_report, render_report_html


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATA_DIR", tmp_path)
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(database, "_schema_ready", False)
    return database


def _seed(db, mac="aa:bb:cc:dd:ee:01"):
    db.update_device(mac, name="Carte Test", location="Atelier")
    db.update_device_from_inventory({
        "identification": {
            "mac": mac, "chip": "ESP32-S3", "chip_family": "esp32s3",
            "revision": "v0.1",
        },
        "timestamp": "2026-09-22T10:00:00+00:00",
        "port": "COM3",
    })
    db.save_reading(mac, "efuse", {
        "identity": {"revision": "v0.1"},
        "security": {
            "secure_boot": False, "flash_encryption": False,
            "secure_version": 0, "keys_used": [],
        },
    })
    db.save_reading(mac, "partitions", {"partitions": [
        {"label": "app0", "type": "app", "subtype": "ota_0",
         "offset": 0x10000, "size": 0x100000, "encrypted": False},
    ]})
    return mac


def test_build_report_assemble(db):
    mac = _seed(db)
    report = build_report(mac)

    assert report is not None
    assert report["device"]["name"] == "Carte Test"
    assert report["assessment"]["posture"] == "development"
    assert report["gpio"]["family_supported"] is True
    # Sections non capturees.
    assert report["firmware"] is None
    assert report["sfdp"] is None


def test_render_html_contenu_et_sans_secret(db):
    mac = _seed(db)
    html = render_report_html(build_report(mac))

    assert "Carte Test" in html
    assert "Developpement" in html          # posture
    assert "app0" in html                    # partition
    assert "GPIO" in html                    # cartographie
    # Aucun secret dans le rapport.
    assert "password" not in html.lower()
    assert "pswd" not in html.lower()


def test_report_carte_absente(db):
    assert build_report("00:00:00:00:00:00") is None
    assert "introuvable" in render_report_html(None).lower()
