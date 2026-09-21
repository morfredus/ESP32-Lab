# Architecture du projet

Ce document explique comment le code est organisé. Utile si tu veux comprendre,
modifier ou étendre ESP32-Lab.

## Vue d'ensemble

```
Navigateur (HTML/CSS/JS)
        │  requêtes HTTP (fetch)
        ▼
Serveur web  (src/web/server.py)
        │  appels de fonctions
        ▼
Cœur métier  (src/core/)
        │  subprocess
        ▼
esptool  ──►  carte ESP32 (USB série)
```

Le serveur est volontairement minimal : il s'appuie sur `http.server` de la
bibliothèque standard, **sans framework externe**.

## Arborescence

```
src/
├── core/
│   ├── esp32_identification.py   Appelle esptool (flash-id) et parse la sortie
│   ├── esp32_inventory.py        Construit une fiche d'inventaire complète
│   ├── esp32_partitions.py       Lit + analyse la table de partitions (0x8000)
│   ├── esp32_efuse.py            Lit + analyse les eFuses (espefuse), sécurité
│   ├── esp32_flash_sfdp.py      Lit le SFDP (JESD216) + ID unique de la Flash
│   ├── esp32_nvs.py             Lit + analyse la partition NVS (à la demande)
│   ├── esp32_gpio.py            Cartographie GPIO (niveau puce, par famille)
│   ├── espressif_dataset.py     Base de références Espressif locale (offline)
│   ├── database.py              Base SQLite : cartes + toutes les lectures
│   ├── comparison.py            Comparaison riche entre deux cartes
│   ├── secret_changes.py       Détection de changement de secrets (empreintes)
│   ├── morfbeacon.py           Annonce morfBeacon (heartbeat UDP 45454)
│   ├── secret_redaction.py     Caviarde les secrets avant stockage (empreinte)
│   ├── install_key.py          Clé d'installation + empreintes HMAC-SHA-256
│   ├── flash_catalog.py          Correspondance des identifiants Flash JEDEC
│   ├── esptool_runner.py         Résolution portable d'esptool
│   ├── device_registry.py        Registre persistant des cartes (par MAC)
│   ├── inventory_store.py        Lecture du dernier inventaire
│   └── inventory_history.py      Historique des inventaires
├── transport/
│   ├── serial_detect.py          Détection des ports série
│   └── serial_connection.py      Connexion série bas niveau
└── web/
    ├── server.py                 Serveur HTTP + routage API
    └── static/
        ├── index.html            Structure de la page (onglets)
        ├── css/style.css         Styles
        └── js/                   Modules JavaScript (voir plus bas)
```

## Le front-end (modules JS)

Les scripts sont des **scripts classiques** chargés dans l'ordre en fin de
`<body>`. Ils partagent le même contexte global, ce qui évite tout système de
build. Chaque fichier a une responsabilité :

| Fichier         | Rôle |
|-----------------|------|
| `util.js`       | Fonctions utilitaires (échappement HTML, formats, décodage NVS, catalogue Flash). |
| `state.js`      | État partagé et références DOM globales. |
| `api.js`        | Enveloppes `fetch` (`apiGet`, `apiPost`). |
| `ports.js`      | Détection et sélection des ports. |
| `inventory.js`  | Inventaire matériel + fiche de la carte. |
| `devices.js`    | Registre des cartes + comparaison de scans. |
| `history.js`    | Historique, comparaison, export CSV. |
| `partitions.js` | Lecture et rendu de la table de partitions. |
| `flash_sfdp.js` | SFDP de la puce Flash + identifiant unique. |
| `efuse.js`      | eFuses : identité, sécurité, MAC dérivées, dump complet. |
| `nvs.js`        | Analyse NVS et décodage lisible. |
| `db_compare.js` | Export/import de la base, comparaison de deux cartes, suivi des secrets. |
| `gpio.js`       | GPIO Inspector : base Espressif locale, tableau, filtres, sections. |
| `tabs.js`       | Navigation par onglets. |
| `main.js`       | Initialisation au chargement. |

