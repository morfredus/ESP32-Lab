"""
Tests des profils de cartes (exposition GPIO reelle).

Lit le catalogue cure livre (`reference/espressif/boards.json`) sans ecrire dans
le cache `data/`.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core import espressif_dataset
from core.esp32_gpio import compute_gpio_map


@pytest.fixture(autouse=True)
def use_reference_dataset(monkeypatch):
    monkeypatch.setattr(
        espressif_dataset, "CACHE_DIR", espressif_dataset.REFERENCE_DIR
    )


def _pins(report):
    return {pin["gpio"]: pin for pin in report["pins"]}


def test_boards_for_family_filtre():
    s3 = {b["id"] for b in espressif_dataset.boards_for_family("esp32s3")}
    c3 = {b["id"] for b in espressif_dataset.boards_for_family("esp32c3")}

    assert "esp32-s3-devkitc-1-v1.0" in s3
    assert "seeed-xiao-esp32s3" in s3
    assert "esp32-c3-devkitm-1" in c3
    # Pas de melange entre familles.
    assert not (s3 & c3)


def test_get_board_inconnu():
    assert espressif_dataset.get_board("carte-inexistante") is None


def test_devkit_onboard_annotations():
    report = compute_gpio_map("esp32s3", board="esp32-s3-devkitc-1-v1.0")
    assert report["board_exposure"]["name"] == "ESP32-S3-DevKitC-1 (v1.0)"

    pins = _pins(report)
    assert pins[0]["board"]["role"] == "button"
    assert pins[48]["board"]["role"] == "led"
    assert pins[19]["board"]["role"] == "usb"
    # Broche coeur Flash/PSRAM : non exposee sur les connecteurs.
    assert pins[26]["board"]["exposure"] == "not_exposed"
    # Broche generale sortie sur connecteur.
    assert pins[10]["board"]["exposure"] == "header"


def test_devkit_revision_led_differente():
    v10 = _pins(compute_gpio_map("esp32s3", board="esp32-s3-devkitc-1-v1.0"))
    v11 = _pins(compute_gpio_map("esp32s3", board="esp32-s3-devkitc-1-v1.1"))
    assert v10[48]["board"]["role"] == "led"
    assert v11[38]["board"]["role"] == "led"
    # Sur la v1.1, GPIO48 n'est plus la LED.
    assert v11[48]["board"]["exposure"] != "onboard"


def test_xiao_liste_blanche_exposed():
    pins = _pins(compute_gpio_map("esp32s3", board="seeed-xiao-esp32s3"))
    # Broche sortie sur un pad.
    assert pins[1]["board"]["exposure"] == "header"
    # LED utilisateur embarquee.
    assert pins[21]["board"]["role"] == "led"
    # Broche non sortie sur cette petite carte.
    assert pins[10]["board"]["exposure"] == "not_exposed"


def test_board_mauvaise_famille_ignore():
    report = compute_gpio_map("esp32s3", board="esp32-c3-devkitm-1")
    assert report["board_exposure"] == "unknown"
    assert "board" not in report["pins"][0]


def test_sans_board_reste_inconnu():
    report = compute_gpio_map("esp32s3")
    assert report["board_exposure"] == "unknown"
    assert "board" not in report["pins"][0]


def test_garde_fou_octal_detecte_profil_quad():
    # PSRAM Octal detectee (8 Mo) mais profil exposant GPIO33-37 : alerte.
    report = compute_gpio_map(
        "esp32s3", board="esp32-s3-supermini-n4r2", psram_size=8)
    assert report["board_exposure"]["warning"]
    assert "33" in report["board_exposure"]["warning"]


def test_garde_fou_pas_d_alerte_si_quad():
    report = compute_gpio_map(
        "esp32s3", board="esp32-s3-supermini-n4r2", psram_size=2)
    assert report["board_exposure"]["warning"] is None


def test_garde_fou_pas_d_alerte_si_profil_octal():
    # Profil Octal (33-37 deja non exposes) + PSRAM Octal : coherent, pas d'alerte.
    report = compute_gpio_map(
        "esp32s3", board="upesy-esp32-s3-n16r8", psram_size=8)
    assert report["board_exposure"]["warning"] is None
