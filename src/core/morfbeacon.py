"""
Annonce morfBeacon d'ESP32-Lab.

Contrat morfBeacon (écosystème morfSystem) :
- **Présence** : heartbeat UDP périodique, court, diffusé en broadcast sur le
  port **45454/UDP** (canal commun où tous les services s'annoncent et que
  morfMonitor écoute).
- **Détail** : servi à la demande par les endpoints HTTP ``/status`` et
  ``/healthz`` du service (côté serveur web).

Cette annonce est **purement additive** : ESP32-Lab fonctionne exactement pareil
sans réseau ni morfMonitor. Toute erreur (pas de réseau, socket refusé) est
silencieuse et ne perturbe jamais le service.
"""

import json
import socket
import threading
import time


BEACON_PORT = 45454
BROADCAST_ADDR = "255.255.255.255"
PROTO = "morfbeacon/1"
APP_NAME = "ESP32-Lab"
CAPABILITIES = ["esp32-characterization"]
DEFAULT_INTERVAL = 10   # secondes entre deux heartbeats


def beacon_payload(version, status_port, host, state="ok", now=None):
    """Construit la charge utile d'un heartbeat morfBeacon."""

    return {
        "proto": PROTO,
        "app": APP_NAME,
        "host": host,
        "version": version,
        "state": state,
        "status_port": status_port,
        "instance": f"{APP_NAME}@{host}",
        "capabilities": list(CAPABILITIES),
        "ts": int(now if now is not None else time.time()),
    }


def start_heartbeat(version, status_port, interval=DEFAULT_INTERVAL,
                    state_fn=None):
    """
    Démarre l'émission périodique du heartbeat en tâche de fond (thread démon).

    Retourne un ``threading.Event`` : l'activer arrête l'émission. En cas
    d'impossibilité réseau, l'émission s'arrête silencieusement.
    """

    host = socket.gethostname()
    stop = threading.Event()

    def _run():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except OSError:
            return   # pas de socket UDP disponible : on abandonne en silence

        while not stop.is_set():
            try:
                state = state_fn() if state_fn else "ok"
                payload = beacon_payload(version, status_port, host, state)
                data = json.dumps(payload).encode("utf-8")
                sock.sendto(data, (BROADCAST_ADDR, BEACON_PORT))
            except OSError:
                pass   # erreur ponctuelle (réseau) : on réessaiera au tour suivant

            stop.wait(interval)

        try:
            sock.close()
        except OSError:
            pass

    thread = threading.Thread(target=_run, name="morfbeacon", daemon=True)
    thread.start()
    return stop
