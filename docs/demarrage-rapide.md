# Démarrage rapide

Objectif : faire ton **premier scan** d'une carte ESP32 en quelques minutes.

> Tu n'as pas encore installé le projet ? Va d'abord voir
> [Installation](installation.md).

## 1. Lancer le serveur

Dans un terminal, depuis le dossier du projet :

```bash
PYTHONPATH=src .venv/bin/python -m web.server
```

Laisse ce terminal ouvert : le serveur y tourne. Pour l'arrêter plus tard,
fais `Ctrl+C`.

## 2. Ouvrir l'interface

Dans un navigateur, va sur :

```
http://localhost:8765
```

(ou `http://IP_DU_RASPBERRY:8765` depuis un autre appareil du réseau).

## 3. Choisir le port

En haut de la page, un menu déroulant liste les ports détectés. Sélectionne
celui de ta carte, par exemple `/dev/ttyACM0 - USB JTAG/serial debug unit`.

Les détails du port (fabricant, numéro de série…) s'affichent juste en dessous.

> Le menu est vide ? Clique sur **« Actualiser les ports »**. Toujours rien ?
> Voir [Dépannage](depannage.md#aucun-port-détecté).

## 4. Scanner la carte

Clique sur **« Scanner la carte »**.

ESP32-Lab interroge la carte via esptool et affiche, dans l'onglet **Général** :

- le microcontrôleur (puce, révision, fréquence CPU, quartz) ;
- la mémoire Flash (taille, fabricant, référence, type, tension) ;
- la PSRAM ;
- la connectivité (Wi-Fi / Bluetooth, adresse MAC) ;
- le port et la date du scan.

Le scan est aussi **enregistré dans l'historique** et la carte est ajoutée au
**registre** (onglet Inventaire).

## 5. Explorer les autres onglets

- **Identité & Sécurité** : clique sur « Lire les eFuses » pour révéler
  l'identité profonde de la puce (identifiant unique, posture de sécurité, MAC
  universelles). « Charger depuis la base » réaffiche la dernière lecture sans la
  carte.
- **Analyse NVS** : examine les réglages stockés par l'ESP32. « Charger
  l'analyse NVS » lit la dernière analyse de la carte en base (et la déclenche si
  besoin) ; « Analyser la NVS de la carte » force une nouvelle lecture.
- **Partitions Flash** : clique sur « Lire la table de partitions » pour lire
  **réellement** l'organisation de la Flash (et le SFDP de la puce). Là aussi,
  « Charger depuis la base » évite d'avoir la carte sous la main.
- **GPIO Inspector** : affiche les GPIO **au niveau de la puce** d'après la
  famille détectée (strapping, entrée seule, Flash/PSRAM, USB-JTAG, ADC…), avec
  filtres et avertissements de boot. Données Espressif locales, disponibles hors
  ligne. Choisis ton **modèle de carte** pour voir l'exposition réelle des broches.
- **Firmware & OTA** : « Lire le firmware » affiche l'identité du firmware présent
  (nom du projet, version, version ESP-IDF, date de compilation, sha256) et le
  slot OTA sélectionné au démarrage.
- **Inventaire** : retrouve toutes tes cartes, l'historique des scans, compare
  deux scans (ou deux cartes), et gère la base (export/import, suppression).

> 🔒 **Tes secrets restent chez toi.** Les mots de passe Wi-Fi et les clés ne
> sont **jamais enregistrés** : seule une empreinte est conservée pour détecter
> un changement. Rien de sensible ne part dans un export ou une sauvegarde.

## Et ensuite ?

- Donne un **nom** et un **emplacement** à ta carte : onglet Général, section
  « Fiche de la carte », *Enregistrer la fiche*.
- Refais un scan plus tard et **compare** les deux (onglet Inventaire,
  « Comparer les scans »).
- Repère un secret modifié entre deux scans avec **« Suivi des secrets »**
  (bouton dans la fiche détaillée d'une carte).

➡️ Pour tout comprendre : [Guide de l'interface](guide-interface.md)
