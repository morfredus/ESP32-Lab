"""
Base de references Espressif locale (offline-first).

Les caracteristiques GPIO d'une famille ESP32 ne sont pas publiees par Espressif
sous forme de jeu de donnees exploitable : elles vivent dans les datasheets
(sections Boot Configurations) et la reference GPIO d'ESP-IDF. ESP32-Lab embarque
donc un jeu cure (verifie sur ces sources) dans ``reference/espressif/``, livre
avec l'application et donc disponible des le premier lancement, hors ligne.

Au premier usage, ce jeu est copie dans un cache inscriptible ``data/espressif/``.
Une mise a jour manuelle (bouton dans l'interface) peut telecharger une version
plus recente du jeu cure depuis le canal projet (raw GitHub), avec :

- controle du schema (``schema_version``) ;
- controle d'integrite (sha256 par fichier, valide contre le metadata telecharge) ;
- sauvegarde de la version precedente avant tout remplacement ;
- conservation de la base locale intacte en cas d'echec.
"""

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen


SUPPORTED_SCHEMA = 1

_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_DIR = _ROOT / "reference" / "espressif"
CACHE_DIR = _ROOT / "data" / "espressif"
BACKUP_DIR = CACHE_DIR / ".backup"

CHANNEL_BASE = (
    "https://raw.githubusercontent.com/morfredus/ESP32-Lab/main/"
    "reference/espressif/"
)

# Fichiers du jeu de donnees (hors metadata).
DATASET_FILES = ("esp32.json", "esp32-s3.json", "esp32-c3.json")
METADATA_FILE = "metadata.json"

# Correspondance famille (valeur chip_family) -> nom de fichier (sans extension).
_FAMILY_FILES = {
    "esp32": "esp32",
    "esp32s3": "esp32-s3",
    "esp32c3": "esp32-c3",
}


def normalize_family(chip):
    """Normalise un libelle de famille (``ESP32-S3`` -> ``esp32s3``)."""

    if not chip:
        return None

    return str(chip).strip().lower().replace("-", "")


def _sha256(data):
    """Empreinte sha256 d'un contenu binaire."""

    return hashlib.sha256(data).hexdigest()


def ensure_local_dataset():
    """
    Copie le jeu cure livre vers le cache inscriptible si celui-ci est absent.
    N'ecrase jamais un cache existant. Aucun acces reseau.
    """

    marker = CACHE_DIR / METADATA_FILE

    if marker.exists():
        return

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    for name in (METADATA_FILE, *DATASET_FILES):
        source = REFERENCE_DIR / name
        if source.exists():
            shutil.copy2(source, CACHE_DIR / name)


def _read_json(path):
    """Lit un fichier JSON (retourne ``None`` si absent ou illisible)."""

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def metadata():
    """Metadonnees du cache local (dict) ou ``None``."""

    ensure_local_dataset()
    return _read_json(CACHE_DIR / METADATA_FILE)


def load_family(chip):
    """
    Charge les donnees d'une famille depuis le cache local.

    Retourne le dict de la famille, ou ``None`` si la famille n'est pas couverte
    ou si le schema du fichier est incompatible (rejet honnete plutot qu'une
    interpretation hasardeuse).
    """

    ensure_local_dataset()

    stem = _FAMILY_FILES.get(normalize_family(chip))
    if stem is None:
        return None

    data = _read_json(CACHE_DIR / f"{stem}.json")
    if not isinstance(data, dict):
        return None

    if data.get("schema_version") != SUPPORTED_SCHEMA:
        return None

    return data


def dataset_status():
    """
    Etat de la base locale : version, source, date de synchronisation,
    disponibilite hors ligne et integrite (sha256).
    """

    ensure_local_dataset()

    meta = _read_json(CACHE_DIR / METADATA_FILE) or {}
    declared = meta.get("files", {})

    integrity_ok = True
    offline_available = True
    families = []

    for name in DATASET_FILES:
        stem = name[:-5]
        path = CACHE_DIR / name

        if not path.exists():
            offline_available = False
            integrity_ok = False
            continue

        family = _read_json(path) or {}
        if family.get("label"):
            families.append({
                "family": family.get("family"),
                "label": family.get("label"),
            })

        expected = (declared.get(stem) or {}).get("sha256")
        if expected is not None:
            actual = _sha256(path.read_bytes())
            if actual != expected:
                integrity_ok = False

    return {
        "status": "ok",
        "schema_version": meta.get("schema_version"),
        "dataset_version": meta.get("dataset_version"),
        "source": meta.get("source"),
        "source_urls": meta.get("source_urls", []),
        "channel": meta.get("channel"),
        "synced_at": meta.get("synced_at"),
        "offline_available": offline_available,
        "integrity_ok": integrity_ok,
        "families": families,
    }


