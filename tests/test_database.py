"""
Tests de la base SQLite et du moteur de comparaison inter-cartes.

Chaque test s'exécute sur une base temporaire isolée.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core import comparison, database


def _fresh_db():
    """Redirige la base vers un fichier temporaire vierge."""

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    database.DB_PATH = Path(tmp.name)
    database._schema_ready = False
    # Recrée le schéma sur la nouvelle base.
    with database.connect():
        pass
    return Path(tmp.name)


def _inventory(mac, chip, flash_mb, when):
    return {
        "timestamp": when,
        "port": "COM_TEST",
        "identification": {
            "mac": mac,
            "chip": chip,
            "flash_size_mb": flash_mb,
            "cpu_frequency_mhz": 240,
        },
    }


def test_save_and_read_inventory():
    _fresh_db()
    database.save_reading(
        "AA:BB:CC:DD:EE:01", "inventory",
        _inventory("aa:bb:cc:dd:ee:01", "ESP32-S3", 16, "2026-01-01T00:00:00"),
        port="COM_TEST",
    )

    last = database.get_last_inventory()
    assert last["identification"]["chip"] == "ESP32-S3"
    assert len(database.get_inventory_history()) == 1

    devices = database.get_devices()
    assert "aa:bb:cc:dd:ee:01" in devices


def test_update_device_metadata():
    _fresh_db()
    database.save_reading(
        "aa:bb:cc:dd:ee:02", "inventory",
        _inventory("aa:bb:cc:dd:ee:02", "ESP32-C3", 4, "2026-01-02T00:00:00"),
    )
    database.update_device("aa:bb:cc:dd:ee:02", name="Capteur", location="Atelier")

    device = database.get_device("aa:bb:cc:dd:ee:02")
    assert device["name"] == "Capteur"
    assert device["location"] == "Atelier"


def test_dossier_sections():
    _fresh_db()
    mac = "aa:bb:cc:dd:ee:03"
    database.save_reading(mac, "inventory",
                          _inventory(mac, "ESP32-S3", 16, "2026-01-03T00:00:00"))
    database.save_reading(mac, "efuse", {"status": "ok", "security": {}})

    dossier = database.get_device_dossier(mac)
    assert set(dossier["captured"].keys()) == {"inventory", "efuse"}
    assert dossier["counts"]["inventory"] == 1


def test_compare_two_cards():
    _fresh_db()
    database.save_reading(
        "aa:bb:cc:dd:ee:10", "inventory",
        _inventory("aa:bb:cc:dd:ee:10", "ESP32-S3", 16, "2026-01-04T00:00:00"))
    database.update_device("aa:bb:cc:dd:ee:10", name="Carte 16 Mo")

    database.save_reading(
        "aa:bb:cc:dd:ee:11", "inventory",
        _inventory("aa:bb:cc:dd:ee:11", "ESP32-S3", 4, "2026-01-04T00:00:00"))
    database.update_device("aa:bb:cc:dd:ee:11", name="Carte 4 Mo")

    result = comparison.compare_devices("aa:bb:cc:dd:ee:10", "aa:bb:cc:dd:ee:11")
    assert result["status"] == "ok"
    assert result["a"]["name"] == "Carte 16 Mo"

    identity = next(g for g in result["groups"] if g["title"] == "Identité")
    labels = {row["label"]: row for row in identity["rows"]}
    assert labels["Puce"]["same"] is True          # même puce
    assert labels["Flash (Mo)"]["same"] is False    # tailles différentes
    assert result["summary"]["different"] >= 1


def test_migration_is_noop_without_json(tmp_path=None):
    _fresh_db()
    # Base vierge : init_db ne doit pas planter même sans JSON.
    database.init_db()
    assert isinstance(database.get_devices(), dict)


def test_export_import_roundtrip():
    _fresh_db()
    mac = "aa:bb:cc:dd:ee:20"
    database.save_reading(mac, "inventory",
                          _inventory(mac, "ESP32-S3", 16, "2026-02-01T00:00:00"))
    database.save_reading(mac, "efuse", {"status": "ok", "security": {}})
    database.update_device(mac, name="Poste 1")

    export = database.export_all()
    assert export["format"] == "esp32lab-export"
    assert len(export["devices"]) == 1
    assert len(export["readings"]) == 2

    # Import sur une base vierge → tout est restauré.
    _fresh_db()
    summary = database.import_data(export)
    assert summary["devices_added"] == 1
    assert summary["readings_added"] == 2
    assert database.get_device(mac)["name"] == "Poste 1"

    # Réimport → aucun doublon (idempotent).
    summary2 = database.import_data(export)
    assert summary2["devices_added"] == 0
    assert summary2["readings_added"] == 0


def test_import_rejects_bad_format():
    _fresh_db()
    try:
        database.import_data({"not": "an export"})
        assert False, "aurait dû lever ValueError"
    except ValueError:
        pass


def test_reset_and_no_remigration():
    _fresh_db()
    database.set_meta("json_migrated", "1")  # migration réputée faite
    mac = "aa:bb:cc:dd:ee:30"
    database.save_reading(mac, "inventory",
                          _inventory(mac, "ESP32-S3", 16, "2026-03-01T00:00:00"))
    assert len(database.get_devices()) == 1

    database.reset_database()
    assert len(database.get_devices()) == 0
    assert len(database.get_inventory_history()) == 0

    # Le marqueur empêche toute réimportation des anciens JSON.
    database.init_db()
    assert len(database.get_devices()) == 0


def test_get_latest_reading():
    _fresh_db()
    mac = "aa:bb:cc:dd:ee:40"
    database.save_reading(mac, "nvs", {"status": "ok", "report": {"tag": "vieux"}},
                          recorded_at="2026-01-01T00:00:00")
    database.save_reading(mac, "nvs", {"status": "ok", "report": {"tag": "recent"}},
                          recorded_at="2026-02-01T00:00:00")

    latest = database.get_latest_reading(mac, "nvs")
    assert latest is not None
    assert latest["payload"]["report"]["tag"] == "recent"

    # Section absente → None.
    assert database.get_latest_reading(mac, "efuse") is None


def test_verify_database():
    _fresh_db()
    database.set_meta("json_migrated", "1")
    mac = "aa:bb:cc:dd:ee:31"
    database.save_reading(mac, "inventory",
                          _inventory(mac, "ESP32-S3", 16, "2026-03-02T00:00:00"))
    database.save_reading(mac, "efuse", {"status": "ok"})

    report = database.verify_database()
    assert report["healthy"] is True
    assert report["devices"] == 1
    assert report["readings_by_section"]["inventory"] == 1
    assert report["readings_total"] == 2


if __name__ == "__main__":
    test_save_and_read_inventory()
    test_update_device_metadata()
    test_dossier_sections()
    test_compare_two_cards()
    test_migration_is_noop_without_json()
    test_export_import_roundtrip()
    test_import_rejects_bad_format()
    test_reset_and_no_remigration()
    test_get_latest_reading()
    test_verify_database()
    print("Tous les tests de base de données sont réussis.")
