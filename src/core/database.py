"""
Base de données SQLite d'ESP32-Lab.

Source de vérité unique pour :
- le registre des cartes (identité + métadonnées utilisateur) ;
- l'historique complet de toutes les lectures (identification, eFuses, SFDP,
  partitions, NVS), conservées telles quelles pour des comparaisons riches.

Migration automatique depuis les anciens fichiers JSON au premier lancement.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "esp32lab.db"

# Sections de lecture reconnues.
SECTIONS = ("inventory", "efuse", "sfdp", "partitions", "nvs")

# Champs techniques d'identification conservés sur la fiche carte (compat).
IDENTIFICATION_FIELDS = (
    "chip", "chip_family", "revision", "features",
    "cpu_frequency_mhz", "psram", "psram_size_mb", "crystal_frequency_mhz",
    "flash_manufacturer", "flash_manufacturer_name",
    "flash_device", "flash_device_name",
    "flash_size_mb", "flash_type", "flash_voltage", "mac",
)


SCHEMA = """
CREATE TABLE IF NOT EXISTS devices (
    mac TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    location TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    first_seen TEXT,
    last_seen TEXT,
    port TEXT,
    identification TEXT
);

CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mac TEXT NOT NULL,
    section TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    port TEXT,
    payload TEXT NOT NULL,
    FOREIGN KEY (mac) REFERENCES devices(mac)
);

CREATE INDEX IF NOT EXISTS idx_readings_lookup
    ON readings(mac, section, recorded_at);
"""


def _now():
    return datetime.now(timezone.utc).isoformat()


def connect():
    """Ouvre une connexion SQLite (dossier data/ créé au besoin)."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    """Crée le schéma et migre les anciens JSON si nécessaire."""

    with connect() as connection:
        connection.executescript(SCHEMA)
        count = connection.execute(
            "SELECT COUNT(*) FROM devices"
        ).fetchone()[0]

    if count == 0:
        migrate_from_json()


# --- Cartes ---------------------------------------------------------------

def _row_to_device(row):
    """Convertit une ligne devices en dictionnaire (compat historique)."""

    device = {
        "mac": row["mac"],
        "name": row["name"],
        "location": row["location"],
        "note": row["note"],
        "first_seen": row["first_seen"],
        "last_seen": row["last_seen"],
        "port": row["port"],
    }

    if row["identification"]:
        try:
            identification = json.loads(row["identification"])
        except (TypeError, json.JSONDecodeError):
            identification = {}
        for field in IDENTIFICATION_FIELDS:
            if field in identification:
                device[field] = identification[field]

    return device


def get_device(mac):
    """Retourne la fiche d'une carte, ou None."""

    if not mac:
        return None

    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM devices WHERE mac = ?", (mac.lower(),)
        ).fetchone()

    return _row_to_device(row) if row else None


def get_devices():
    """Retourne toutes les cartes (dict indexé par MAC)."""

    with connect() as connection:
        rows = connection.execute("SELECT * FROM devices").fetchall()

    return {row["mac"]: _row_to_device(row) for row in rows}


def update_device(mac, name="", note="", location=""):
    """Crée ou met à jour les métadonnées utilisateur d'une carte."""

    if not mac:
        raise ValueError("L'adresse MAC est obligatoire.")

    mac = mac.lower()
    now = _now()

    with connect() as connection:
        connection.execute(
            """
            INSERT INTO devices (mac, name, note, location, first_seen)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(mac) DO UPDATE SET
                name = excluded.name,
                note = excluded.note,
                location = excluded.location
            """,
            (mac, name.strip(), note.strip(), location.strip(), now),
        )
        connection.commit()

    return get_device(mac)


def ensure_device(mac, port=None, seen_at=None):
    """Garantit l'existence d'une carte et met à jour sa dernière détection."""

    mac = mac.lower()
    seen_at = seen_at or _now()

    with connect() as connection:
        connection.execute(
            """
            INSERT INTO devices (mac, first_seen, last_seen, port)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(mac) DO UPDATE SET
                last_seen = excluded.last_seen,
                port = COALESCE(excluded.port, devices.port)
            """,
            (mac, seen_at, seen_at, port),
        )
        connection.commit()


def update_device_from_inventory(inventory):
    """Actualise l'identité technique d'une carte à partir d'un inventaire."""

    identification = inventory.get("identification", {})
    mac = identification.get("mac")

    if not mac:
        return None

    mac = mac.lower()
    timestamp = inventory.get("timestamp") or _now()
    port = inventory.get("port")

    kept = {
        field: identification[field]
        for field in IDENTIFICATION_FIELDS
        if field in identification
    }

    with connect() as connection:
        connection.execute(
            """
            INSERT INTO devices (mac, first_seen, last_seen, port, identification)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(mac) DO UPDATE SET
                last_seen = excluded.last_seen,
                port = excluded.port,
                identification = excluded.identification
            """,
            (mac, timestamp, timestamp, port, json.dumps(kept, ensure_ascii=False)),
        )
        connection.commit()

    return get_device(mac)


