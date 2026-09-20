"""
Serveur Web ESP32-Lab.
"""

import json

from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from core.device_registry import (
    get_device,
    get_devices,
    update_device,
    update_device_from_inventory,
)
from core.esp32_inventory import create_inventory, save_inventory
from core.esp32_partitions import read_partition_table
from core.inventory_history import get_history, save_history
from core.inventory_store import load_last_inventory
from transport.serial_detect import detect_serial_ports


HOST = "0.0.0.0"
PORT = 8765
STATIC_DIRECTORY = Path(__file__).resolve().parent / "static"

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
            })
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

        if path == "/api/device/update":
            self.update_device()
            return

        self.send_json({
            "status": "error",
            "message": "Route inconnue.",
        }, status=404)

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
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        """Conserve un affichage simple des requêtes."""

        print(f"[WEB] {self.address_string()} - {format % args}")


def main():
    """Démarre le serveur."""

    server = HTTPServer((HOST, PORT), ESP32LabHandler)

    print(f"ESP32-Lab Web disponible sur http://0.0.0.0:{PORT}")
    print("Ctrl+C pour arrêter le serveur.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
