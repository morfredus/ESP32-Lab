"""
Gestion de l'historique des inventaires ESP32.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
HISTORY_FILE = PROJECT_ROOT / "data" / "inventory_history.json"


def load_history():
    """Charge l'historique existant."""

    if not HISTORY_FILE.exists():
        return []

    with HISTORY_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_history(inventory):
    """Ajoute un inventaire à l'historique."""

    history = load_history()

    entry = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "inventory": inventory,
    }

    history.append(entry)

    HISTORY_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with HISTORY_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            history,
            file,
            indent=4,
            ensure_ascii=False,
        )

    return HISTORY_FILE


def get_history():
    """Retourne l'historique des inventaires."""

    return load_history()


if __name__ == "__main__":
    print(json.dumps(
        get_history(),
        indent=4,
        ensure_ascii=False,
    ))
