# Journal des modifications

Toutes les évolutions notables du projet sont consignées ici.

Le format s'inspire de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/),
et le projet suit le [versionnage sémantique](https://semver.org/lang/fr/)
(`MAJEUR.MINEUR.CORRECTIF`).

Le projet est en développement actif (série `0.x`). La `1.0.0` sera publiée
lorsqu'ESP32-Lab sera considéré comme abouti.

## [0.9.0] - 2026-09-22

Nouvelle fonctionnalite : identite du firmware et etat OTA (lecture seule).

### Ajoute
- **Onglet « Firmware & OTA »**. Lit dans la Flash (lecture seule) l'identite de
  chaque partition applicative via `esp_app_desc_t` : nom du projet, version,
  version ESP-IDF, date et heure de compilation, compteur anti-rollback
  (`secure_version`) et sha256 de l'ELF. Les slots vides ou chiffres sont
  signales comme tels.
- **Etat OTA** via la partition `otadata` : slot **selectionne au demarrage**
  (regle du bootloader), sequence, etat et CRC de chaque entree. Reserve honnete :
  c'est le slot de boot, pas forcement le firmware en cours d'execution.
- Endpoint `POST /api/firmware`, section de base de donnees `firmware`
  (persistee et reaffichable via « Charger depuis la base »).

## [0.8.0] - 2026-09-21

Nouvelle fonctionnalite : profils de cartes (exposition GPIO reelle).

### Ajoute
- **Profils de cartes** dans le GPIO Inspector. On choisit son modele de carte
  (menu filtre par la famille detectee) et le tableau indique, pour chaque
  broche, si elle est utilisee par une fonction embarquee (bouton BOOT, LED, USB
  natif, pont USB-UART), sortie sur connecteur, ou non exposee. Nouvelle colonne
  « Sur la carte », filtre « Exposees sur la carte », et contexte (source
  officielle + note de revision).
- **Catalogue cure** `reference/espressif/boards.json` (9 cartes : ESP32-DevKitC,
  ESP32-S3-DevKitC-1 v1.0 et v1.1, ESP32-C3-DevKitM-1, Seeed XIAO ESP32-S3 et
  ESP32-C3, ESP32-C3 SuperMini, ESP32-S3 SuperMini/Zero N4R2, uPesy ESP32-S3
  N16R8), source par carte. Il beneficie de la meme machinerie offline que le jeu
  GPIO (seed, integrite sha256, mise a jour, sauvegarde). Exemple de finesse : sur
  l'uPesy N16R8 (PSRAM Octal) GPIO33 a GPIO37 sont reserves, alors qu'ils sont
  disponibles sur la SuperMini N4R2 (PSRAM quad).
- **Memorisation par carte** : le modele choisi est enregistre sur la fiche (par
  MAC, colonne `board_profile`) et suit l'export/import et le changement de poste.
- **Garde-fou de compatibilite** : si le scan detecte une PSRAM Octal alors que
  le profil choisi expose les broches reservees a l'Octal (GPIO33-37 sur S3), un
  avertissement le signale. Le scan rattrape ainsi un mauvais choix de profil
  (meme puce, memoire differente selon le module), sans jamais imposer de carte.
- Endpoints : `GET /api/boards?family=`, `POST /api/device/board`, et parametre
  `board=` sur `GET /api/gpio`.

### Limites connues
- Le modele de carte n'est pas detecte automatiquement (USB VID/PID ne l'identifie
  pas de facon fiable) : la selection est manuelle.

## [0.7.0] - 2026-09-21

Nouvelle fonctionnalité : GPIO Inspector (niveau puce) et base de références
Espressif locale, disponible hors ligne.

### Ajouté
- **GPIO Inspector** (onglet dédié, lecture seule). À partir de la famille exacte
  détectée (ESP32, ESP32-S3, ESP32-C3), affiche pour chaque broche sa
  classification (strapping, entrée seule, réservé Flash/PSRAM, USB-JTAG, ADC,
  DAC), un statut d'usage (disponible / avec restrictions / à éviter) et les
  avertissements de boot. Les informations dépendent de la famille : jamais de
  table générique. Filtres (strapping, Flash/PSRAM, fonctions spéciales, entrée
  seule), résumé chiffré et sections repliables par catégorie de restriction.
