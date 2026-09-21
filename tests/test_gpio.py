"""
Tests de la cartographie GPIO (calcul niveau puce, data-driven).

Les tests lisent le jeu de references cure livre avec l'application
(``reference/espressif/``), sans ecrire dans le cache ``data/``.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core import espressif_dataset
from core.esp32_gpio import compute_gpio_map


@pytest.fixture(autouse=True)
def use_reference_dataset(monkeypatch):
    """Lit directement le jeu cure livre (aucune ecriture)."""

    monkeypatch.setattr(
        espressif_dataset, "CACHE_DIR", espressif_dataset.REFERENCE_DIR
    )


def _pins(report):
    return {pin["gpio"]: pin for pin in report["pins"]}


def test_counts_par_famille():
    assert compute_gpio_map("esp32s3")["gpio_count"] == 45
    assert compute_gpio_map("esp32c3")["gpio_count"] == 22
    assert compute_gpio_map("esp32")["gpio_count"] == 34


def test_s3_absence_22_a_25():
    pins = _pins(compute_gpio_map("esp32s3"))
    for gpio in (22, 23, 24, 25):
        assert gpio not in pins


def test_esp32_broches_absentes():
    pins = _pins(compute_gpio_map("esp32"))
    for gpio in (20, 24, 28, 29, 30, 31):
        assert gpio not in pins


def test_strapping_par_famille():
    def strap(fam):
        return sorted(p["gpio"] for p in compute_gpio_map(fam)["pins"]
                      if p["strapping"])

    assert strap("esp32") == [0, 2, 5, 12, 15]
    assert strap("esp32s3") == [0, 3, 45, 46]
    assert strap("esp32c3") == [2, 8, 9]


def test_entree_seule_esp32():
    pins = _pins(compute_gpio_map("esp32"))
    input_only = sorted(g for g, p in pins.items() if p["input_only"])
    assert input_only == [34, 35, 36, 37, 38, 39]
    # Les autres familles n'ont pas de broche en entree seule.
    assert not any(p["input_only"] for p in compute_gpio_map("esp32s3")["pins"])


def test_flash_psram_a_eviter():
    pins = _pins(compute_gpio_map("esp32"))
    avoid = sorted(g for g, p in pins.items() if p["status"] == "avoid")
    assert avoid == [6, 7, 8, 9, 10, 11, 16, 17]


def test_adc_mapping():
    s3 = _pins(compute_gpio_map("esp32s3"))
    assert s3[1]["adc"] == "ADC1_CH0"
    assert s3[11]["adc"] == "ADC2_CH0"

    e = _pins(compute_gpio_map("esp32"))
    assert e[36]["adc"] == "ADC1_CH0"
    assert e[4]["adc"] == "ADC2_CH0"


def test_classification_statuts():
    s3 = _pins(compute_gpio_map("esp32s3"))
    # Coeur Flash/PSRAM : a eviter.
    assert s3[26]["status"] == "avoid"
    # Strapping : disponible avec restrictions.
    assert s3[0]["status"] == "restricted"
    # Broche generale : disponible.
    assert s3[10]["status"] == "available"


def test_octal_conditionnel_s3():
    s3 = _pins(compute_gpio_map("esp32s3"))
    assert s3[33]["status"] == "restricted"
    assert "Octal" in s3[33]["classification"]


def test_usb_jtag_restreint():
    s3 = _pins(compute_gpio_map("esp32s3"))
    assert s3[19]["usb_jtag"] is True
    assert s3[19]["status"] == "restricted"


def test_famille_non_couverte():
    # esp32p4 n'a pas (encore) de profil GPIO dans la base.
    report = compute_gpio_map("esp32p4")
    assert report["status"] == "ok"
    assert report["family_supported"] is False
    assert report["pins"] == []


def test_chip_vide_erreur():
    report = compute_gpio_map("")
    assert report["status"] == "error"


def test_familles_supplementaires():
    assert compute_gpio_map("esp32c6")["gpio_count"] == 31
    assert compute_gpio_map("esp32s2")["gpio_count"] == 43
    assert compute_gpio_map("esp32h2")["gpio_count"] == 28

    def strap(fam):
        return sorted(p["gpio"] for p in compute_gpio_map(fam)["pins"]
                      if p["strapping"])

    assert strap("esp32c6") == [4, 5, 8, 9, 15]
    assert strap("esp32s2") == [0, 45, 46]
    assert strap("esp32h2") == [2, 3, 8, 9, 25]

    # ESP32-S2 : entree seule GPIO46, DAC 17/18.
    s2 = _pins(compute_gpio_map("esp32s2"))
    assert s2[46]["input_only"] is True
    assert s2[17]["dac"] is True
    assert s2[18]["dac"] is True


def test_boot_caveat_sur_strapping():
    s3 = _pins(compute_gpio_map("esp32s3"))
    assert s3[0]["boot_caveat"]
    assert s3[10]["boot_caveat"] is None