Pour **ajouter un onglet** : ajoute un `<button data-tab="mon-id">` et une
`<section class="tab-panel" data-panel="mon-id">` dans `index.html`. La
navigation (`tabs.js`) est automatique via les attributs `data-*`.

## Le flux d'un scan

1. L'utilisateur clique sur « Scanner la carte » → `POST /api/inventory/refresh`.
2. `server.py` appelle `create_inventory(port)` (`esp32_inventory.py`).
3. `identify_esp32()` lance esptool `flash-id` via `esptool_runner`.
4. `parse_identification()` extrait puce, Flash, PSRAM, MAC…
5. `enrich_identification()` ajoute les libellés Flash (`flash_catalog`).
6. L'inventaire est sauvegardé, ajouté à l'historique, et le registre mis à jour.

## La lecture des partitions

`esp32_partitions.read_partition_table(port, chip)` :

1. lance esptool `read-flash 0x8000 0xC00 <fichier temporaire>` (lecture seule) ;
2. `parse_partition_table(octets)` décode les entrées de 32 octets
   (magic `0xAA50`, type, sous-type, offset, taille, label, flags) ;
3. s'arrête à la première entrée invalide ou à la signature MD5.

Ce parseur est **testé** indépendamment du matériel dans
`tests/test_partitions.py`.

## Portabilité d'esptool

`esptool_runner.py` résout la commande esptool dans cet ordre :

1. l'interpréteur Python courant (`sys.executable`) s'il a le module `esptool` ;
2. le `.venv` du projet (`.venv/bin/python` ou `.venv/Scripts/python.exe`) ;
3. la commande `esptool` présente dans le PATH.

Le résultat est mis en cache. Cela permet de lancer le serveur avec le Python
système tout en utilisant l'esptool du `.venv`.

