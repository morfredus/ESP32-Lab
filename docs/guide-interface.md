# Guide de l'interface

L'interface s'organise autour d'une **barre d'outils globale** (toujours
visible) et de **sept onglets** : Général · Identité & Sécurité · Analyse NVS ·
Partitions Flash · GPIO Inspector · Firmware & OTA · Inventaire.

> Les captures d'écran de ce guide utilisent un **jeu de démonstration
> anonymisé** (noms, adresses MAC et identifiants fictifs).

## La barre d'outils (toujours visible)

En haut de la page, quel que soit l'onglet :

- **Menu des ports** - sélectionne la carte à interroger.
- **Actualiser les ports** - relance la détection des ports USB.
- **Scanner la carte** - interroge la carte sélectionnée et met à jour tout.
- **Bandeau de statut** - messages de succès (vert) ou d'erreur (rouge).

## Onglet Général

![Onglet Général : inventaire matériel en 8 cartes et fiche de la carte](images/01-general.png)

C'est la vue d'ensemble de la carte actuellement connectée.

### Inventaire matériel actuel
Des cartes résument le microcontrôleur, la Flash, la PSRAM, la connectivité et
la connexion. Les données proviennent du **dernier scan** (`Scanner la carte`).

### Fiche de la carte
Associe des informations **personnelles** à la carte (identifiée par sa MAC) :

- **Nom** (ex. « ESP32-S3 capteur météo ») ;
- **Emplacement** (ex. « Atelier ») ;
- **Note** libre.

Clique sur **Enregistrer la fiche** pour sauvegarder. Ces informations sont
conservées même après un redémarrage.

## Onglet Identité & Sécurité (eFuses)

Les **eFuses** sont des fusibles programmables une seule fois, gravés dans le
silicium. Ils contiennent les informations les plus profondes de la puce,
rarement visibles ailleurs. La lecture est **en lecture seule** : aucune eFuse
n'est modifiée.

![Onglet Identité & Sécurité : posture de sécurité, identité du silicium, MAC universelles](images/02-identite-securite.png)

Deux boutons :

- **Lire les eFuses** (le port doit être sélectionné dans Général) : lecture sur
  la carte, une dizaine de secondes.
- **Charger depuis la base** : réaffiche la **dernière lecture enregistrée** de
  cette carte, **sans la carte branchée** (pratique après un changement de
  poste).

S'affichent :

### Sécurité
Un tableau de bord de l'état de sécurité, avec un badge Activé/Désactivé :

- **Secure Boot** - vérification de signature du firmware au démarrage ;
- **Chiffrement Flash** - chiffrement du contenu de la Flash ;
- **USB-JTAG désactivé** - blocage du débogage matériel ;
- **Mode téléchargement désactivé** - blocage du reflashage ;
- **Téléchargement sécurisé** ;
- **Version sécurisée** - compteur anti-rollback ;
- **Clés provisionnées** - emplacements de clés utilisés.

### Bilan de sécurité
Sous le tableau de bord, un **bilan** transforme ces indicateurs en checklist
lisible : une **posture globale** (Développement / Durcissement partiel / Durcie),
et pour chaque protection son état, une explication et un **conseil « en
production »**. Le ton est volontairement **non alarmiste** : sur une carte de
développement, une protection désactivée est normale, pas une erreur.

### Identité du silicium
Révision exacte, version de package, capacités PSRAM/Flash gravées, calibration
de température, et surtout l'**identifiant unique 128 bits** de la puce.

### Adresses MAC universelles
Les quatre adresses dérivées de la MAC de base : Wi-Fi station, Wi-Fi point
d'accès, Bluetooth et Ethernet.

### Toutes les eFuses
Le dump complet (plus de 100 champs), regroupé par catégorie en sections
repliables, avec pour chaque eFuse sa valeur lisible, sa description et sa
valeur brute.

## Onglet Analyse NVS

La **NVS** est un petit espace mémoire où l'ESP32 range des réglages
(identifiants Wi-Fi, compteurs de démarrage, calibration…).

![Onglet Analyse NVS : résumé des données détectées et structure des pages](images/03-analyse-nvs.png)

Deux boutons :

- **Charger l'analyse NVS** - affiche la dernière analyse NVS **de la carte
  scannée** (récupérée en base par son adresse MAC) ; si aucune n'existe pour
  cette carte, l'analyse est **déclenchée automatiquement** en lisant la carte.
- **Analyser la NVS de la carte** - force une nouvelle lecture de la partition
  NVS (lecture seule) et régénère le rapport.

L'analyse affiche :

