#!/usr/bin/env bash
#
# Lancement d'ESP32-Lab sous Linux / Raspberry Pi.
#
# - Vérifie le projet et l'environnement virtuel.
# - Démarre le serveur web.
# - Affiche les adresses d'accès (locale, IP réseau, nom mDNS).
# - N'ouvre un navigateur QUE si une session graphique est présente.
#   Sur un Pi sans écran, aucune erreur : les adresses à saisir depuis un
#   autre poste sont simplement affichées.

set -e

PROJECT_DIR="$HOME/Codage/Python/ESP32-Lab"
PORT=8765

if [ ! -d "$PROJECT_DIR" ]; then
    echo "Erreur : dossier du projet introuvable :"
    echo "  $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

PYTHON="$PROJECT_DIR/.venv/bin/python"

if [ ! -x "$PYTHON" ]; then
    echo "Erreur : environnement virtuel Python introuvable :"
    echo "  $PYTHON"
    echo "Crée-le avec :"
    echo "  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

export PYTHONPATH="$PROJECT_DIR/src"

# --- Adresses d'accès (non bloquant si indisponible) ----------------------
LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}')" || LAN_IP=""
if [ -z "$LAN_IP" ]; then
    LAN_IP="$(ip -4 -o addr show scope global 2>/dev/null \
        | awk '{print $4}' | cut -d/ -f1 | head -n1)" || LAN_IP=""
fi
HOST_NAME="$(hostname 2>/dev/null)" || HOST_NAME=""

# --- Démarrage du serveur -------------------------------------------------
"$PYTHON" -m web.server &
SERVER_PID=$!

echo ""
echo "ESP32-Lab démarré (PID : $SERVER_PID)"
echo "-------------------------------------------------------------"
echo "  Sur cette machine    : http://127.0.0.1:$PORT"
if [ -n "$LAN_IP" ]; then
    echo "  Depuis un autre poste: http://$LAN_IP:$PORT"
fi
if [ -n "$HOST_NAME" ]; then
    echo "                     ou: http://$HOST_NAME.local:$PORT   (si mDNS/Bonjour actif)"
fi
echo "-------------------------------------------------------------"
echo "  Ctrl+C pour arrêter."
echo ""

# --- Ouverture du navigateur (uniquement en session graphique) ------------
if [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; then
    sleep 3
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "http://127.0.0.1:$PORT" >/dev/null 2>&1 &
    elif command -v sensible-browser >/dev/null 2>&1; then
        sensible-browser "http://127.0.0.1:$PORT" >/dev/null 2>&1 &
    fi
else
    echo "Pas d'écran/session graphique détecté (Pi headless) :"
    echo "ouvre l'une des adresses ci-dessus depuis le navigateur d'un autre poste."
    echo ""
fi

# Conserver le serveur au premier plan et relayer ses messages.
wait "$SERVER_PID"
