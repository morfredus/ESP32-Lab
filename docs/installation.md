# Installation

Ce guide part de zéro. Suis les étapes dans l'ordre.

## 1. Ce qu'il te faut

- Un **Raspberry Pi** (ou un PC Linux/Windows) avec **Python 3.10 ou plus récent**.
- Une **carte ESP32** (S3 ou C3) et un **câble USB** de données.
- Un accès au terminal.

Vérifie ta version de Python :

```bash
python3 --version
```

## 2. Récupérer le projet

Place le dossier `ESP32-Lab` là où tu veux, par exemple :

```bash
cd ~/Codage/Python/ESP32-Lab
```

## 3. Créer un environnement virtuel (recommandé)

Un « environnement virtuel » (`.venv`) isole les dépendances du projet du reste
du système. C'est **la méthode conseillée**, surtout sur Raspberry Pi OS.

```bash
python3 -m venv .venv
```

Puis installe les dépendances **dans** cet environnement :

```bash
.venv/bin/pip install -r requirements.txt
```

Les deux dépendances installées sont :

- `pyserial` — pour détecter les ports série ;
- `esptool` — l'outil officiel Espressif qui communique avec l'ESP32.

> ### Erreur « externally-managed-environment » ?
> Sur Raspberry Pi OS récent, `pip install` directement sur le système est
> **bloqué volontairement**. C'est normal. Utilise bien un `.venv` comme
> ci-dessus. Voir [Dépannage](depannage.md#erreur-externally-managed-environment).

## 4. Brancher la carte

Branche l'ESP32 en USB, puis vérifie qu'elle est détectée :

```bash
ls /dev/ttyACM* /dev/ttyUSB*
```

Tu devrais voir apparaître quelque chose comme `/dev/ttyACM0`.

> Sous Windows, la carte apparaît plutôt comme `COM3`, `COM4`, etc.

### Droits d'accès au port (Linux)

Si le port existe mais que la lecture échoue, ton utilisateur doit appartenir
au groupe `dialout` :

```bash
sudo usermod -a -G dialout $USER
```

Déconnecte-toi puis reconnecte-toi pour que ce changement prenne effet.

## 5. Lancer le serveur

```bash
PYTHONPATH=src .venv/bin/python -m web.server
```

Tu devrais voir :

```
ESP32-Lab v0.4.3 — Web disponible sur http://0.0.0.0:8765
Ctrl+C pour arrêter le serveur.
```

Ouvre alors un navigateur sur **http://ADRESSE:8765** (remplace `ADRESSE` par
l'IP du Raspberry Pi, ou `localhost` si tu es sur la même machine).

## Variante : sans environnement virtuel

Le projet fonctionne aussi avec le Python système, **à condition qu'esptool y
soit installé**. ESP32-Lab détecte automatiquement esptool (interpréteur
courant, `.venv` du projet, ou commande `esptool` du PATH). Tu peux donc lancer :

```bash
PYTHONPATH=src python -m web.server
```

## Variante Windows
# 1. Créer l'environnement virtuel
python -m venv .venv

# 2. Installer les dépendances
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 3. Définir le PYTHONPATH pour cette session PowerShell
$env:PYTHONPATH = "src"

# 4. Lancer ESP32-Lab
.\.venv\Scripts\python.exe -m web.server

Même si ce Python n'a pas esptool, le serveur utilisera automatiquement celui
du `.venv` du projet s'il existe.

## Scripts de lancement (raccourcis)

Deux scripts à la racine du projet évitent de retaper les commandes. Ils
vérifient le `.venv`, lancent le serveur et gèrent l'accès.

### Windows — `launch_esp32_lab.bat`

Double-clic (ou `launch_esp32_lab.bat` en ligne de commande). Le serveur démarre
dans une fenêtre dédiée et le navigateur s'ouvre sur http://127.0.0.1:8765.

### Linux / Raspberry Pi — `launch_esp32_lab.sh`

```bash
./launch_esp32_lab.sh
```

Le script affiche les **adresses d'accès** puis :

- **Pi avec écran** : ouvre le navigateur local automatiquement.
- **Pi sans écran (headless)** : n'ouvre rien (pas d'erreur) et **indique les
  adresses à saisir depuis le navigateur d'un autre poste** — l'IP réseau et le
  nom mDNS `<hôte>.local`. Exemple :

  ```
  ESP32-Lab démarré (PID : 1234)
  -------------------------------------------------------------
    Sur cette machine    : http://127.0.0.1:8765
    Depuis un autre poste: http://192.168.1.104:8765
                       ou: http://pi4dev.local:8765   (si mDNS/Bonjour actif)
  -------------------------------------------------------------
  ```

> Le nom `<hôte>.local` fonctionne si le service mDNS (avahi sous Linux,
> Bonjour sous Windows/macOS) est actif sur le réseau. Sinon, utilise l'IP.

Rends le script exécutable la première fois si besoin : `chmod +x launch_esp32_lab.sh`.

## Étape suivante

➡️ [Démarrage rapide : ton premier scan](demarrage-rapide.md)
