"""
Invocation portable d'esptool.

L'ancienne version appelait ``.venv/bin/python`` en dur, ce qui liait le
projet à un environnement virtuel Linux précis. On résout désormais esptool
automatiquement, dans cet ordre :

1. l'interpréteur Python courant, s'il dispose du module ``esptool`` ;
2. le ``.venv`` du projet (``.venv/bin/python`` ou ``.venv/Scripts/python.exe``),
   s'il dispose du module ``esptool`` ;
3. la commande ``esptool`` présente dans le PATH.

Ainsi le serveur fonctionne dans ou hors d'un ``.venv``, sous Linux comme sous
Windows, y compris s'il est lancé avec un interpréteur système dépourvu
d'esptool tant qu'un ``.venv`` du projet en dispose.
"""

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Cache de la commande de base résolue (évite de refaire la détection).
_cached_base_command = None


def _interpreter_has_esptool(python_path):
    """Indique si l'interpréteur donné dispose du module esptool."""

    try:
        result = subprocess.run(
            [str(python_path), "-c", "import esptool"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return False

    return result.returncode == 0


def _venv_python_candidates():
    """Chemins possibles de l'interpréteur du ``.venv`` du projet."""

    return [
        PROJECT_ROOT / ".venv" / "bin" / "python",
        PROJECT_ROOT / ".venv" / "bin" / "python3",
        PROJECT_ROOT / ".venv" / "Scripts" / "python.exe",
    ]


def _resolve_base_command():
    """Détermine la meilleure commande de base pour lancer esptool."""

    # 1. Interpréteur courant.
    if importlib.util.find_spec("esptool") is not None:
        return [sys.executable, "-m", "esptool"]

    # 2. Interpréteur du .venv du projet.
    for candidate in _venv_python_candidates():
        if candidate.exists() and _interpreter_has_esptool(candidate):
            return [str(candidate), "-m", "esptool"]

    # 3. Commande esptool du PATH.
    esptool_executable = shutil.which("esptool")
    if esptool_executable:
        return [esptool_executable]

    # 4. Repli : interpréteur courant (produira une erreur explicite).
    return [sys.executable or "python", "-m", "esptool"]


def esptool_base_command():
    """Retourne (et met en cache) la commande de base pour lancer esptool."""

    global _cached_base_command

    if _cached_base_command is None:
        _cached_base_command = _resolve_base_command()

    return list(_cached_base_command)


def espefuse_base_command():
    """
    Retourne la commande de base pour lancer espefuse.

    espefuse est fourni par le même paquet qu'esptool : on réutilise donc
    le même interpréteur, en remplaçant simplement le module. Si esptool a
    été résolu via une commande console (``esptool`` du PATH), on tente
    ``espefuse``.
    """

    base = esptool_base_command()

    if len(base) >= 2 and base[1] == "-m":
        # [python, "-m", "esptool", ...] -> [python, "-m", "espefuse"]
        return [base[0], "-m", "espefuse"]

    # Commande console : esptool -> espefuse (même dossier).
    console = shutil.which("espefuse")
    if console:
        return [console]

    return [sys.executable or "python", "-m", "espefuse"]


def run_esptool(arguments, timeout=60):
    """Exécute esptool avec les arguments fournis (après ``-m esptool``)."""

    command = esptool_base_command() + list(arguments)

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def run_espefuse(arguments, timeout=90):
    """Exécute espefuse avec les arguments fournis (lecture seule attendue)."""

    command = espefuse_base_command() + list(arguments)

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def resolved_python():
    """
    Retourne l'interpréteur Python disposant d'esptool, pour exécuter des
    scripts utilisant directement l'API Python d'esptool. Retourne ``None``
    si esptool n'est accessible que via une commande console.
    """

    base = esptool_base_command()

    if len(base) >= 2 and base[1] == "-m":
        return base[0]

    return None
