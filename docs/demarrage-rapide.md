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

- **Analyse NVS** — examine les réglages stockés par l'ESP32 (nécessite un
  rapport NVS ; voir [le guide de l'interface](guide-interface.md#onglet-analyse-nvs)).
- **Partitions Flash** — clique sur « Lire la table de partitions » pour lire
  **réellement** l'organisation de la Flash sur la carte.
- **Inventaire** — retrouve toutes tes cartes, l'historique des scans, et
  compare deux scans entre eux.

## Et ensuite ?

- Donne un **nom** et un **emplacement** à ta carte : onglet Général → section
  « Fiche de la carte » → *Enregistrer la fiche*.
- Refais un scan plus tard et **compare** les deux (onglet Inventaire →
  « Comparer les scans »).

➡️ Pour tout comprendre : [Guide de l'interface](guide-interface.md)
