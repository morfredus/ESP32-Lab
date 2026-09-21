# Journal des modifications

Toutes les évolutions notables du projet sont consignées ici.

Le format s'inspire de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/),
et le projet suit le [versionnage sémantique](https://semver.org/lang/fr/)
(`MAJEUR.MINEUR.CORRECTIF`).

Le projet est en développement actif (série `0.x`). La `1.0.0` sera publiée
lorsqu'ESP32-Lab sera considéré comme abouti.

## [0.4.2] - 2026-09-21

Scripts de lancement documentés et adaptés au Raspberry Pi sans écran.

### Modifié
- **`launch_esp32_lab.sh`** : n'ouvre plus un navigateur à l'aveugle. Il
  n'ouvre le navigateur local que si une **session graphique** est présente
  (`DISPLAY`/`WAYLAND_DISPLAY`) ; sur un Pi **headless**, il **affiche les
  adresses d'accès distant** (IP réseau et nom mDNS `<hôte>.local`) au lieu
  d'échouer.
- `VERSION` → 0.4.2.

### Ajouté
- Documentation des deux scripts de lancement (`launch_esp32_lab.bat` /
  `launch_esp32_lab.sh`) dans le README et `docs/installation.md`.
- **README bilingue** : `README.md` en anglais, `README_fr.md` en français,
  avec sélecteur de langue en tête de chaque fichier.

## [0.4.1] - 2026-09-21

Correctifs révélés par le test « changement de poste » (clone neuf + import).

### Corrigé
- **`.gitignore` : la règle `web/` (non ancrée) ignorait `src/web/`**, ce qui a
  fait qu'un fichier neuf de l'interface (`db_compare.js`) n'a pas été versionné
  et manquait sur un clone neuf → Export/Import/Vérifier/Comparer inopérants.
  Ancrée en `/web/` ; `src/web/` n'est plus jamais ignoré.
- Sauvegardes datées locales (`*.bak-*`, `*.backup-*`) désormais ignorées pour
  ne pas polluer le dépôt.

### Modifié
- **Import de base robuste** : retour visible directement dans la section
  Maintenance (lecture du fichier, JSON invalide, import en cours, résultat ou
  erreur), au lieu du seul bandeau de statut en haut de page. Sélecteur de
  fichier plus tolérant (`.json` + type MIME).
- `VERSION` → 0.4.1.

## [0.4.0] - 2026-09-21

Base de données SQLite, comparaison inter-cartes et analyse NVS à la demande.

### Ajouté
- **Base de données SQLite** (`data/esp32lab.db`) comme source de vérité :
  registre des cartes + historique complet de toutes les lectures
  (identification, eFuses, SFDP, partitions, NVS). Création automatique et
  propre au premier lancement (schéma créé à la première connexion, même sur
  une installation neuve), avec **migration** des anciens fichiers JSON.
- **Persistance de toutes les lectures** : chaque analyse (eFuses, SFDP,
  partitions, NVS) est enregistrée par carte.
- **Comparaison complète de deux cartes** (onglet Inventaire) : identification,
  eFuses/sécurité, SFDP et partitions côte à côte, avec repérage des
  différences. Endpoints `/api/db/device` et `/api/db/compare`.
- **Analyse NVS à la demande** : si aucun rapport n'existe, l'analyse est
  déclenchée automatiquement en lisant la partition NVS de la carte (lecture
  seule). Nouveau module `esp32_nvs.py` avec **CRC ESP-IDF correct** (les
  vraies entrées sont désormais validées), bouton « Analyser la NVS de la
  carte », endpoint `/api/nvs/analyze`.
- **Section « Maintenance de la base »** (onglet Inventaire) : Export / Import
  JSON portable (fusion additive, sans doublon ni écrasement des noms),
  **vérification d'intégrité** et **remise à zéro** propre (sans réimporter les
  anciens JSON, grâce à un marqueur de migration). Endpoints `/api/db/export`,
  `/api/db/import`, `/api/db/verify`, `/api/db/reset`. (Copier le fichier
  `data/esp32lab.db` transfère aussi tout.)
- Migration des anciens JSON **idempotente et additive** (rattrape les scans
  manquants sans dupliquer).
- Modules `database.py`, `comparison.py`, `esp32_nvs.py`.
- Tests `test_database.py`, `test_nvs.py`.

### Modifié
- `device_registry.py`, `inventory_history.py`, `inventory_store.py` délèguent
  désormais à la base SQLite (signatures inchangées).
- `VERSION` → 0.4.0.

## [0.3.0] - 2026-09-20

Lecture bas niveau de la puce Flash : SFDP et identifiant unique.

### Ajouté
- **Lecture SFDP** (JESD216) de la puce Flash, dans l'onglet Partitions Flash :
  densité réelle, adressage, granularités d'effacement (4/32/64 Kio + opcodes),
  modes de lecture rapide (dual/quad), tables de paramètres.