## Tests

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q
```

| Fichier de test                  | Couvre |
|----------------------------------|--------|
| `test_identification_parser.py`  | Parsing de la sortie esptool. |
| `test_partitions.py`             | Décodage de la table de partitions. |
| `test_flash_catalog.py`          | Catalogue Flash JEDEC. |
| `test_efuse.py`                  | Analyse eFuse, sécurité, MAC dérivées. |
| `test_flash_sfdp.py`             | Analyse SFDP (JESD216), ID unique Flash. |
| `test_secret_redaction.py`       | Rédaction des secrets, empreintes HMAC. |
| `test_secret_changes.py`         | Détection de changement de secrets (empreintes). |
| `test_database_import_delete.py` | Import (noms complétés) et suppression d'une carte. |
| `test_gpio.py`                   | Cartographie GPIO (comptes, strapping, ADC, statuts). |
| `test_espressif_dataset.py`      | Base Espressif locale : seed, intégrité, refresh, sauvegarde. |
| `test_morfbeacon.py`             | Annonce morfBeacon, endpoints /healthz + /status. |
| `test_serial_connection.py`      | Connexion série. |

## Données générées

Le dossier `data/` contient les fichiers produits à l'usage :

- `esp32lab.db` - **base SQLite**, source de vérité (cartes + toutes les
  lectures). Créée automatiquement au premier lancement, avec migration des
  anciens JSON ;
- `last_inventory.json` - dernier scan (compat) ;
- `inventory_history.json`, `device_registry.json` - anciens fichiers migrés
  une fois dans la base au premier démarrage ;
- `analysis/reports/nvs_structure_analysis.json` - dernier rapport NVS généré ;
- `espressif/` - cache local de la base de références GPIO (copié depuis
  `reference/espressif/` au premier lancement, plus `.backup/` avant une mise à
  jour). Voir « GPIO Inspector et base de références Espressif ».

### Base de données

Deux tables :

- `devices(mac, name, location, note, first_seen, last_seen, port,
  identification)` - une carte par MAC (métadonnées + dernière identité) ;
- `readings(id, mac, section, recorded_at, port, payload)` : chaque lecture
  (section : `inventory`, `efuse`, `sfdp`, `partitions`, `nvs`) avec sa charge
  utile JSON, **assainie des secrets** avant stockage (voir ci-dessous).

Le schéma se crée à la première connexion (`database.connect`), donc une
installation neuve fonctionne sans aucune préparation. Les métadonnées de
migration/purge sont conservées dans une table `meta`.

Réaffichage : chaque section peut être rechargée depuis la base par MAC
(`GET /api/db/reading?mac=&section=`), ce qui permet de tout revoir sur un autre
poste sans la carte. Comparaison de deux cartes via `comparison.py`
(`/api/db/compare`), suppression d'une carte et de ses lectures via
`database.delete_device` (`/api/device/delete`).

### Sécurité des secrets

Aucun secret n'est stocké en base. Le nettoyage se fait sur une **copie** avant
écriture (`secret_redaction.py`) ; l'affichage live (lecture directe de la
carte) reste complet.

- **eFuses** : les blocs `BLOCK_KEYx` provisionnés sont caviardés et remplacés
  par une **empreinte HMAC-SHA-256** (`install_key.py`, clé propre à
  l'installation, hors base et non versionnée).
- **NVS** : les entrées sensibles (denylist : `pswd`, `passwd`, `psk`, `pmk`,
  `token`, `secret`) reçoivent une empreinte ; surtout, **aucun octet brut NVS**
  (`raw_hex`/`data_hex`/`key_hex`) n'est conservé, car la NVS est un journal où
  d'anciennes copies de secrets subsistent dans des slots effacés/orphelins. La
  « clé » des slots à CRC invalide (fragments de secret) est aussi neutralisée.
- **Détection de changement** (`secret_changes.py`, `/api/db/changes`) : compare
  les empreintes d'une même clé entre deux scans pour signaler un secret modifié,
  sans jamais le stocker.

La purge des secrets déjà présents (installations antérieures) est appliquée
**une fois** au démarrage via des marqueurs `meta` (`readings_redacted`,
`nvs_hex_purged`).

## GPIO Inspector et base de références Espressif

Le GPIO Inspector raisonne **au niveau de la puce** : à partir de la famille
détectée, `esp32_gpio.compute_gpio_map(chip)` génère la liste des broches avec
leur classification (strapping, entrée seule, Flash/PSRAM, USB-JTAG, ADC, DAC),
un statut d'usage (`available` / `restricted` / `avoid`) et les avertissements de
boot. Le calcul est **piloté par les données**, jamais générique.

Ces données ne sont pas publiées par Espressif sous une forme exploitable :
`espressif_dataset.py` gère un **jeu curé** (vérifié sur les datasheets et la
référence GPIO d'ESP-IDF), livré dans `reference/espressif/` (suivi git, donc
disponible **hors ligne** dès le clone) et copié au premier lancement dans un
cache inscriptible `data/espressif/`.

- **Source de vérité** : chaque famille est un fichier JSON versionné
  (`schema_version`) décrivant les ensembles de broches ; `metadata.json` porte
  la version du jeu, la source, la date de synchronisation et un **sha256 par
  fichier**.
- **Mise à jour manuelle** (`refresh_from_channel`, `POST /api/espressif/refresh`)
  depuis le canal projet (raw GitHub) : téléchargement (stdlib `urllib`),
  **validation du schéma + intégrité sha256**, **sauvegarde** de la base actuelle
  dans `.backup/` avant remplacement, et **conservation de la base locale** en cas
  d'échec (réseau, intégrité, schéma).
- L'exposition réelle des broches sur une carte donnée n'étant pas déductible de
  la puce, elle est signalée `board_exposure: "unknown"` (profil de carte prévu
  pour une version ultérieure).

Endpoints associés : `GET /api/gpio?chip=`, `GET /api/espressif/status`,
`POST /api/espressif/refresh`.
