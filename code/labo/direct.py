"""Etat en direct des missions, lu par la page « En direct » du tableau de bord."""
import json
import os
import time

from .config import LIVE_DIR


def write(name, data):
    """Remplace l'etat d'une mission d'un seul coup : la page ne lit jamais un fichier a moitie ecrit."""
    try:
        LIVE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = LIVE_DIR / f".{name}.tmp"
        tmp.write_text(json.dumps({**data, "t": time.time()}, ensure_ascii=False))
        os.replace(tmp, LIVE_DIR / f"{name}.json")
    except OSError:
        pass  # l'affichage en direct ne doit jamais arreter une mission


def read(name):
    try:
        return json.loads((LIVE_DIR / f"{name}.json").read_text())
    except (OSError, ValueError):
        return None