- **Identifiant unique 64 bits** de la puce Flash (commande SPI 0x4B).
- Module `esp32_flash_sfdp.py` : lecture via l'API Python d'esptool sur une
  seule connexion (sous-processus portable), parseurs JESD216 testables.
- Endpoint HTTP `/api/flash` (SFDP + identifiant unique, lecture seule).
- `resolved_python()` dans `esptool_runner.py`.
- Tests `test_flash_sfdp.py` (valeurs réelles ESP32-S3 / Boya W25Q128).

### Modifié
- Onglet Partitions Flash enrichi d'une section « Puce Flash (SFDP) » au-dessus
  de la table de partitions.
- `VERSION` → 0.3.0.

## [0.2.0] - 2026-09-20

Ajout de la lecture des **eFuses** : la source d'information la plus profonde
d'une puce Espressif.

### Ajouté
- **Onglet « Identité & Sécurité »** exposant les eFuses de la puce (lecture
  seule via `espefuse summary`) :
  - **posture de sécurité** claire (Secure Boot, chiffrement Flash, USB-JTAG,
    mode téléchargement, version anti-rollback, clés provisionnées) ;
  - **identité du silicium** : révision exacte, version de package, version de
    bloc de calibration, capacités PSRAM/Flash, calibration température ;
  - **identifiant unique 128 bits** de la puce ;
  - **adresses MAC universelles** dérivées (Wi-Fi STA/AP, Bluetooth, Ethernet) ;
  - **dump complet des 112 eFuses** regroupées par catégorie (repliables).
- Module `esp32_efuse.py` (analyse, posture de sécurité, dérivation des MAC).
- Endpoint HTTP `/api/efuse` (lecture des eFuses, lecture seule).
- Support d'`espefuse` dans le résolveur portable (`esptool_runner.py`).
- Tests `test_efuse.py` avec capture réelle (fixture ESP32-S3).

### Modifié
- Onglets réorganisés : Général · **Identité & Sécurité** · Analyse NVS ·
  Partitions Flash · Inventaire.
- `VERSION` → 0.2.0.

## [0.1.0] - 2026-09-20

Première version structurée : refonte de l'interface web, lecture réelle des
données matérielles et modularisation du code.

### Ajouté
- **Lecture réelle de la table de partitions** sur la carte (`esp32_partitions.py`),
  en lecture seule à l'adresse `0x8000`, avec analyse du format binaire
  (type, sous-type, offset, taille, chiffrement).
- **Catalogue Flash JEDEC** (`flash_catalog.py`) : identification du fabricant
  et de la référence de la puce Flash (ex. `68` → Boya, `4018` → W25Q128).
- **Comparaison de deux scans d'une même carte** depuis l'onglet Inventaire
  (bouton « Comparer les scans » + colonne « Scans »).
- **Colonne « Valeur lisible »** dans l'analyse NVS : décodage des entiers
  (little-endian, signé/non signé selon le code de type NVS) et des tailles
  de chaînes/blobs.
- **Résolution portable d'esptool** (`esptool_runner.py`) : détection
  automatique d'esptool (interpréteur courant, `.venv` du projet, ou PATH).
- Endpoint HTTP `/api/partitions` (lecture des partitions).
- Service des fichiers statiques (`/css/`, `/js/`) avec protection anti-traversal.
- Fichier `VERSION`, `CHANGELOG.md` et documentation débutant dans `docs/`.
- Version exposée par `/api/health` et affichée dans l'interface.

### Modifié
- **Interface réorganisée en 4 onglets** : Général · Analyse NVS ·
  Partitions Flash · Inventaire (regroupe Cartes enregistrées, Historique
  et Comparaison).
- **Modularisation** : `index.html` (2971 lignes) éclaté en HTML propre +
  `css/style.css` + 11 modules JavaScript (`util`, `state`, `api`, `ports`,
  `inventory`, `devices`, `history`, `partitions`, `nvs`, `tabs`, `main`).
- Inventaire enrichi côté serveur avec les libellés Flash lisibles.

### Corrigé
- **Erreur JavaScript `Cannot set properties of null`** au chargement
  (script NVS orphelin référençant des éléments inexistants).
- **Données NVS fabriquées supprimées** : les valeurs codées en dur
  (SSID, compteurs) présentées comme lues sont remplacées par les vraies
  valeurs décodées du rapport.
- `inventory_store.load_last_inventory()` renvoie `None` (au lieu de lever)
  quand aucun inventaire n'existe, évitant une erreur 500 au démarrage.
- Ordre de chargement corrigé (historique avant cartes) pour le comptage
  des scans par carte.

### Sécurité
- Aucune écriture ni modification de la carte : toutes les opérations
  matérielles restent en lecture seule (conforme aux principes du projet).

[0.1.0]: https://example.invalid/ESP32-Lab/releases/tag/v0.1.0
