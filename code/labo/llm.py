"""Acces a l'IA locale (Ollama). Si elle n'est pas installee, available() renvoie
False et les missions continuent sans descriptions ni propositions."""
import base64
import json
import fcntl
import time
from pathlib import Path

import requests

from .config import OLLAMA_MODEL, OLLAMA_URL, DATA


def available(model=None):
    try:
        tags = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5).json()
    except (requests.RequestException, ValueError):
        return False
    return any(m.get("name", "") == (model or OLLAMA_MODEL) for m in tags.get("models", []))


class Busy(requests.RequestException):
    """L'autre mission utilise deja le modele local."""


def ask(prompt, image_path=None, schema=None, timeout=3600, wait=True,
        model=None, num_predict=768, num_ctx=4096, progress=None, thinking=False):
    """Pose une question au modele. Avec un schema JSON, renvoie un dict.
    Delai large : l'IA passe apres les missions pour le processeur, une reponse peut prendre longtemps."""
    payload = {
        "model": model or OLLAMA_MODEL,
        "prompt": prompt,
        "stream": bool(progress),
        "options": {"temperature": 0.4, "num_ctx": num_ctx, "num_predict": num_predict,
                    "num_thread": 2, "num_batch": 128},
        "keep_alive": 0,  # libere aussi le cache de prompts, qui finissait par depasser 7 Gio
    }
    if payload['model'].startswith('qwen3:'):
        payload['think'] = bool(thinking)
    if image_path:
        payload["images"] = [base64.b64encode(Path(image_path).read_bytes()).decode()]
    if schema:
        payload["format"] = schema
    with (DATA / '.ollama-request.lock').open('a') as lock:
        if progress: progress('waiting', 0)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | (0 if wait else fcntl.LOCK_NB))
        except BlockingIOError as exc:
            raise Busy("IA locale occupee par l'autre mission") from exc
        if progress: progress('generating', 0)
        r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=timeout, stream=bool(progress))
        r.raise_for_status()
        if progress:
            pieces, result = [], {}
            started = last = time.monotonic()
            length = 0
            try:
                for line in r.iter_lines():
                    if not line: continue
                    event = json.loads(line)
                    if event.get('error'): raise ValueError(event['error'])
                    piece = event.get('response', '')
                    pieces.append(piece)
                    length += len(piece)
                    now = time.monotonic()
                    if now - started > timeout: raise requests.Timeout('Delai total de generation depasse')
                    if now - last > 2:
                        progress('reasoning' if event.get('thinking') and not length else 'generating', length)
                        last = now
                    if event.get('done'):
                        result = event
                        break
                if not result.get('done'): raise ValueError('Flux IA interrompu avant la fin')
                result['response'] = ''.join(pieces)
                progress('complete', length)
            finally:
                r.close()
        else:
            result = r.json()
        if result.get('done_reason') == 'length':
            raise ValueError('Reponse IA tronquee : limite de generation atteinte')
        text = result["response"]
    return json.loads(text) if schema else text.strip()