- un **Résumé des données détectées** avec trois colonnes :
  - *Paramètre* (ex. « Compteur de démarrages ») ;
  - *Valeur brute* (les octets tels que stockés) ;
  - *Valeur lisible* (décodée : `41`, `640`, `chaîne (36 octets)`…) ;
- des informations sur le fichier analysé et ses pages ;
- le **détail des entrées** (repliable), avec la valeur lisible de chacune.

> 🔒 **Secrets non stockés.** Pour ne jamais conserver de secret (ni de copie
> résiduelle), ESP32-Lab n'enregistre **aucun octet brut NVS** en base : seule
> la structure est gardée. Quand tu **charges depuis la base**, les valeurs
> décodées (SSID, canal…) apparaissent donc « (non stocké en base) », et les
> mots de passe « Présent (masqué) ». Une **lecture live** sur la carte
> (« Analyser la NVS de la carte ») affiche, elle, toutes les valeurs décodées.

## Onglet Partitions Flash

Cet onglet regroupe deux lectures **réelles** de la puce Flash (lecture seule).

![Onglet Partitions Flash : SFDP, identifiant unique et table de partitions](images/04-partitions-flash.png)

### Puce Flash (SFDP & identifiant unique)
Clique sur **Lire les détails de la Flash (SFDP)**. Le SFDP (JESD216) est une
table gravée par le fabricant décrivant la puce :

- fabricant et référence (identifiant JEDEC) ;
- **densité réelle**, adressage (3 ou 4 octets) ;
- **granularités d'effacement** disponibles (4/32/64 Kio) avec leurs opcodes ;
- **modes de lecture rapide** supportés (dual, quad, DTR) ;
- les tables de paramètres SFDP ;
- l'**identifiant unique 64 bits** propre à cette puce Flash.

### Partitionnement de la mémoire Flash

La Flash est découpée en **partitions** (application, données, système de
fichiers…). Cette section lit **réellement** cette organisation sur la carte.

1. Sélectionne le port (onglet Général).
2. Clique sur **Lire la table de partitions**.

> Comme pour les eFuses, un bouton **Charger depuis la base** réaffiche la
> dernière lecture SFDP et la dernière table de partitions enregistrées, **sans
> la carte branchée**.

