# ESP32-Lab

[🇬🇧 English](README.md) | 🇫🇷 **Français**

![Version](https://img.shields.io/badge/version-0.5.0-blue)
![Python](https://img.shields.io/badge/python-3.10+-3776AB?logo=python&logoColor=white)
![Tests](https://img.shields.io/badge/tests-43%20passing-brightgreen)
![Cibles](https://img.shields.io/badge/cibles-ESP32--S3%20%7C%20ESP32--C3-orange)
![Mode](https://img.shields.io/badge/mat%C3%A9riel-lecture%20seule-success)
![Statut](https://img.shields.io/badge/statut-en%20d%C3%A9veloppement-yellow)

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
- **Base de données SQLite** conservant toutes les lectures par carte
- **Aucun secret en base** : mots de passe Wi-Fi et clés eFuse jamais stockés
  (une empreinte HMAC-SHA-256 détecte les changements sans garder le secret)
- Registre des cartes connues (nom, emplacement, note par adresse MAC)
- Historique des inventaires, **comparaison de deux scans** et
  **comparaison complète de deux cartes différentes**
- **Analyse NVS à la demande** (lecture de la partition NVS de la carte)
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
├── data/                   Données générées (inventaires, historique, registre)
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
| GET     | `/api/health`               | État du service + version                |
| GET     | `/api/ports`                | Ports série détectés                     |
| GET     | `/api/inventory`            | Dernier inventaire enregistré            |
| GET     | `/api/inventory/history`    | Historique des inventaires               |
| GET     | `/api/devices`              | Registre des cartes                      |
| GET     | `/api/device?mac=…`         | Fiche d'une carte                        |
| GET     | `/api/db/device?mac=…`      | Dossier complet d'une carte (base)       |
| GET     | `/api/db/reading?mac=…&section=…` | Dernière lecture d'une section pour une carte |
| GET     | `/api/db/compare?mac_a=…&mac_b=…` | Comparaison de deux cartes         |
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

Projet personnel. Voir avec l'auteur pour toute réutilisation.
