"""
Tests de l'import (complétion des noms) et de la suppression d'une carte.

Chaque test tourne sur une base SQLite temporaire isolée, pour ne jamais
toucher la vraie base du projet.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import core.database as database


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Réoriente la base vers un dossier temporaire, schéma neuf."""

    monkeypatch.setattr(database, "DATA_DIR", tmp_path)
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(database, "_schema_ready", False)
    return database


def _export(devices, readings=None):
    return {
        "format": "esp32lab-export",
        "version": 1,
        "devices": devices,
        "readings": readings or [],
    }


def test_import_fills_name_of_empty_device(db):
    # Carte créée vide par un scan (nom vide).
    db.save_reading("aa:bb:cc:dd:ee:ff", "inventory",
                    {"identification": {"mac": "aa:bb:cc:dd:ee:ff"}})
    assert db.get_device("aa:bb:cc:dd:ee:ff")["name"] == ""

    summary = db.import_data(_export([
        {"mac": "aa:bb:cc:dd:ee:ff", "name": "Carte Salon",
         "location": "Bureau", "note": ""},
    ]))

    assert summary["devices_updated"] == 1
    device = db.get_device("aa:bb:cc:dd:ee:ff")
    assert device["name"] == "Carte Salon"
    assert device["location"] == "Bureau"


def test_import_adds_new_device(db):
    summary = db.import_data(_export([
        {"mac": "11:22:33:44:55:66", "name": "Nouvelle",
         "location": "", "note": ""},
    ]))
    assert summary["devices_added"] == 1
    assert db.get_device("11:22:33:44:55:66")["name"] == "Nouvelle"


def test_import_never_overwrites_local_name(db):
    db.update_device("aa:bb:cc:dd:ee:ff", name="Nom Local")
    db.import_data(_export([
        {"mac": "aa:bb:cc:dd:ee:ff", "name": "Autre", "location": "",
         "note": ""},
    ]))
    assert db.get_device("aa:bb:cc:dd:ee:ff")["name"] == "Nom Local"


def test_delete_device_removes_device_and_readings(db):
    db.save_reading("aa:bb:cc:dd:ee:ff", "inventory",
                    {"identification": {"mac": "aa:bb:cc:dd:ee:ff"}})
    db.save_reading("aa:bb:cc:dd:ee:ff", "efuse", {"categories": {}})

    result = db.delete_device("aa:bb:cc:dd:ee:ff")
    assert result["status"] == "ok"
    assert result["readings_deleted"] == 2
    assert db.get_device("aa:bb:cc:dd:ee:ff") is None
    assert db.get_readings("aa:bb:cc:dd:ee:ff") == []


def test_delete_missing_device_returns_none(db):
    assert db.delete_device("00:00:00:00:00:00") is None