- **Base de références Espressif locale, offline-first.** Un jeu de données curé
  (vérifié sur les datasheets Espressif et la référence GPIO d'ESP-IDF) est livré
  avec l'application (`reference/espressif/`) et copié dans un cache inscriptible
  (`data/espressif/`) au premier lancement. Fonctionne sans réseau.
- **Mise à jour manuelle** de la base (bouton « Actualiser depuis Espressif »)
  depuis le canal projet, avec schéma versionné, contrôle d'intégrité (sha256),
  sauvegarde de la version précédente et conservation de la base locale en cas
  d'échec.
- Endpoints : `GET /api/gpio`, `GET /api/espressif/status`,
  `POST /api/espressif/refresh`.
- **Outillage de maintenance** : `tools/build_espressif_metadata.py` régénère
  `metadata.json` (validation du schéma + recalcul des sha256), et un guide
  `reference/espressif/README.md` explique où récupérer chaque donnée chez
  Espressif avant d'utiliser le script.

### Limites connues
- L'exposition réelle des broches sur une carte (BOOT, LED, écran, USB natif du
  fabricant) dépend du profil de la carte et n'est pas déductible de la puce :
  elle est signalée « à confirmer ». Un sélecteur de profil de carte est prévu
  pour une version ultérieure.

## [0.6.5] - 2026-09-21

Correctif de sécurité : suppression des copies résiduelles de secrets en base.

### Sécurité
- **Mot de passe Wi-Fi en clair supprimé de la base.** Le caviardage 0.5.0
  masquait l'entrée « live » du secret (par clé + `span`), mais la NVS est un
  journal : d'anciennes copies (mot de passe, SSID) subsistaient dans des slots
  effacés/orphelins, à la clé illisible, non rattachés à la clé sensible. Ces
  copies étaient donc stockées **et exportées** vers d'autres postes.
- Correctif : **aucun octet brut NVS n'est plus conservé en base**. Tout dump
  hexadécimal (`raw_hex`/`data_hex`/`key_hex`) est caviardé pour **toutes** les
  entrées, et la « clé » des slots à CRC invalide (fragments de secret) est
  neutralisée. Les empreintes HMAC des secrets et la structure (pages, entrées,
  CRC, types, clés valides) sont conservées.
- **Purge rétroactive** de la base existante au démarrage (marqueur
  `nvs_hex_purged`). Vérifié : plus aucun mot de passe ni SSID dans la base ni
  dans les exports.

### Conséquence
- La lecture **live** sur la carte reste complète (le caviardage ne touche que
  la copie stockée). En revanche, la vue **NVS « depuis la base »** ne
  reconstruit plus les valeurs décodées (SSID, canal, dump hex) : elle affiche
  la structure. Les autres sections (eFuses, SFDP, partitions) sont inchangées.

## [0.6.4] - 2026-09-21

Réaffichage complet depuis la base, sans la carte (portabilité inter-postes).

### Ajouté
- **« Charger depuis la base »** sur les onglets eFuses, SFDP et Partitions :
  les dernières lectures enregistrées d'une carte se réaffichent **sans la
  carte branchée** (par MAC), au même titre que Général et NVS le faisaient
  déjà. Après un export/import sur un autre poste, on retrouve donc et on
  visualise l'intégralité des sections. Helper `loadStoredReading(section)`
  (endpoint existant `GET /api/db/reading`).

### Modifié
- Le vidage des panneaux au changement de carte (0.6.3) couvre maintenant aussi
  SFDP et Partitions, en plus d'eFuses et NVS.
- `VERSION` -> 0.6.4.

## [0.6.3] - 2026-09-21

