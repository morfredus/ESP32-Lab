"""
Tests de la base de references Espressif locale (offline-first).

Verifie le seed depuis le jeu cure livre, la validation de schema, le controle
d'integrite, la sauvegarde avant remplacement et la robustesse en cas d'echec de
mise a jour (base locale conservee). Aucun acces reseau : le telechargeur est
injecte.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core import espressif_dataset


@pytest.fixture
def cache(tmp_path, monkeypatch):
    """Cache isole dans un dossier temporaire ; seed depuis le vrai reference/."""

    cache_dir = tmp_path / "espressif"
    monkeypatch.setattr(espressif_dataset, "CACHE_DIR", cache_dir)
    monkeypatch.setattr(espressif_dataset, "BACKUP_DIR", cache_dir / ".backup")
    return cache_dir


def _reference_bytes(name):
    return (espressif_dataset.REFERENCE_DIR / name).read_bytes()


def _fixture_downloader(overrides=None):
    """Telechargeur simule : renvoie le contenu du jeu cure (ou un override)."""

    overrides = overrides or {}

    def download(url):
        name = url.rsplit("/", 1)[-1]
        if name in overrides:
            value = overrides[name]
            if isinstance(value, Exception):
                raise value
            return value
        return _reference_bytes(name)

    return download


def test_seed_depuis_reference(cache):
    espressif_dataset.ensure_local_dataset()

    assert (cache / "metadata.json").exists()
    for name in espressif_dataset.DATASET_FILES:
        assert (cache / name).exists()


def test_load_family_valide(cache):
    data = espressif_dataset.load_family("esp32s3")
    assert data is not None
    assert data["family"] == "esp32s3"
    assert 46 in data["strapping"]


def test_load_family_schema_incompatible(cache):
    espressif_dataset.ensure_local_dataset()
    # Corrompt le schema du fichier en cache.
    bad = {"schema_version": 99, "family": "esp32c3", "pins_present": []}
    (cache / "esp32-c3.json").write_text(json.dumps(bad), encoding="utf-8")

    assert espressif_dataset.load_family("esp32c3") is None


def test_integrite_ok_puis_corrompue(cache):
    status = espressif_dataset.dataset_status()
    assert status["integrity_ok"] is True
    assert status["offline_available"] is True

    # Modifie un fichier : le sha256 ne correspond plus au metadata.
    (cache / "esp32.json").write_text("{}", encoding="utf-8")
    assert espressif_dataset.dataset_status()["integrity_ok"] is False


def test_refresh_succes_horodate_et_sauvegarde(cache):
    espressif_dataset.ensure_local_dataset()

    result = espressif_dataset.refresh_from_channel(
        downloader=_fixture_downloader()
    )

    assert result["status"] == "ok"
    assert result["synced_at"]
    # La sauvegarde de l'ancienne base a ete creee.
    assert (cache / ".backup" / "metadata.json").exists()
    # Le metadata en cache porte desormais une date de synchro.
    meta = json.loads((cache / "metadata.json").read_text(encoding="utf-8"))
    assert meta["synced_at"]


def test_refresh_echec_reseau_conserve_la_base(cache):
    espressif_dataset.ensure_local_dataset()
    before = (cache / "esp32.json").read_bytes()

    downloader = _fixture_downloader(
        {"metadata.json": ConnectionError("reseau indisponible")}
    )
    result = espressif_dataset.refresh_from_channel(downloader=downloader)

    assert result["status"] == "error"
    # Base locale intacte.
    assert (cache / "esp32.json").read_bytes() == before


def test_refresh_integrite_invalide_conserve_la_base(cache):
    espressif_dataset.ensure_local_dataset()
    before = (cache / "esp32-s3.json").read_bytes()

    # Le fichier telecharge ne correspond pas au sha256 declare dans le metadata.
    downloader = _fixture_downloader(
        {"esp32-s3.json": b'{"schema_version": 1, "family": "esp32s3"}'}
    )
    result = espressif_dataset.refresh_from_channel(downloader=downloader)

    assert result["status"] == "error"
    assert "sha256" in result["message"] or "Integrite" in result["message"]
    assert (cache / "esp32-s3.json").read_bytes() == before
