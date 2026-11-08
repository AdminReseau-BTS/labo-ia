"""Acces a l'IA locale (Ollama). Si elle n'est pas installee, available() renvoie
False et les missions continuent sans descriptions ni propositions."""
import base64
import json
import fcntl
from pathlib import Path

import requests

from .config import OLLAMA_MODEL, OLLAMA_URL, DATA


def available():
    try:
        tags = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5).json()
    except (requests.RequestException, ValueError):
        return False
    return any(m.get("name", "").startswith(OLLAMA_MODEL) for m in tags.get("models", []))


class Busy(requests.RequestException):
    """L'autre mission utilise deja le modele local."""


def ask(prompt, image_path=None, schema=None, timeout=3600, wait=True):
    """Pose une question au modele. Avec un schema JSON, renvoie un dict.
    Delai large : l'IA passe apres les missions pour le processeur, une reponse peut prendre longtemps."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.4, "num_ctx": 4096, "num_predict": 768,
                    "num_thread": 2, "num_batch": 128},
        "keep_alive": 0,  # libere aussi le cache de prompts, qui finissait par depasser 7 Gio
    }
    if image_path:
        payload["images"] = [base64.b64encode(Path(image_path).read_bytes()).decode()]
    if schema:
        payload["format"] = schema
    with (DATA / '.ollama-request.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | (0 if wait else fcntl.LOCK_NB))
        except BlockingIOError as exc:
            raise Busy("IA locale occupee par l'autre mission") from exc
        r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=timeout)
        r.raise_for_status()
        result = r.json()
        if result.get('done_reason') == 'length':
            raise ValueError('Reponse IA tronquee : limite de generation atteinte')
        text = result["response"]
    return json.loads(text) if schema else text.strip()