def _download(url, timeout=15):
    """Telecharge une URL et renvoie son contenu binaire (stdlib urllib)."""

    with urlopen(url, timeout=timeout) as response:  # noqa: S310 (URL fixe, canal projet)
        return response.read()


def refresh_from_channel(force=False, downloader=None):
    """
    Met a jour la base locale depuis le canal projet.

    Etapes robustes : telecharge le metadata + les fichiers de familles, valide
    le schema et le sha256 de chaque fichier contre le metadata telecharge, puis
    seulement en cas de succes complet sauvegarde l'ancienne base et remplace le
    cache. Toute erreur (reseau, integrite, schema) laisse la base locale intacte.

    ``downloader`` est injectable (tests) : callable ``url -> bytes``.
    """

    ensure_local_dataset()
    fetch = downloader or _download

    # 1. Telechargement (aucune ecriture dans le cache a ce stade).
    try:
        raw_meta = fetch(CHANNEL_BASE + METADATA_FILE)
        new_meta = json.loads(raw_meta.decode("utf-8"))
    except HTTPError as error:
        if error.code == 404:
            return {
                "status": "error",
                "message": (
                    "Aucune base publiee sur le canal de mise a jour (404). Le "
                    "jeu de references n'y est pas encore disponible. La base "
                    "locale livree reste utilisable hors ligne."
                ),
            }
        return {
            "status": "error",
            "message": f"Telechargement du metadata impossible : {error}",
        }
    except Exception as error:
        return {
            "status": "error",
            "message": f"Telechargement du metadata impossible : {error}",
        }

    if new_meta.get("schema_version") != SUPPORTED_SCHEMA:
        return {
            "status": "error",
            "message": (
                "Schema de donnees distant incompatible "
                f"({new_meta.get('schema_version')}). Base locale conservee."
            ),
        }

    declared = new_meta.get("files", {})
    downloaded = {METADATA_FILE: raw_meta}

    for name in DATASET_FILES:
        stem = name[:-5]
        try:
            raw = fetch(CHANNEL_BASE + name)
        except Exception as error:
            return {
                "status": "error",
                "message": (
                    f"Telechargement de {name} impossible : {error}. "
                    "Base locale conservee."
                ),
            }

        expected = (declared.get(stem) or {}).get("sha256")
        if expected is not None and _sha256(raw) != expected:
            return {
                "status": "error",
                "message": (
                    f"Integrite de {name} invalide (sha256). "
                    "Base locale conservee."
                ),
            }

        family = json.loads(raw.decode("utf-8"))
        if family.get("schema_version") != SUPPORTED_SCHEMA:
            return {
                "status": "error",
                "message": (
                    f"Schema de {name} incompatible. Base locale conservee."
                ),
            }

        downloaded[name] = raw

    # 2. Sauvegarde de la base actuelle avant tout remplacement.
    _backup_current_cache()

    # 3. Remplacement (horodate la synchronisation).
    new_meta["synced_at"] = datetime.now(timezone.utc).isoformat()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    for name, raw in downloaded.items():
        if name == METADATA_FILE:
            (CACHE_DIR / name).write_text(
                json.dumps(new_meta, indent=4, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        else:
            (CACHE_DIR / name).write_bytes(raw)

    return {
        "status": "ok",
        "message": "Base Espressif mise a jour.",
        "dataset_version": new_meta.get("dataset_version"),
        "synced_at": new_meta["synced_at"],
    }


def _backup_current_cache():
    """Copie la base locale actuelle dans ``.backup/`` (ecrase la precedente)."""

    if BACKUP_DIR.exists():
        shutil.rmtree(BACKUP_DIR, ignore_errors=True)

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    for name in (METADATA_FILE, *DATASET_FILES):
        source = CACHE_DIR / name
        if source.exists():
            shutil.copy2(source, BACKUP_DIR / name)
