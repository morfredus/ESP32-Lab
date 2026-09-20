#!/usr/bin/env bash

set -e

# Repertoire du projet ESP32-Lab
PROJECT_DIR="$HOME/Codage/Python/ESP32-Lab"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "Erreur : dossier du projet introuvable :"
    echo "$PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

# Vérifier l'environnement virtuel
PYTHON="$PROJECT_DIR/.venv/bin/python"

if [ ! -x "$PYTHON" ]; then
    echo "Erreur : environnement virtuel Python introuvable :"
    echo "$PYTHON"
    echo "Crée-le avec : python3 -m venv .venv"
    exit 1
fi

# Configuration Python
export PYTHONPATH="$PROJECT_DIR/src"

# Lancer le serveur en arrière-plan
"$PYTHON" -m web.server &
SERVER_PID=$!

echo "ESP32-Lab lancé (PID : $SERVER_PID)"
echo "Interface : http://127.0.0.1:8765"

# Attendre quelques secondes avant d'ouvrir le navigateur
sleep 3

if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://127.0.0.1:8765" >/dev/null 2>&1 &
elif command -v sensible-browser >/dev/null 2>&1; then
    sensible-browser "http://127.0.0.1:8765" >/dev/null 2>&1 &
else
    echo "Navigateur non détecté. Ouvre manuellement : http://127.0.0.1:8765"
fi

# Conserver le serveur actif et afficher ses messages
wait "$SERVER_PID"
