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

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def _now():
    return datetime.now(timezone.utc).isoformat()


# Le schéma n'est créé qu'une fois par processus (idempotent et peu coûteux).
_schema_ready = False


def connect():
    """
    Ouvre une connexion SQLite. Crée le dossier ``data/`` et le schéma au
    besoin : la base se crée donc proprement dès la première utilisation,
    y compris après une installation neuve (aucun fichier au départ).
    """

    global _schema_ready

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    if not _schema_ready:
        connection.executescript(SCHEMA)
        connection.commit()
        _schema_ready = True

    return connection


def get_meta(key):
    """Retourne une valeur méta, ou None."""

    with connect() as connection:
        row = connection.execute(
            "SELECT value FROM meta WHERE key = ?", (key,)
        ).fetchone()
    return row["value"] if row else None


def set_meta(key, value):
    """Enregistre une valeur méta."""

    with connect() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            (key, value),
        )
        connection.commit()


def init_db():
    """
    Initialise la base : garantit le schéma (créé à la première connexion)
    et migre les anciens fichiers JSON **une seule fois** (marqueur ``meta``).

    La migration est idempotente et additive : elle n'ajoute que ce qui
    manque (déduplication par MAC et par date), sans écraser les métadonnées
    déjà présentes. Le marqueur évite qu'une remise à zéro ne réimporte les
    anciens JSON.
    """

    # La connexion crée le schéma.
    with connect():
        pass

    if get_meta("json_migrated") != "1":
        migrate_from_json()
        set_meta("json_migrated", "1")

    # Purge unique des secrets dans les lectures enregistrées avant la
    # rédaction (versions < 0.5.0).
    if get_meta("readings_redacted") != "1":
        redact_existing_readings()
        set_meta("readings_redacted", "1")

    # Purge unique renforcée (0.6.5) : suppression de TOUT dump hexadécimal NVS,
    # pour éliminer les copies résiduelles de secrets (mot de passe, SSID) que
    # la rédaction par clé laissait dans les slots effacés/orphelins.
    if get_meta("nvs_hex_purged") != "1":
        redact_existing_readings()
        set_meta("nvs_hex_purged", "1")


def redact_existing_readings():
    """Caviarde les secrets des lectures NVS/eFuse déjà en base (rétroactif)."""

    from core.secret_redaction import (
        sanitize_efuse_for_storage,
        sanitize_nvs_for_storage,
    )

    sanitizers = {
        "nvs": sanitize_nvs_for_storage,
        "efuse": sanitize_efuse_for_storage,
    }

    with connect() as connection:
        rows = connection.execute(
            "SELECT id, section, payload FROM readings "
            "WHERE section IN ('nvs', 'efuse')"
        ).fetchall()

        for row in rows:
            sanitize = sanitizers.get(row["section"])
            if not sanitize:
                continue
            try:
                payload = json.loads(row["payload"])
            except (TypeError, json.JSONDecodeError):
                continue

            cleaned = sanitize(payload)
            connection.execute(
                "UPDATE readings SET payload = ? WHERE id = ?",
                (json.dumps(cleaned, ensure_ascii=False), row["id"]),
            )

        connection.commit()


def delete_device(mac):
    """
    Supprime une carte et toutes ses lectures. Opération irréversible.
    Retourne le nombre de lectures supprimées, ou None si la carte est absente.
    """

    if not mac:
        return None

    mac = mac.lower()
    with connect() as connection:
        exists = connection.execute(
            "SELECT 1 FROM devices WHERE mac = ?", (mac,)
        ).fetchone()
        if not exists:
            return None

        readings = connection.execute(
            "DELETE FROM readings WHERE mac = ?", (mac,)
        ).rowcount
        connection.execute("DELETE FROM devices WHERE mac = ?", (mac,))
        connection.commit()

    return {"status": "ok", "mac": mac, "readings_deleted": readings}


def reset_database():
    """
    Vide entièrement la base (cartes + lectures), sans réimporter les anciens
    JSON. Le schéma et le marqueur de migration sont conservés.
    """

    with connect() as connection:
        connection.execute("DELETE FROM readings")
        connection.execute("DELETE FROM devices")
        connection.commit()

    return {"status": "ok", "message": "Base remise à zéro."}


def counts():
    """Compteurs légers (cartes, lectures) pour les métriques de supervision."""

    with connect() as connection:
        devices = connection.execute(
            "SELECT COUNT(*) FROM devices"
        ).fetchone()[0]
        readings = connection.execute(
            "SELECT COUNT(*) FROM readings"
        ).fetchone()[0]

    return {"devices": devices, "readings": readings}


def verify_database():
    """Vérifie l'intégrité de la base et retourne des statistiques."""

    with connect() as connection:
        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]
        devices = connection.execute(
            "SELECT COUNT(*) FROM devices"
        ).fetchone()[0]
        rows = connection.execute(
            "SELECT section, COUNT(*) AS n FROM readings GROUP BY section"
        ).fetchall()

    by_section = {row["section"]: row["n"] for row in rows}
    size = DB_PATH.stat().st_size if DB_PATH.exists() else 0

    return {
        "status": "ok",
        "integrity": integrity,
        "healthy": integrity == "ok",
        "devices": devices,
        "readings_by_section": by_section,
        "readings_total": sum(by_section.values()),
        "db_path": str(DB_PATH),
        "db_size_bytes": size,
    }


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

