# ESP32-Lab

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
- Registre des cartes connues (nom, emplacement, note par adresse MAC)
- Historique des inventaires et **comparaison de deux scans**
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
| GET     | `/api/nvs`                  | Rapport d'analyse NVS                    |
| POST    | `/api/inventory/refresh?port=…` | Scanne la carte et met à jour        |
| POST    | `/api/partitions?port=…`    | Lit la table de partitions (lecture seule) |
| POST    | `/api/efuse?port=…`         | Lit et analyse les eFuses (lecture seule) |
| POST    | `/api/flash?port=…`         | Lit le SFDP et l'ID unique de la Flash (lecture seule) |
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
