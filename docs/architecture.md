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
| `test_serial_connection.py`      | Connexion série. |

## Données générées

Le dossier `data/` contient les fichiers produits à l'usage :

- `last_inventory.json` — dernier scan ;
- `inventory_history.json` — tous les scans ;
- `device_registry.json` — registre des cartes (noms, notes…).
