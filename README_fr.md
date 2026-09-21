# ESP32-Lab

[🇬🇧 English](README.md) | 🇫🇷 **Français**

![Version](https://img.shields.io/badge/version-0.7.0-blue)
![Python](https://img.shields.io/badge/python-3.10+-3776AB?logo=python&logoColor=white)
![Tests](https://img.shields.io/badge/tests-79%20passing-brightgreen)
![Cibles](https://img.shields.io/badge/cibles-ESP32--S3%20%7C%20ESP32--C3-orange)
![Mode](https://img.shields.io/badge/mat%C3%A9riel-lecture%20seule-success)
![Statut](https://img.shields.io/badge/statut-en%20d%C3%A9veloppement-yellow)
![Licence](https://img.shields.io/badge/licence-GPL--3.0--only-blue)

Laboratoire de diagnostic et de test pour microcontrôleurs ESP32, avec
interface web. Détecte, identifie et analyse une carte ESP32 connectée en USB
à un Raspberry Pi (ou tout autre hôte Linux/Windows).

> **Nouveau ?** Commence par le [guide de démarrage rapide](docs/demarrage-rapide.md).
> La documentation complète est dans le dossier [`docs/`](docs/).

## Objectif

Permettre l'identification, l'analyse et le test **non destructifs** d'un ESP32
connecté, et conserver un historique des diagnostics.

## Cibles

- ESP32-S3
- ESP32-C3
- Versions avec ou sans PSRAM

## Fonctionnalités

- Détection des ports USB / série
- Identification du SoC (puce, révision, fréquences, PSRAM)
- Analyse de la Flash (fabricant, référence JEDEC, taille, type, tension)
- **Lecture des eFuses** : identité du silicium, identifiant unique 128 bits,
  posture de sécurité, calibration, MAC universelles (lecture seule)
- **SFDP de la puce Flash** (JESD216) : densité, adressage, granularités
  d'effacement, modes de lecture rapide, et identifiant unique 64 bits
- **Lecture réelle de la table de partitions** (lecture seule, à `0x8000`)
- **Analyse structurelle NVS** avec décodage lisible des valeurs
- **Base de données SQLite** conservant toutes les lectures par carte, avec
  **réaffichage depuis la base** (sans carte branchée) sur toutes les sections :
  un export/import restaure et affiche l'intégralité sur un autre poste
- **Aucun secret en base** : mots de passe Wi-Fi et clés eFuse jamais stockés
  (une empreinte HMAC-SHA-256 détecte les changements sans garder le secret)
- **Détection de changement de secrets** : compare les empreintes HMAC d'une
  même clé entre deux scans pour signaler un secret modifié - sans jamais le stocker
- Registre des cartes connues (nom, emplacement, note par adresse MAC)
- Historique des inventaires, **comparaison de deux scans** et
  **comparaison complète de deux cartes différentes**
- **Analyse NVS à la demande** (lecture de la partition NVS de la carte)
- **GPIO Inspector** (niveau puce, dépendant de la famille) : classification de
  chaque broche (strapping, entrée seule, Flash/PSRAM, USB-JTAG, ADC, DAC),
  statut d'usage et avertissements de boot - appuyé sur une **base de références
  Espressif locale** disponible hors ligne (curée d'après les datasheets
  Espressif, mise à jour manuelle, contrôle d'intégrité)
- **Compatible morfSystem** : s'annonce via morfBeacon (heartbeat UDP) avec les
  endpoints `/healthz` et `/status` - découvrable par morfMonitor
- Export CSV
- Interface web organisée en onglets

## Démarrage rapide

```bash
# 1. Installer les dépendances dans un environnement virtuel
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Lancer le serveur
PYTHONPATH=src .venv/bin/python -m web.server

# 3. Ouvrir l'interface
#    http://<adresse-du-serveur>:8765
```

### Scripts de lancement

Deux scripts à la racine automatisent le démarrage (vérification du `.venv`,
lancement du serveur, ouverture ou affichage de l'adresse) :

- **Windows** : double-clic sur `launch_esp32_lab.bat` (ouvre le navigateur
  local sur http://127.0.0.1:8765).
- **Linux / Raspberry Pi** : `./launch_esp32_lab.sh`. Sur un Pi **avec** écran,
  il ouvre le navigateur ; sur un Pi **sans écran** (headless), il n'ouvre rien
  et **affiche les adresses à saisir depuis un autre poste** (IP réseau et nom
  mDNS `<hôte>.local`).

Détails et alternatives (hors venv, Windows, Raspberry Pi) :
voir [`docs/installation.md`](docs/installation.md).

## Structure du projet

```
ESP32-Lab/
├── VERSION                 Version courante du projet
├── CHANGELOG.md            Journal des modifications
├── requirements.txt        Dépendances Python
├── docs/                   Documentation (débutant + architecture)
├── reference/espressif/    Jeu de références GPIO Espressif curé (livré, hors ligne)
├── data/                   Données générées + cache local du jeu (git-ignoré)
├── src/
│   ├── core/               Logique métier (identification, partitions, NVS…)
│   ├── transport/          Accès série / détection des ports
│   └── web/                Serveur HTTP + interface statique (HTML/CSS/JS)
├── tests/                  Tests unitaires
└── tools/                  Utilitaires (lecture SFDP, etc.)
```

Voir [`docs/architecture.md`](docs/architecture.md) pour le détail.

## API HTTP

| Méthode | Route                       | Description                              |
|---------|-----------------------------|------------------------------------------|
| GET     | `/api/health`               | État du service + version + port         |
| GET     | `/healthz`                  | Liveness (contrat morfBeacon)            |
| GET     | `/status`                   | Statut riche (contrat morfBeacon)        |
| GET     | `/api/ports`                | Ports série détectés                     |
| GET     | `/api/inventory`            | Dernier inventaire enregistré            |
| GET     | `/api/inventory/history`    | Historique des inventaires               |
| GET     | `/api/devices`              | Registre des cartes                      |
| GET     | `/api/device?mac=…`         | Fiche d'une carte                        |
| GET     | `/api/db/device?mac=…`      | Dossier complet d'une carte (base)       |
| GET     | `/api/db/reading?mac=…&section=…` | Dernière lecture d'une section pour une carte |
| GET     | `/api/db/compare?mac_a=…&mac_b=…` | Comparaison de deux cartes         |
| GET     | `/api/db/changes?mac=…`     | Détection de changement de secrets (empreintes HMAC) |
| GET     | `/api/gpio?chip=…`          | Cartographie GPIO au niveau puce (par famille) |
| GET     | `/api/espressif/status`     | État de la base de références Espressif locale |
| POST    | `/api/espressif/refresh`    | Mise à jour de la base Espressif (canal projet) |
| GET     | `/api/nvs`                  | Dernier rapport d'analyse NVS            |
| POST    | `/api/inventory/refresh?port=…` | Scanne la carte et met à jour        |
| POST    | `/api/partitions?port=…`    | Lit la table de partitions (lecture seule) |
| POST    | `/api/efuse?port=…`         | Lit et analyse les eFuses (lecture seule) |
| POST    | `/api/flash?port=…`         | Lit le SFDP et l'ID unique de la Flash (lecture seule) |
| POST    | `/api/nvs/analyze?port=…`   | Lit et analyse la partition NVS (lecture seule) |
| GET     | `/api/db/export`            | Exporte toute la base (JSON portable)    |
| GET     | `/api/db/verify`            | Vérifie l'intégrité et les statistiques  |
| POST    | `/api/db/import`            | Importe/fusionne un export de base       |
| POST    | `/api/db/reset`             | Remet la base à zéro (irréversible)      |
| POST    | `/api/device/update`        | Enregistre la fiche d'une carte          |
| POST    | `/api/device/delete`        | Supprime une carte et toutes ses lectures |

## Principes

- Aucun effacement automatique
- Aucune modification des eFuses
- Tests non destructifs par défaut
- Séparation entre informations **détectées** et informations **rapportées**
- Compatibilité multi-familles ESP32

## Tests

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q
```

## Licence

Ce projet est distribué sous licence **GNU General Public License v3.0
uniquement** (`GPL-3.0-only`). Voir le fichier [LICENSE](LICENSE) pour le texte
complet.

Copyright (C) 2026 Frédéric Biron.

Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
modifier selon les termes de la GNU General Public License telle que publiée
par la Free Software Foundation, version 3 uniquement. Il est distribué dans
l'espoir qu'il sera utile, mais SANS AUCUNE GARANTIE, ni explicite ni implicite,
notamment de QUALITÉ MARCHANDE ou d'ADÉQUATION À UN USAGE PARTICULIER.