La lecture (en **lecture seule**, à l'adresse `0x8000`) affiche :

- une **barre colorée** proportionnelle à la taille de chaque partition ;
- un **tableau** : nom, adresse, taille, type, fin, et si la partition est
  chiffrée.

> La lecture redémarre brièvement la carte (comportement normal d'esptool).

## Onglet GPIO Inspector

Cet onglet décrit les **GPIO au niveau de la puce**, calculés d'après la
**famille exacte** détectée lors du scan (ESP32, ESP32-S3, ESP32-C3, ESP32-C6,
ESP32-S2, ESP32-H2). Les informations dépendent de la famille : jamais de table
générique. Lecture seule.
Fais d'abord un **scan** dans l'onglet Général.

![Onglet GPIO Inspector : base Espressif locale, résumé, tableau des broches et sections repliables](images/06-gpio-inspector.png)

> **Exposition sur la carte : à confirmer.** L'accessibilité réelle des broches
> sur les connecteurs (bouton BOOT, LED, écran, USB natif du fabricant) dépend
> du **modèle de carte** et n'est pas déductible de la puce. Cette page décrit
> les capacités et restrictions **du silicium**, pas le brochage d'une carte
> précise.

### Base Espressif locale
Un encart en haut de l'onglet indique la base de références utilisée :

- **version du jeu**, **date de dernière synchronisation**, **source**
  (datasheets Espressif, base curée ESP32-Lab), familles couvertes et statut
  (disponible **hors ligne**, intègre) ;
- **Utiliser les données locales** : affiche les GPIO à partir de la base locale
  (aucun réseau) ;
- **Actualiser depuis Espressif** : télécharge une version mise à jour du jeu
  curé depuis le canal du projet, avec contrôle d'intégrité et sauvegarde de la
  version précédente. En cas d'échec (réseau, intégrité), la base locale est
  **conservée**.

### Résumé et tableau
Un résumé chiffré classe les broches en trois statuts : **Disponible**,
**Disponible avec restrictions**, **À éviter / réservé**. Le tableau détaille
chaque broche : numéro, classification, statut (badge coloré), fonctions
(strapping, entrée seule, Flash/PSRAM, USB-JTAG, ADC, DAC) et notes (dont
l'avertissement de boot pour les broches de strapping).

Des **filtres** (Strapping, Flash/PSRAM, Fonctions spéciales, Entrée seule)
permettent de n'afficher que les broches concernées.

### Profils de cartes (exposition réelle)
Sous le résumé, un menu **« Carte »** (filtré par la famille détectée) permet de
choisir ton **modèle exact** (ESP32-DevKitC, ESP32-S3-DevKitC-1 v1.0/v1.1 et
sa variante N16R8 Octal, ESP32-C3-DevKitM-1, Seeed XIAO ESP32-S3/C3, ESP32-C3
SuperMini, ESP32-S3 SuperMini/Zero N4R2, uPesy ESP32-S3 N16R8). Le tableau gagne
alors une colonne
**« Sur la carte »** qui indique, pour chaque broche, si elle est :

- **utilisée par une fonction embarquée** (bouton BOOT, LED, USB natif, pont
  USB-UART) ;
- **exposée sur un connecteur** (libre d'emploi côté carte) ;
- **non exposée** (présente sur la puce mais pas sortie sur cette carte).

Un filtre **« Exposées sur la carte »** masque les broches non accessibles. Le
choix est **mémorisé sur la fiche de la carte** (par MAC) : il est rappelé au
prochain scan et suit l'export/import vers un autre poste. La source officielle
et une éventuelle **note de révision** (ex. LED sur GPIO48 en v1.0, GPIO38 en
v1.1) sont affichées sous le menu.

> Le modèle n'est pas détecté automatiquement (l'USB ne permet pas d'identifier
> la carte de façon fiable) : c'est à toi de le choisir une fois. En revanche, le
> scan **rattrape** un mauvais choix : si une **PSRAM Octal** est détectée alors
> que le profil choisi suppose GPIO33-37 libres (config quad), un avertissement
> rouge te prévient que ces broches sont en réalité réservées sur ta carte.

### Restrictions à connaître (sections repliables)
Sous le tableau, des sections repliables regroupent, avec un avertissement
explicite, les broches sensibles : **strapping** (lues au reset, fixent le mode
de boot), **Flash/PSRAM** (à ne pas réaffecter sans connaître le matériel) et
**interfaces système** (UART console, USB-JTAG).

## Onglet Firmware & OTA

Cet onglet lit, **en lecture seule**, le firmware réellement présent dans la
Flash et l'état des mises à jour **OTA**. Fais d'abord un scan (ou sélectionne le
port dans Général).

![Onglet Firmware & OTA : état OTA et identité des applications](images/07-firmware-ota.png)

Deux boutons : **« Lire le firmware »** (lecture sur la carte, quelques secondes,
plusieurs zones Flash) et **« Charger depuis la base »** (réaffiche la dernière
lecture enregistrée, sans la carte).

### OTA
Indique le **slot sélectionné au démarrage** (`factory`, `ota_0`, `ota_1`…) et,
pour chacune des deux entrées `otadata`, sa séquence, son état et la validité du
CRC.

> C'est le slot que le **bootloader choisira au prochain démarrage**, pas
> forcément le firmware **en cours d'exécution** (indéductible sans interroger la
> carte en fonctionnement).

### Applications
Pour chaque partition applicative, l'identité lue dans `esp_app_desc` : **nom du
projet**, **version**, **version ESP-IDF**, **date et heure de compilation**,
compteur **anti-rollback** (`secure_version`) et **sha256 de l'ELF**. Un slot non
programmé apparaît « vide », une partition chiffrée « illisible ».

## Onglet Inventaire

Regroupe tout l'historique de tes cartes, en trois sections.

![Onglet Inventaire : registre des cartes, historique et maintenance de la base](images/05-inventaire.png)

### 1. Cartes enregistrées
Le **registre** de toutes les cartes déjà vues. Colonnes : nom, MAC, modèle,
emplacement, dernière détection, **nombre de scans**, et actions :

- **Modifier** - édite la fiche de la carte.
- **Détails** - ouvre une fenêtre avec toutes les caractéristiques connues. On y
  trouve aussi **Suivi des secrets** (voir ci-dessous).
- **Comparer les scans** - compare deux scans de **cette même carte** (actif
  seulement à partir de 2 scans).
- **Supprimer** - retire **définitivement** la carte et toutes ses lectures de
  la base (une confirmation est demandée).
- **Rapport** - ouvre un **rapport HTML autonome** de la carte (identité, bilan
  de sécurité, Flash/SFDP, partitions, structure NVS, GPIO, firmware). Hors
  ligne, **sans aucun secret**, à enregistrer et partager.

#### Suivi des secrets (détection de changement)
Dans la fenêtre **Détails**, le bouton **Suivi des secrets** compare, entre les
**deux dernières analyses** d'une carte, l'**empreinte** de chaque secret (mot
de passe Wi-Fi, clé eFuse provisionnée) pour dire s'il a **changé** - sans jamais
stocker le secret lui-même. Cinq verdicts : *inchangé*, *changé*, *nouveau*,
*disparu*, et *indéterminable* (quand les deux analyses viennent de postes
différents, dont les empreintes ne sont pas comparables).

Un champ de recherche filtre la liste.

### 2. Historique des inventaires
Tous les scans réalisés, la dernière détection par carte. Ici tu peux :

- **cocher deux scans** puis **Comparer les inventaires** ;
- **Exporter en CSV** l'historique complet ;
- afficher **uniquement les différences** dans la comparaison.

### 3. Comparaison de scans
Affiche le résultat côte à côte de deux scans : chaque caractéristique est
marquée **Identique** (vert) ou **Différent** (rouge). Pratique pour repérer un
changement de mémoire, de firmware détecté, etc.

### 4. Comparaison complète de deux cartes
Choisis **deux cartes différentes** dans les listes déroulantes puis
**Comparer les cartes**. ESP32-Lab confronte toutes les données enregistrées en
base (identification, eFuses/sécurité, SFDP, partitions), groupe par groupe.
Des badges indiquent quelles sections ont déjà été capturées pour chaque carte
(scanne et lis les eFuses/SFDP/partitions/NVS d'une carte pour enrichir la
comparaison).

### 5. Maintenance de la base de données
Quatre outils :

- **Exporter la base** - télécharge un fichier JSON portable contenant toutes
  les cartes et toutes les lectures. Idéal pour sauvegarder ou **changer de
  poste** (l'échange fonctionne y compris entre Windows et Raspberry Pi).
- **Importer une base** - fusionne un export dans la base actuelle, sans
  doublon ni écrasement des noms. Le résultat s'affiche dans la section.
- **Vérifier la base** - contrôle d'intégrité + statistiques (nombre de cartes,
  de lectures, taille du fichier).
- **Remettre à zéro** - efface **définitivement** toutes les données (une
  confirmation est demandée ; pense à exporter avant).

> **Changer de poste** : l'export/import **et** la copie du fichier
> `data/esp32lab.db` fonctionnent tous les deux. Aucun des deux ne contient de
> secret (mots de passe, clés) : ils ne sont **jamais stockés**, seulement une
> empreinte pour détecter un changement. Cette empreinte est calculée avec une
> **clé propre à chaque installation** (hors base) : après un transfert vers un
> autre poste, la détection de changement se rebase simplement au prochain scan.
> Rien à faire de spécial, et aucun secret ne circule.
>
> Tout le contenu des sections (identification, eFuses, SFDP, partitions,
> structure NVS) est transféré à l'identique et se réaffiche depuis la base sur
> le nouveau poste. Seuls les **octets bruts NVS** ne sont pas conservés (pour
> ne laisser passer aucun secret) : leurs valeurs décodées ne réapparaissent
> qu'en **relisant la carte**.

## Sécurité et confidentialité

ESP32-Lab est conçu pour ne rien exposer de sensible :

- **Lecture seule.** Aucune écriture sur la carte : pas de flash, pas de
  modification d'eFuse. La table de partitions et la NVS sont seulement **lues**.
- **Aucun secret stocké.** Les mots de passe Wi-Fi et les clés eFuse ne sont
  **jamais enregistrés** en base. À la place, une **empreinte HMAC-SHA-256** est
  conservée : elle permet de détecter un changement (voir « Suivi des secrets »)
  sans jamais garder la valeur. L'empreinte est calculée avec une **clé propre à
  l'installation**, rangée hors de la base (jamais versionnée, jamais exportée).
- **Aucun octet brut NVS en base.** Comme la NVS est un journal où d'anciennes
  valeurs subsistent, ESP32-Lab ne stocke **aucun dump hexadécimal** NVS : cela
  garantit qu'aucune copie résiduelle de mot de passe ou de SSID ne traîne dans
  la base ni dans un export. La contrepartie : la vue **NVS « depuis la base »**
  n'affiche que la structure (« non stocké en base ») ; une **lecture live** sur
  la carte montre, elle, toutes les valeurs décodées.
- **Export/sauvegarde sans risque.** Un export de base ou une copie de
  `data/esp32lab.db` ne peut donc pas divulguer de secret.

## Astuce

Pour comparer l'évolution d'une carte dans le temps : scanne-la aujourd'hui,
puis à nouveau plus tard, et utilise **Comparer les scans** dans l'onglet
Inventaire.

➡️ Un souci ? [Dépannage](depannage.md)
