# ESP32-Lab

Laboratoire de diagnostic et de test pour microcontrôleurs ESP32.

## Objectif

Permettre l'identification, l'analyse et le test d'un ESP32 connecté
à un Raspberry Pi.

## Cibles

- ESP32-S3
- ESP32-C3
- Versions avec ou sans PSRAM

## Fonctionnalités prévues

- Détection USB / série
- Identification du SoC
- Analyse mémoire
- Analyse Flash et partitions
- Détection PSRAM
- Cartographie GPIO
- Informations eFuse en lecture seule
- Tests CPU et mémoire
- Tests de communication
- Tests périphériques
- Interface Web
- Historique des diagnostics
- Export JSON / CSV

## Principes

- Aucun effacement automatique
- Aucune modification des eFuses
- Tests non destructifs par défaut
- Séparation entre informations détectées et informations rapportées
- Compatibilité multi-familles ESP32
