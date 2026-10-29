"""Acces a l'IA locale (Ollama). Si elle n'est pas installee, available() renvoie
False et les missions continuent sans descriptions ni propositions."""
import base64
import json
from pathlib import Path

import requests

from .config import OLLAMA_MODEL, OLLAMA_URL


def available():
    try:
        tags = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5).json()
    except (requests.RequestException, ValueError):
        return False
    return any(m.get("name", "").startswith(OLLAMA_MODEL) for m in tags.get("models", []))


def ask(prompt, image_path=None, schema=None, timeout=1200):
    """Pose une question au modele. Avec un schema JSON, renvoie un dict."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.4},
    }
    if image_path:
        payload["images"] = [base64.b64encode(Path(image_path).read_bytes()).decode()]
    if schema:
        payload["format"] = schema
    r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=timeout)
    r.raise_for_status()
    text = r.json()["response"]
    return json.loads(text) if schema else text.strip()