def export_all():
    """
    Exporte l'intégralité de la base (cartes + lectures) en dictionnaire
    JSON lisible et portable, pour changer de poste ou sauvegarder.
    """

    with connect() as connection:
        device_rows = connection.execute("SELECT * FROM devices").fetchall()
        reading_rows = connection.execute(
            "SELECT mac, section, recorded_at, port, payload FROM readings"
        ).fetchall()

    def _parse(text):
        try:
            return json.loads(text) if text else None
        except (TypeError, json.JSONDecodeError):
            return None

    devices = []
    for row in device_rows:
        devices.append({
            "mac": row["mac"],
            "name": row["name"],
            "location": row["location"],
            "note": row["note"],
            "first_seen": row["first_seen"],
            "last_seen": row["last_seen"],
            "port": row["port"],
            "identification": _parse(row["identification"]),
        })

    readings = []
    for row in reading_rows:
        readings.append({
            "mac": row["mac"],
            "section": row["section"],
            "recorded_at": row["recorded_at"],
            "port": row["port"],
            "payload": _parse(row["payload"]),
        })

    return {
        "format": "esp32lab-export",
        "version": 1,
        "exported_at": _now(),
        "devices": devices,
        "readings": readings,
    }


def import_data(payload):
    """
    Importe un export (fusion additive, sans écraser les métadonnées ni
    dupliquer les lectures). Retourne le nombre d'éléments ajoutés.
    """

    if not isinstance(payload, dict) or payload.get("format") != "esp32lab-export":
        raise ValueError("Fichier d'import invalide (format inattendu).")

    devices_added = 0
    devices_updated = 0
    with connect() as connection:
        for device in payload.get("devices", []):
            mac = (device.get("mac") or "").lower()
            if not mac:
                continue

            identification = device.get("identification")
            identification_json = (
                json.dumps(identification, ensure_ascii=False)
                if identification is not None else None
            )

            existing = connection.execute(
                "SELECT name, location, note, identification "
                "FROM devices WHERE mac = ?",
                (mac,),
            ).fetchone()

            if existing is None:
                connection.execute(
                    """
                    INSERT INTO devices
                        (mac, name, location, note, first_seen, last_seen, port,
                         identification)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        mac,
                        device.get("name", ""),
                        device.get("location", ""),
                        device.get("note", ""),
                        device.get("first_seen"),
                        device.get("last_seen"),
                        device.get("port"),
                        identification_json,
                    ),
                )
                devices_added += 1
                continue

            # Carte déjà connue : on complète seulement les champs vides
            # (un nom édité localement n'est jamais écrasé), et on renseigne
            # l'identification si elle manque. C'est ce qui permet à une carte
            # créée vide par un scan de récupérer son nom lors de l'import.
            updates = {}
            for field in ("name", "location", "note"):
                incoming = (device.get(field) or "").strip()
                if incoming and not (existing[field] or "").strip():
                    updates[field] = incoming
            if identification_json and existing["identification"] is None:
                updates["identification"] = identification_json

            if updates:
                assignments = ", ".join(f"{field} = ?" for field in updates)
                connection.execute(
                    f"UPDATE devices SET {assignments} WHERE mac = ?",
                    (*updates.values(), mac),
                )
                devices_updated += 1
        connection.commit()

    readings_added = 0
    for reading in payload.get("readings", []):
        mac = (reading.get("mac") or "").lower()
        section = reading.get("section")
        recorded_at = reading.get("recorded_at")
        if not mac or not section or not recorded_at:
            continue
        if _reading_exists(mac, section, recorded_at):
            continue
        save_reading(
            mac, section, reading.get("payload"),
            port=reading.get("port"), recorded_at=recorded_at,
        )
        readings_added += 1

    return {
        "devices_added": devices_added,
        "devices_updated": devices_updated,
        "readings_added": readings_added,
    }


def _reading_exists(mac, section, recorded_at):
    """Indique si une lecture identique existe déjà (déduplication)."""

    with connect() as connection:
        row = connection.execute(
            """
            SELECT 1 FROM readings
            WHERE mac = ? AND section = ? AND recorded_at = ? LIMIT 1
            """,
            (mac.lower(), section, recorded_at),
        ).fetchone()
    return row is not None


def migrate_from_json():
    """
    Importe les anciens fichiers JSON dans la base, de façon idempotente :
    on n'ajoute que ce qui manque, sans écraser les métadonnées existantes.
    """

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
                # INSERT OR IGNORE : ne pas écraser un nom/une note déjà édités.
                connection.execute(
                    """
                    INSERT OR IGNORE INTO devices
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
            recorded_at = entry.get("recorded_at")
            if not mac or not recorded_at:
                continue
            if _reading_exists(mac, "inventory", recorded_at):
                continue
            save_reading(
                mac,
                "inventory",
                inventory,
                port=inventory.get("port"),
                recorded_at=recorded_at,
            )
