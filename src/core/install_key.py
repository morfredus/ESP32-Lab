"""
Clé d'installation et empreintes HMAC.

Pour ne jamais stocker de secret (mot de passe Wi-Fi, token, clé) en base tout
en pouvant détecter un changement d'un scan à l'autre, on remplace la valeur
sensible par une **empreinte HMAC-SHA-256** calculée avec une clé propre à
l'installation.

- La clé vit dans la **config du service**, jamais en base ni versionnée.
- Emplacement (convention morfSystem), avec repli utilisateur si le dossier
  système n'est pas inscriptible (cas normal : service lancé sans droits root) :
    - Linux   : /etc/morfsystem/esp32-lab/         puis ~/.config/morfsystem/esp32-lab/
    - Windows : %ProgramData%\\morfsystem\\esp32-lab\\  puis %APPDATA%\\morfsystem\\esp32-lab\\
- L'empreinte est **stable pour une même installation** : indispensable pour
  comparer un scan au précédent. Elle n'est PAS comparable entre installations
  (clés différentes) — c'est voulu, la clé ne quitte jamais la machine.
"""

import hashlib
import hmac
import os
from pathlib import Path


KEY_FILENAME = "install.key"
KEY_SIZE_BYTES = 32

_cached_key = None


def _candidate_config_dirs():
    """Dossiers de config candidats, du plus « intégré » au repli utilisateur."""

    dirs = []

    if os.name == "nt":
        program_data = os.environ.get("ProgramData", r"C:\ProgramData")
        dirs.append(Path(program_data) / "morfsystem" / "esp32-lab")
        appdata = os.environ.get("APPDATA")
        if appdata:
            dirs.append(Path(appdata) / "morfsystem" / "esp32-lab")
    else:
        dirs.append(Path("/etc/morfsystem/esp32-lab"))
        xdg = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
        dirs.append(Path(xdg) / "morfsystem" / "esp32-lab")

    return dirs


def _resolve_key_path():
    """Chemin du fichier clé : une clé existante prime, sinon 1er dossier inscriptible."""

    candidates = _candidate_config_dirs()

    # 1. Une clé déjà présente l'emporte (peu importe le dossier).
    for directory in candidates:
        path = directory / KEY_FILENAME
        if path.exists():
            return path

    # 2. Premier dossier que l'on peut créer.
    for directory in candidates:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            return directory / KEY_FILENAME
        except OSError:
            continue

    # 3. Dernier recours : dossier data du projet.
    fallback = Path(__file__).resolve().parents[2] / "data"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback / KEY_FILENAME


def _load_or_create_key():
    """Lit la clé d'installation, ou la génère (une fois) si absente."""

    path = _resolve_key_path()

    if path.exists():
        return path.read_bytes()

    key = os.urandom(KEY_SIZE_BYTES)
    path.write_bytes(key)

    # Droits restreints côté POSIX (best effort ; ACL par défaut côté Windows).
    if os.name != "nt":
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass

    return key


def install_key():
    """Retourne (et met en cache) la clé d'installation."""

    global _cached_key
    if _cached_key is None:
        _cached_key = _load_or_create_key()
    return _cached_key


def fingerprint(data):
    """Empreinte HMAC-SHA-256 (hex) d'une donnée, avec la clé d'installation."""

    if isinstance(data, str):
        data = data.encode("utf-8")
    return hmac.new(install_key(), data, hashlib.sha256).hexdigest()


def key_id():
    """
    Identifiant public de la clé d'installation (ne révèle rien de la clé).
    Permet de savoir si deux empreintes proviennent de la même installation.
    """

    return hashlib.sha256(install_key()).hexdigest()[:16]
