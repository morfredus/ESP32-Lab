# Base de references GPIO Espressif

Ce dossier contient le **jeu de donnees cure** qui alimente le GPIO Inspector.
Un fichier par famille de puce, plus `metadata.json` (version + empreintes
d'integrite). Ces donnees sont livrees avec l'application et fonctionnent hors
ligne.

> Espressif ne publie pas ces informations sous une forme telechargeable prete a
> l'emploi. On les recopie donc a la main depuis deux sources officielles, puis
> on regenere `metadata.json` avec le script.

## Les deux sources officielles

Pour **chaque famille**, tout se trouve dans deux documents Espressif :

1. **Page ESP-IDF "GPIO & RTC GPIO"** de la famille (la plus pratique) :

   `https://docs.espressif.com/projects/esp-idf/en/latest/<famille>/api-reference/peripherals/gpio.html`

   Remplace `<famille>` par `esp32`, `esp32s3`, `esp32c3`, `esp32c6`...
   La section **"GPIO Summary"** y donne, en clair, presque tout ce dont on a
   besoin (broches presentes, entree seule, Flash/PSRAM, USB-JTAG, ADC).

2. **Datasheet de la famille**, chapitre **"Boot Configurations"** :
   c'est la seule source fiable pour les **broches de strapping** (la page GPIO
   renvoie a la datasheet pour ce point). Cherchez "ESP32-XX datasheet" sur
   espressif.com.

## Ou trouver chaque champ

| Champ du JSON | Ou le lire | Exemple |
|---------------|-----------|---------|
| `pins_present` | GPIO Summary : "N physical GPIO pins (GPIOx ~ GPIOy)". Notez les trous. | S3 : 0-21 et 26-48 (22-25 absents) |
| `input_only` | GPIO Summary : broches "can only be set as input mode". | ESP32 : 34-39 |
| `flash_psram` | GPIO Summary : "usually used for SPI flash and PSRAM". | C3 : 12-17 |
| `flash_psram_octal` | GPIO Summary : broches reservees **uniquement** en Flash/PSRAM Octal. | S3 : 33-37 |
| `usb_jtag` | GPIO Summary : "used by USB-JTAG by default". | C3 : 18-19 |
| `adc1` / `adc2` | GPIO Summary : canaux ADC1_CHx / ADC2_CHx. Format `{ "gpio": canal }`. | S3 : `{"1":0,"2":1,...}` |
| `dac` | GPIO Summary (uniquement l'ESP32 classique a un DAC). | ESP32 : 25, 26 |
| `strapping` | **Datasheet**, chapitre Boot Configurations. | S3 : 0, 3, 45, 46 |
| `notes` | Redige a la main d'apres ces sources (role de la broche, avertissement). | `{"0": "Strapping (mode de boot)..."}` |

Les URLs exactes deja utilisees sont conservees dans `metadata.json`
(`source_urls`) : pratique pour reverifier.

## Recette pas a pas

### Mettre a jour une famille existante
1. Ouvrez la page GPIO Summary de la famille (et la datasheet pour le strapping).
2. Corrigez le fichier concerne (ex. `esp32-s3.json`) en suivant le tableau
   ci-dessus. Respectez le schema (voir un fichier existant comme modele).
3. Regenerez les empreintes :
   ```bash
   python tools/build_espressif_metadata.py
   ```
4. Verifiez : `PYTHONPATH=src python -m pytest tests/ -q`.

### Ajouter une nouvelle famille (ex. ESP32-C6)
1. Creez `reference/espressif/esp32-c6.json` en copiant un fichier existant et
   en remplissant chaque champ depuis les deux sources.
2. **Deux lignes de code** dans `src/core/espressif_dataset.py` :
   - ajoutez `"esp32c6": "esp32-c6"` dans `_FAMILY_FILES` ;
   - ajoutez `"esp32-c6.json"` dans `DATASET_FILES`.
3. Regenerez le metadata puis lancez les tests (voir ci-dessus).

## Schema d'un fichier de famille

```json
{
    "schema_version": 1,
    "family": "esp32s3",
    "label": "ESP32-S3",
    "pins_present": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, ...],
    "strapping": [0, 3, 45, 46],
    "input_only": [],
    "flash_psram": [26, 27, 28, 29, 30, 31, 32],
    "flash_psram_octal": [33, 34, 35, 36, 37],
    "usb_jtag": [19, 20],
    "adc1": {"1": 0, "2": 1, "3": 2},
    "adc2": {"11": 0, "12": 1},
    "dac": [],
    "notes": {
        "0": "Strapping (mode de boot) ; souvent relie au bouton BOOT.",
        "26": "Reserve : Flash SPI / PSRAM."
    }
}
```

Points d'attention :
- les cles de `adc1` / `adc2` / `notes` sont des **chaines** (contrainte JSON),
  converties en entiers a la lecture ;
- si vous modifiez un fichier **sans** relancer le script, le controle
  d'integrite echouera (le sha256 ne correspondra plus). Lancez toujours le
  script apres une modification.
