"""
Serveur Web ESP32-Lab.
"""

import json

from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from core import database, morfbeacon
from core.comparison import compare_devices
from core.secret_changes import detect_changes
from core.device_registry import (
    get_device,
    get_devices,
    update_device,
    update_device_from_inventory,
)
from core import espressif_dataset
from core.esp32_efuse import read_efuses
from core.esp32_firmware import read_firmware
from core.esp32_flash_sfdp import read_flash_details
from core.esp32_gpio import compute_gpio_map
from core.esp32_inventory import create_inventory, save_inventory
from core.esp32_nvs import read_and_analyze_nvs
from core.esp32_partitions import read_partition_table
from core.report import build_report, render_report_html
from core.secret_redaction import (
    sanitize_efuse_for_storage,
    sanitize_nvs_for_storage,
)
from core.inventory_history import get_history, save_history
from core.inventory_store import load_last_inventory
from transport.serial_detect import detect_serial_ports


# Garantit l'existence de la base (schéma + migration) dès l'import.
database.init_db()

# Copie le jeu de references Espressif vers le cache local si absent (hors ligne,
# aucun accès réseau : le jeu curé est livré avec l'application).
espressif_dataset.ensure_local_dataset()


HOST = "0.0.0.0"
PORT = 8765
PORT_ATTEMPTS = 20   # 8765..8784 si le port par défaut est occupé
STATIC_DIRECTORY = Path(__file__).resolve().parent / "static"
VERSION_FILE = Path(__file__).resolve().parents[2] / "VERSION"

# Port réellement utilisé (résolu au démarrage). Par défaut, le port préféré.
ACTIVE_PORT = PORT


def read_version():
    """Lit la version du projet depuis le fichier VERSION."""

    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return "dev"


APP_VERSION = read_version()

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".png": "image/png",
}