Retouches d'ergonomie de l'interface (cohérence d'affichage).

### Corrigé
- **Panneaux eFuse et NVS vidés au changement de carte** : les onglets
  « Identité & Sécurité » et « Analyse NVS » se lisent en direct sur la carte.
  Après « Actualiser les ports » ou un changement de port, ils ne conservent
  plus les données de la carte précédente et repartent vides.
- **Mise à jour en direct après édition d'une fiche** : enregistrer le nom,
  l'emplacement ou la note d'une carte rafraîchit immédiatement le registre des
  cartes, l'historique et la fiche affichée dans « Général », sans recharger
  la page.

### Modifié
- `VERSION` -> 0.6.3.

## [0.6.2] - 2026-09-21

Correctif d'import (noms de cartes) et suppression d'une carte.

### Corrigé
- **Import** : une carte déjà présente en base (créée vide par un scan) ne
  récupérait pas son **nom** (ni emplacement/note) lors de l'import, à cause
  d'un `INSERT OR IGNORE`. L'import **complète désormais les champs vides** des
  cartes existantes sans jamais écraser une valeur éditée localement, et
  renseigne l'identification manquante. Le résumé d'import indique le nombre de
  fiches complétées (`devices_updated`). La fiche affichée est rafraîchie après
  import.

### Ajouté
- **Suppression d'une carte** : bouton « Supprimer » dans le registre des
  cartes (avec confirmation), qui efface la carte **et toutes ses lectures**.
  Endpoint `POST /api/device/delete`, fonction `database.delete_device`.
- Tests `test_database_import_delete.py` (complétion des noms à l'import, nom
  local préservé, suppression carte + lectures). **59 tests.**

### Modifié
- `VERSION` -> 0.6.2.

## [0.6.1] - 2026-09-21

Détection de changement de secrets, par empreinte HMAC, entre deux scans.

### Ajouté
- **Suivi des secrets** : comparaison des empreintes HMAC d'une même clé
  (entrée NVS sensible ou bloc eFuse provisionné) entre les **deux dernières
  analyses** d'une carte, pour signaler qu'un secret a **changé** sans jamais
  le stocker. Verdicts : inchangé, changé, nouveau, disparu, et
  **indéterminable** lorsque les deux empreintes proviennent de clés
  d'installation différentes (scans faits sur deux postes). Module
  `core/secret_changes.py`, endpoint `GET /api/db/changes?mac=…`.
- Bouton **« Suivi des secrets »** dans la fiche détaillée d'une carte.
- Tests `test_secret_changes.py` (inchangé / changé / nouveau / disparu /
  indéterminable, extraction des empreintes NVS et eFuse).

### Licence
- Le projet passe sous **GNU GPL v3.0 only** (`GPL-3.0-only`). Ajout du fichier
  `LICENSE` (texte intégral) et mise à jour des mentions dans les README.

### Modifié
- `VERSION` → 0.6.1.

## [0.6.0] - 2026-09-21

ESP32-Lab rejoint le langage commun morfSystem (morfBeacon).

### Ajouté
- **Annonce morfBeacon** : ESP32-Lab diffuse un heartbeat UDP périodique en
  broadcast sur **45454/UDP** (`proto: morfbeacon/1`, `app`, `host`, `version`,
  `state`, `status_port`, `instance`, `capabilities: ["esp32-characterization"]`,
  `ts`). morfMonitor peut ainsi le découvrir automatiquement. Module
  `core/morfbeacon.py`.
- Endpoints **`/healthz`** (liveness) et **`/status`** (riche : app, version,
  state, host, port, capacité, métriques, liste d'endpoints), conformes au
  contrat morfBeacon.
- Métriques légères de la base (`database.counts`).
- Tests `test_morfbeacon.py` (dont capture réelle du broadcast).

### Note (autonomie)
- L'annonce est **purement additive** : sans réseau ni morfMonitor, ESP32-Lab
  fonctionne exactement pareil. Toute erreur d'émission est silencieuse.

### Modifié
- `VERSION` → 0.6.0.

## [0.5.3] - 2026-09-21

Sélection automatique du port, et affichage du port dans l'interface.

### Ajouté
- **Port automatique** : au démarrage, si le port 8765 est déjà utilisé, le
  serveur bascule sur le premier port libre suivant (8766, 8767…). Détection
  fiable par test de connexion (fonctionne sous Linux comme Windows, malgré
  `SO_REUSEADDR`). Le port réel est indiqué au démarrage (console) et exposé
  par `/api/health`.
- **Port affiché dans l'interface**, à côté de la version.
- Le message de démarrage rappelle l'adresse mDNS `<hôte>.local:<port>`.

### Modifié
- `VERSION` → 0.5.3.

### Note (indépendance des postes)
- Toutes les requêtes de l'interface sont **relatives** : chaque UI dialogue
  avec le serveur qui l'a servie. Lancer ESP32-Lab simultanément sur le Pi et
  sous Windows reste donc totalement indépendant (bases et actions séparées).

## [0.5.2] - 2026-09-21

Affichage de l'inventaire piloté par la carte connectée, et fin du cache JS.

### Modifié
- **Plus d'inventaire « par défaut » au lancement.** La vue Général part vide,
  puis affiche **la carte connectée si elle a déjà été scannée** - la
  correspondance se fait via le **numéro de série USB** (qui, sur les ESP32 à
  USB natif, est la MAC). Sinon la vue reste vide, avec un message d'invite.
  L'inventaire se remplit aussi après « Scanner la carte » et « Actualiser les
  ports ». `loadInventory(mac)` lit désormais la base par MAC.
- **`Cache-Control: no-store`** sur les fichiers statiques : le navigateur ne
  ressert plus un ancien HTML/CSS/JS après une mise à jour (outil local).
- `VERSION` → 0.5.2.

## [0.5.1] - 2026-09-21

Le nom de la carte est visible partout, et la vue Général passe à 8 cartes.

### Ajouté
- **Nom enregistré de la carte affiché partout** : nouvelle carte « Carte »
  (nom + emplacement + note) en tête de l'onglet Général, colonne « Nom » dans
  l'historique, et **noms de cartes** (au lieu de « Inventaire 1/2 ») dans le
  comparatif de scans et le titre de la modale d'historique. Helpers
  `deviceName` / `deviceLabel` / `registeredDevice`.

### Modifié
- **Onglet Général réorganisé en 8 cartes** (deux rangées de 4 sur écran large),
  dans un ordre de lecture logique : Carte · Microcontrôleur · Processeur ·
  Mémoire Flash // PSRAM · Connectivité · Adresse MAC · Connexion.
- Ordre de chargement ajusté (registre chargé en premier) pour que les noms
  soient disponibles dès l'affichage de l'inventaire et de l'historique.
- `VERSION` → 0.5.1.

## [0.5.0] - 2026-09-21

Les secrets ne sont plus jamais stockés en base (piste 1).

### Ajouté
- **Rédaction des secrets avant stockage** (`secret_redaction.py`) : les mots de
  passe Wi-Fi, PMK et clés eFuse provisionnées ne sont **plus jamais écrits en
  base** ; ils sont remplacés par une **empreinte HMAC-SHA-256** permettant de
  détecter un changement d'un scan au suivant, sans conserver le secret.
  L'affichage live (lecture directe de la carte) reste complet.
- **Clé d'installation** (`install_key.py`) : générée une fois, dans la config
  du service (jamais en base ni versionnée), avec résolution multi-plateforme
  (Linux `/etc/morfsystem/esp32-lab/` ou `~/.config/…`, Windows
  `%ProgramData%\morfsystem\esp32-lab\` ou `%APPDATA%\…`) et droits restreints.
- **Purge rétroactive** : au premier lancement après mise à jour, les lectures
  NVS/eFuse déjà enregistrées (versions < 0.5.0, contenant des secrets en clair)
  sont caviardées une fois.
- Tests `test_secret_redaction.py` + purge dans `test_database.py`.

### Sécurité
- Aucune copie stockée (base `.db` ou export JSON) ne contient de secret :
  un backup ou un transfert entre postes ne peut plus fuiter un mot de passe.
- Les empreintes sont **locales à l'installation** (clé propre à la machine) :
  la détection de changement se rebase automatiquement après un transfert de
  données vers un autre poste, sans jamais exposer le secret.

### Modifié
- `VERSION` → 0.5.0.

## [0.4.3] - 2026-09-21

Analyse NVS cohérente par carte (lecture depuis la base).

### Modifié
- **« Charger l'analyse NVS » lit désormais la base par carte** : il affiche la
  dernière analyse NVS **de la carte scannée** (via sa MAC), au lieu du fichier
  partagé `nvs_structure_analysis.json` qui ne gardait que la dernière carte
  analysée toutes confondues. Fin de l'affichage incohérent d'une carte à
  l'autre.
- Si aucune analyse NVS n'existe en base pour la carte, l'analyse est déclenchée
  automatiquement (port requis).
- `VERSION` → 0.4.3.

### Ajouté
- Endpoint `GET /api/db/reading?mac=…&section=…` (dernière lecture d'une section
  pour une carte).
- Test `test_get_latest_reading`.

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
