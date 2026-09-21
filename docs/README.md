# Documentation ESP32-Lab

![Version](https://img.shields.io/badge/version-0.10.0-blue)
![Cibles](https://img.shields.io/badge/cibles-ESP32--S3%20%7C%20ESP32--C3-orange)
![Mode](https://img.shields.io/badge/mat%C3%A9riel-lecture%20seule-success)

Bienvenue ! Cette documentation est pensée pour les **débutants**. Elle
t'accompagne pas à pas, du branchement de la carte à l'analyse de ses données.

## Par où commencer

1. [Installation](installation.md) - installer Python, les dépendances et
   préparer le serveur (Raspberry Pi ou Windows).
2. [Démarrage rapide](demarrage-rapide.md) - lancer le serveur et faire ton
   premier scan en 5 minutes.
3. [Guide de l'interface](guide-interface.md) - à quoi sert chaque onglet et
   chaque bouton.
4. [Dépannage](depannage.md) - les erreurs courantes et comment les résoudre.

## Pour aller plus loin

- [Architecture du projet](architecture.md) - comment le code est organisé
  (utile si tu veux modifier ou contribuer).

## Rappels de sécurité

ESP32-Lab est un outil **non destructif** et **respectueux de tes secrets** :

- il ne modifie jamais la carte (pas d'écriture Flash, pas de changement d'eFuse) ;
- la lecture de la table de partitions et de la NVS se fait en **lecture seule** ;
- aucune donnée n'est effacée automatiquement ;
- **aucun secret n'est stocké** : mots de passe Wi-Fi et clés ne sont jamais
  enregistrés en base (seule une **empreinte** sert à détecter un changement),
  et aucun octet brut NVS n'est conservé. Un export ou une sauvegarde ne peut
  donc pas divulguer de mot de passe.

Tu peux donc explorer sans crainte d'abîmer ta carte ni d'exposer tes réseaux.
Détails : [Guide de l'interface, section Sécurité](guide-interface.md#sécurité-et-confidentialité).

## Vocabulaire utile

| Terme | Signification |
|-------|---------------|
| **SoC** | Le microcontrôleur lui-même (ex. ESP32-S3). |
| **Flash** | La mémoire de stockage du programme (ex. 16 Mo). |
| **PSRAM** | Mémoire vive supplémentaire, présente sur certains modèles. |
| **Partition** | Une zone réservée de la Flash (application, données, etc.). |
| **NVS** | *Non-Volatile Storage* : petit espace où l'ESP32 range des réglages (Wi-Fi, compteurs…). |
| **MAC** | Identifiant matériel unique de la carte (ex. `aa:bb:cc:00:11:22`). |
| **eFuse** | Fusible gravé une fois dans le silicium (identité, sécurité, MAC). |
| **SFDP** | Table normalisée décrivant la puce Flash (densité, effacement…). |
| **Inventaire** | Un « instantané » des caractéristiques d'une carte à un moment donné. |