class ESP32LabHandler(BaseHTTPRequestHandler):
    """Gestionnaire des requêtes HTTP."""

    def send_json(self, data, status=200):
        """Envoie une réponse JSON."""

        payload = json.dumps(
            data,
            indent=4,
            ensure_ascii=False,
        ).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def read_json_body(self):
        """Lit le corps JSON de la requête."""

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        if not body:
            return {}

        return json.loads(body.decode("utf-8"))

    def do_GET(self):
        """Traite les requêtes GET."""

        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/":
            self.serve_static_file("index.html")
            return

        if path.startswith("/css/") or path.startswith("/js/"):
            self.serve_static_file(path.lstrip("/"))
            return

        if path == "/favicon.ico":
            self.serve_static_file("favicon.ico")
            return

        if path == "/api/health":
            self.send_json({
                "status": "ok",
                "service": "ESP32-Lab",
                "version": APP_VERSION,
                "port": ACTIVE_PORT,
            })
            return

        if path == "/healthz":
            # Liveness minimale (contrat morfBeacon).
            self.send_json({"status": "ok"})
            return

        if path == "/status":
            self.send_json(self.build_status())
            return

        if path == "/api/ports":
            self.send_json({
                "status": "ok",
                "ports": detect_serial_ports(),
            })
            return

        if path == "/api/nvs":
            report_path = (
                Path(__file__).resolve().parents[2]
                / "data"
                / "analysis"
                / "reports"
                / "nvs_structure_analysis.json"
            )

            if not report_path.exists():
                self.send_json({
                    "status": "error",
                    "message": "Rapport NVS indisponible.",
                }, status=404)
                return

            try:
                report = json.loads(
                    report_path.read_text(encoding="utf-8")
                )
                self.send_json({
                    "status": "ok",
                    "report": report,
                })
            except (OSError, json.JSONDecodeError) as error:
                self.send_json({
                    "status": "error",
                    "message": f"Lecture du rapport NVS impossible : {error}",
                }, status=500)

            return

        if path == "/api/inventory":
            inventory = load_last_inventory()

            if inventory is None:
                self.send_json({
                    "status": "error",
                    "message": "Aucun inventaire disponible.",
                }, status=404)
                return

            self.send_json(inventory)
            return

        if path == "/api/inventory/history":
            self.send_json({
                "status": "ok",
                "history": get_history(),
            })
            return

        if path == "/api/devices":
            self.send_json({
                "status": "ok",
                "devices": get_devices(),
            })
            return

        if path == "/api/device":
            mac = query.get("mac", [None])[0]
            device = get_device(mac)

            self.send_json({
                "status": "ok",
                "device": device,
            })
            return

        if path == "/api/db/device":
            mac = query.get("mac", [None])[0]
            dossier = database.get_device_dossier(mac) if mac else None

            if dossier is None:
                self.send_json({
                    "status": "error",
                    "message": "Carte introuvable.",
                }, status=404)
                return

            self.send_json({
                "status": "ok",
                "dossier": dossier,
            })
            return

        if path == "/api/db/reading":
            mac = query.get("mac", [None])[0]
            section = query.get("section", [None])[0]

            if not mac or not section:
                self.send_json({
                    "status": "error",
                    "message": "Les paramètres mac et section sont requis.",
                }, status=400)
                return

            reading = database.get_latest_reading(mac, section)
            self.send_json({
                "status": "ok",
                "reading": reading,
            })
            return

        if path == "/api/db/compare":
            mac_a = query.get("mac_a", [None])[0]
            mac_b = query.get("mac_b", [None])[0]
            result = compare_devices(mac_a, mac_b)

            status = 200 if result.get("status") == "ok" else 400
            self.send_json(result, status=status)
            return

        if path == "/api/db/changes":
            mac = query.get("mac", [None])[0]
            result = detect_changes(mac)

            status = 200 if result.get("status") == "ok" else 404
            self.send_json(result, status=status)
            return

        if path == "/api/gpio":
            chip = query.get("chip", [None])[0]
            board = query.get("board", [None])[0]
            psram = query.get("psram", [None])[0]
            result = compute_gpio_map(chip, board=board, psram_size=psram)

            status = 200 if result.get("status") == "ok" else 400
            self.send_json(result, status=status)
            return

        if path == "/api/boards":
            family = query.get("family", [None])[0]
            self.send_json({
                "status": "ok",
                "boards": espressif_dataset.boards_for_family(family),
            })
            return

        if path == "/api/espressif/status":
            self.send_json(espressif_dataset.dataset_status())
            return

        if path == "/api/report":
            mac = query.get("mac", [None])[0]
            report = build_report(mac) if mac else None
            html_page = render_report_html(report)
            payload = html_page.encode("utf-8")

            self.send_response(200 if report else 404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)
            return

        if path == "/api/db/export":
            self.send_json(database.export_all())
            return

        if path == "/api/db/verify":
            self.send_json(database.verify_database())
            return

        self.send_json({
            "status": "error",
            "message": "Route inconnue.",
        }, status=404)

    def do_POST(self):
        """Traite les requêtes POST."""

        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/api/inventory/refresh":
            self.refresh_inventory(query)
            return

        if path == "/api/partitions":
            self.read_partitions(query)
            return

        if path == "/api/efuse":
            self.read_efuse(query)
            return

        if path == "/api/flash":
            self.read_flash(query)
            return

        if path == "/api/nvs/analyze":
            self.analyze_nvs(query)
            return

        if path == "/api/firmware":
            self.read_firmware_handler(query)
            return

        if path == "/api/device/update":
            self.update_device()
            return

        if path == "/api/device/delete":
            self.delete_device_handler()
            return

        if path == "/api/device/board":
            self.set_device_board()
            return

        if path == "/api/db/import":
            self.import_db()
            return

        if path == "/api/espressif/refresh":
            self.refresh_espressif()
            return

        if path == "/api/db/reset":
            try:
                self.send_json(database.reset_database())
            except Exception as error:
                self.send_json({
                    "status": "error",
                    "message": str(error),
                }, status=500)
            return

        self.send_json({
            "status": "error",
            "message": "Route inconnue.",
        }, status=404)

    def delete_device_handler(self):
        """Supprime une carte de l'inventaire et toutes ses lectures."""

        try:
            data = self.read_json_body()
            mac = data.get("mac")

            if not mac:
                self.send_json({
                    "status": "error",
                    "message": "L'adresse MAC est obligatoire.",
                }, status=400)
                return

            result = database.delete_device(mac)

            if result is None:
                self.send_json({
                    "status": "error",
                    "message": "Carte introuvable.",
                }, status=404)
                return

            result["message"] = "Carte supprimée."
            self.send_json(result)
        except Exception as error:
            self.send_json({
                "status": "error",
                "message": str(error),
            }, status=500)

    def set_device_board(self):
        """Enregistre le profil de carte choisi pour une carte (par MAC)."""

        try:
            data = self.read_json_body()
            mac = data.get("mac")

            if not mac:
                self.send_json({
                    "status": "error",
                    "message": "L'adresse MAC est obligatoire.",
                }, status=400)
                return

            device = database.set_board_profile(mac, data.get("board"))
            self.send_json({
                "status": "ok",
                "message": "Carte enregistrée.",
                "device": device,
            })
        except Exception as error:
            self.send_json({
                "status": "error",
                "message": str(error),
            }, status=500)

    def import_db(self):
        """Importe un export de base (fusion additive)."""

        try:
            payload = self.read_json_body()
            summary = database.import_data(payload)
            self.send_json({
                "status": "ok",
                "message": "Import terminé.",
                "summary": summary,
            })
        except ValueError as error:
            self.send_json({
                "status": "error",
                "message": str(error),
            }, status=400)
        except Exception as error:
            self.send_json({
                "status": "error",
                "message": str(error),
            }, status=500)

    def refresh_espressif(self):
        """Met à jour la base de références Espressif depuis le canal projet."""

        try:
            body = self.read_json_body()
            force = bool(body.get("force")) if isinstance(body, dict) else False
            result = espressif_dataset.refresh_from_channel(force=force)
        except Exception as error:
            self.send_json({
                "status": "error",
                "message": str(error),
            }, status=500)
            return

        # Échec (réseau/intégrité/schéma) : la base locale reste intacte.
        status = 200 if result.get("status") == "ok" else 502
        self.send_json(result, status=status)

    def refresh_inventory(self, query):
        """Actualise l'inventaire d'un port."""

        selected_port = query.get("port", [None])[0]

        if not selected_port:
            self.send_json({
                "status": "error",
                "message": "Le port série est obligatoire.",
            }, status=400)
            return

        available_ports = detect_serial_ports()
        available_devices = [
            port["device"] for port in available_ports
        ]

        if selected_port not in available_devices:
            self.send_json({
                "status": "error",
                "message": "Le port sélectionné n'est pas disponible.",
            }, status=400)
            return

        try:
            inventory = create_inventory(selected_port)

            output_file = save_inventory(inventory)
            history_file = save_history(inventory)
            device = update_device_from_inventory(inventory)

            self.send_json({
                "status": "ok",
                "message": "Inventaire actualisé avec succès.",
                "file": str(output_file),
                "history_file": str(history_file),
                "device": device,
                "inventory": inventory,
            })

        except Exception as error:
            self.send_json({
                "status": "error",
                "message": str(error),
            }, status=500)

    def update_device(self):
        """Met à jour les informations personnalisées d'une carte."""

        try:
            data = self.read_json_body()

            mac = data.get("mac")
            name = data.get("name", "")
            note = data.get("note", "")
            location = data.get("location", "")

            if not mac:
                self.send_json({
                    "status": "error",
                    "message": "L'adresse MAC est obligatoire.",
                }, status=400)
                return

            device = update_device(
                mac=mac,
                name=name,
                note=note,
                location=location,
            )

            self.send_json({
                "status": "ok",
                "message": "Carte enregistrée.",
                "device": device,
            })

        except Exception as error:
            self.send_json({
                "status": "error",
                "message": str(error),
            }, status=500)

    def _persist_section(self, query, section, result, fallback_mac=None):
        """Enregistre une lecture en base si elle a réussi et qu'une MAC existe."""

        if not isinstance(result, dict) or result.get("status") != "ok":
            return

        raw_mac = query.get("mac", [None])[0] or fallback_mac or ""
        mac = raw_mac.split("(")[0].strip()

        if not mac:
            return

        port = query.get("port", [None])[0]

        # Assainit une COPIE avant stockage : les secrets (mots de passe NVS,
        # clés eFuse) ne sont jamais écrits en base, seulement une empreinte.
        # L'objet `result` renvoyé à l'interface reste complet.
        to_store = result
        if section == "nvs":
            to_store = sanitize_nvs_for_storage(result)
        elif section == "efuse":
            to_store = sanitize_efuse_for_storage(result)

        try:
            database.save_reading(mac, section, to_store, port=port)
        except Exception:
            # La persistance ne doit jamais faire échouer la lecture matérielle.
            pass

    def build_status(self):
        """Statut riche (contrat morfBeacon /status)."""

        import socket

        try:
            metrics = database.counts()
        except Exception:
            metrics = {}

        return {
            "app": "ESP32-Lab",
            "version": APP_VERSION,
            "state": "ok",
            "host": socket.gethostname(),
            "port": ACTIVE_PORT,
            "capabilities": morfbeacon.CAPABILITIES,
            "metrics": metrics,
            "api": {
                "endpoints": [
                    {"method": "GET", "path": "/api/devices",
                     "summary": "registre des cartes"},
                    {"method": "GET", "path": "/api/db/compare",
                     "summary": "comparaison de deux cartes"},
                    {"method": "GET", "path": "/api/db/changes",
                     "summary": "détection de changement de secrets"},
                    {"method": "GET", "path": "/api/db/export",
                     "summary": "export de la base"},
                    {"method": "GET", "path": "/api/report",
                     "summary": "rapport HTML d'une carte"},
                    {"method": "GET", "path": "/api/gpio",
                     "summary": "cartographie GPIO calculée"},
                    {"method": "GET", "path": "/api/boards",
                     "summary": "profils de cartes par famille"},
                    {"method": "POST", "path": "/api/device/board",
                     "summary": "choix du profil de carte"},
                    {"method": "GET", "path": "/api/espressif/status",
                     "summary": "état de la base de références Espressif"},
                    {"method": "POST", "path": "/api/espressif/refresh",
                     "summary": "mise à jour de la base Espressif"},
                    {"method": "POST", "path": "/api/inventory/refresh",
                     "summary": "scan d'une carte"},
                    {"method": "POST", "path": "/api/efuse",
                     "summary": "lecture des eFuses"},
                    {"method": "POST", "path": "/api/flash",
                     "summary": "lecture SFDP + identifiant unique"},
                    {"method": "POST", "path": "/api/nvs/analyze",
                     "summary": "analyse NVS"},
                    {"method": "POST", "path": "/api/firmware",
                     "summary": "identité firmware + OTA"},
                ],
            },
        }

    def read_partitions(self, query):
        """Lit la table de partitions réelle de la carte (lecture seule)."""

        selected_port = query.get("port", [None])[0]

        if not selected_port:
            self.send_json({
                "status": "error",
                "message": "Le port série est obligatoire.",
            }, status=400)
            return

        chip = query.get("chip", [None])[0]

        try:
            result = read_partition_table(selected_port, chip=chip)
        except Exception as error:
            self.send_json({
                "status": "error",
                "message": str(error),
            }, status=500)
            return

        self._persist_section(query, "partitions", result)

        status = 200 if result.get("status") == "ok" else 502
        self.send_json(result, status=status)

    def read_efuse(self, query):
        """Lit et analyse les eFuses de la carte (lecture seule)."""

        selected_port = query.get("port", [None])[0]

        if not selected_port:
            self.send_json({
                "status": "error",
                "message": "Le port série est obligatoire.",
            }, status=400)
            return

        chip = query.get("chip", [None])[0]

        try:
            result = read_efuses(selected_port, chip=chip)
        except Exception as error:
            self.send_json({
                "status": "error",
                "message": str(error),
            }, status=500)
            return

        fallback_mac = (result.get("identity") or {}).get("mac")
        self._persist_section(query, "efuse", result, fallback_mac=fallback_mac)

        status = 200 if result.get("status") == "ok" else 502
        self.send_json(result, status=status)

    def read_flash(self, query):
        """Lit le SFDP et l'identifiant unique de la puce Flash (lecture seule)."""

        selected_port = query.get("port", [None])[0]

        if not selected_port:
            self.send_json({
                "status": "error",
                "message": "Le port série est obligatoire.",
            }, status=400)
            return

        chip = query.get("chip", [None])[0]

        try:
            result = read_flash_details(selected_port, chip=chip)
        except Exception as error:
            self.send_json({
                "status": "error",
                "message": str(error),
            }, status=500)
            return

        self._persist_section(query, "sfdp", result)

        status = 200 if result.get("status") == "ok" else 502
        self.send_json(result, status=status)

    def analyze_nvs(self, query):
        """Lit la partition NVS de la carte et génère le rapport (lecture seule)."""

        selected_port = query.get("port", [None])[0]

        if not selected_port:
            self.send_json({
                "status": "error",
                "message": "Le port série est obligatoire.",
            }, status=400)
            return

        chip = query.get("chip", [None])[0]

        try:
            result = read_and_analyze_nvs(selected_port, chip=chip)
        except Exception as error:
            self.send_json({
                "status": "error",
                "message": str(error),
            }, status=500)
            return

        self._persist_section(query, "nvs", result)

        status = 200 if result.get("status") == "ok" else 502
        self.send_json(result, status=status)

    def read_firmware_handler(self, query):
        """Lit l'identite firmware et l'etat OTA de la carte (lecture seule)."""

        selected_port = query.get("port", [None])[0]

        if not selected_port:
            self.send_json({
                "status": "error",
                "message": "Le port série est obligatoire.",
            }, status=400)
            return

        chip = query.get("chip", [None])[0]

        try:
            result = read_firmware(selected_port, chip=chip)
        except Exception as error:
            self.send_json({
                "status": "error",
                "message": str(error),
            }, status=500)
            return

        self._persist_section(query, "firmware", result)

        status = 200 if result.get("status") == "ok" else 502
        self.send_json(result, status=status)

    def serve_static_file(self, relative_path):
        """Sert un fichier statique depuis le dossier ``static``."""

        # Empêche toute remontée de répertoire (path traversal).
        target = (STATIC_DIRECTORY / relative_path).resolve()

        if STATIC_DIRECTORY.resolve() not in target.parents \
                and target != STATIC_DIRECTORY.resolve():
            self.send_json({
                "status": "error",
                "message": "Chemin non autorisé.",
            }, status=403)
            return

        if not target.is_file():
            self.send_json({
                "status": "error",
                "message": f"Fichier introuvable : {relative_path}",
            }, status=404)
            return

        content = target.read_bytes()
        content_type = CONTENT_TYPES.get(
            target.suffix.lower(),
            "application/octet-stream",
        )

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        # Outil local : on désactive le cache pour éviter de servir un ancien
        # HTML/CSS/JS après une mise à jour (fichiers petits, réseau local).
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        """Conserve un affichage simple des requêtes."""

        print(f"[WEB] {self.address_string()} - {format % args}")