# --- Lectures (readings) --------------------------------------------------

def save_reading(mac, section, payload, port=None, recorded_at=None):
    """Enregistre une lecture (section quelconque) pour une carte."""

    if not mac:
        return None

    mac = mac.lower()
    recorded_at = recorded_at or _now()

    ensure_device(mac, port=port, seen_at=recorded_at)

    with connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO readings (mac, section, recorded_at, port, payload)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                mac, section, recorded_at, port,
                json.dumps(payload, ensure_ascii=False),
            ),
        )
        connection.commit()
        return cursor.lastrowid


def get_readings(mac, section=None):
    """Retourne les lectures d'une carte (optionnellement filtrées)."""

    query = "SELECT * FROM readings WHERE mac = ?"
    params = [mac.lower()]

    if section:
        query += " AND section = ?"
        params.append(section)

    query += " ORDER BY recorded_at DESC, id DESC"

    with connect() as connection:
        rows = connection.execute(query, params).fetchall()

    return [_row_to_reading(row) for row in rows]


def get_latest_reading(mac, section):
    """Retourne la lecture la plus récente d'une section, ou None."""

    with connect() as connection:
        row = connection.execute(
            """
            SELECT * FROM readings
            WHERE mac = ? AND section = ?
            ORDER BY recorded_at DESC, id DESC LIMIT 1
            """,
            (mac.lower(), section),
        ).fetchone()

    return _row_to_reading(row) if row else None


def _row_to_reading(row):
    try:
        payload = json.loads(row["payload"])
    except (TypeError, json.JSONDecodeError):
        payload = None

    return {
        "id": row["id"],
        "mac": row["mac"],
        "section": row["section"],
        "recorded_at": row["recorded_at"],
        "port": row["port"],
        "payload": payload,
    }


def get_inventory_history():
    """Historique compatible : liste de {recorded_at, inventory}."""

    with connect() as connection:
        rows = connection.execute(
            """
            SELECT recorded_at, payload FROM readings
            WHERE section = 'inventory'
            ORDER BY recorded_at ASC, id ASC
            """
        ).fetchall()

    history = []
    for row in rows:
        try:
            inventory = json.loads(row["payload"])
        except (TypeError, json.JSONDecodeError):
            continue
        history.append({
            "recorded_at": row["recorded_at"],
            "inventory": inventory,
        })
    return history


def get_last_inventory():
    """Dernier inventaire enregistré (payload), ou None."""

    with connect() as connection:
        row = connection.execute(
            """
            SELECT payload FROM readings
            WHERE section = 'inventory'
            ORDER BY recorded_at DESC, id DESC LIMIT 1
            """
        ).fetchone()

    if not row:
        return None

    try:
        return json.loads(row["payload"])
    except (TypeError, json.JSONDecodeError):
        return None


def get_device_dossier(mac):
    """
    Retourne le dossier complet d'une carte : fiche + dernière lecture de
    chaque section + dates de capture.
    """

    device = get_device(mac)
    if not device:
        return None

    sections = {}
    captured = {}
    for section in SECTIONS:
        latest = get_latest_reading(mac, section)
        if latest:
            sections[section] = latest["payload"]
            captured[section] = latest["recorded_at"]

    counts = {
        section: len(get_readings(mac, section)) for section in SECTIONS
    }

    return {
        "device": device,
        "sections": sections,
        "captured": captured,
        "counts": counts,
    }


# --- Migration ------------------------------------------------------------

def migrate_from_json():
    """Importe les anciens fichiers JSON dans la base (une seule fois)."""

    registry_file = DATA_DIR / "device_registry.json"
    history_file = DATA_DIR / "inventory_history.json"

    if registry_file.exists():
        try:
            registry = json.loads(registry_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            registry = {}

        for mac, entry in registry.items():
            mac = mac.lower()
            identification = {
                field: entry[field]
                for field in IDENTIFICATION_FIELDS
                if field in entry
            }
            with connect() as connection:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO devices
                        (mac, name, location, note, last_seen, identification)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        mac,
                        entry.get("name", ""),
                        entry.get("location", ""),
                        entry.get("note", ""),
                        entry.get("last_seen"),
                        json.dumps(identification, ensure_ascii=False),
                    ),
                )
                connection.commit()

    if history_file.exists():
        try:
            history = json.loads(history_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            history = []

        for entry in history:
            inventory = entry.get("inventory", {})
            identification = inventory.get("identification", {})
            mac = (identification.get("mac") or "").lower()
            if not mac:
                continue
            save_reading(
                mac,
                "inventory",
                inventory,
                port=inventory.get("port"),
                recorded_at=entry.get("recorded_at"),
            )