def _port_in_use(port):
    """
    Indique si un serveur écoute déjà sur ce port (détection par connexion,
    fiable sous Linux comme Windows, contrairement à un simple bind qui, avec
    SO_REUSEADDR, peut réussir même si le port est déjà pris sous Windows).
    """

    import socket

    target = "127.0.0.1" if HOST == "0.0.0.0" else HOST
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.3)
        return probe.connect_ex((target, port)) == 0


def _bind_server():
    """
    Crée le serveur sur le port préféré, ou le premier port libre suivant si
    celui-ci est déjà occupé. Met à jour ACTIVE_PORT.
    """

    global ACTIVE_PORT

    for candidate in range(PORT, PORT + PORT_ATTEMPTS):
        if _port_in_use(candidate):
            continue
        try:
            server = HTTPServer((HOST, candidate), ESP32LabHandler)
        except OSError:
            continue
        ACTIVE_PORT = candidate
        return server

    raise RuntimeError(
        f"Aucun port libre entre {PORT} et {PORT + PORT_ATTEMPTS - 1}."
    )


def main():
    """Démarre le serveur."""

    try:
        server = _bind_server()
    except RuntimeError as error:
        print(f"Erreur : {error}")
        return

    if ACTIVE_PORT != PORT:
        print(f"Port {PORT} occupé - bascule sur le port {ACTIVE_PORT}.")

    import socket
    host_name = socket.gethostname()

    print(f"ESP32-Lab v{APP_VERSION} - Web disponible sur :")
    print(f"  http://0.0.0.0:{ACTIVE_PORT}")
    print(f"  http://{host_name}.local:{ACTIVE_PORT}   (si mDNS/Bonjour actif)")

    # Annonce morfBeacon (additive : sans réseau, le service tourne pareil).
    morfbeacon.start_heartbeat(APP_VERSION, ACTIVE_PORT)
    print(f"  Annonce morfBeacon sur {morfbeacon.BEACON_PORT}/UDP "
          f"(capacité : {', '.join(morfbeacon.CAPABILITIES)})")
    print("Ctrl+C pour arrêter le serveur.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
