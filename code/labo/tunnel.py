"""Acces au tableau de bord depuis Internet (par exemple le telephone), par un tunnel Cloudflare.

cloudflared ouvre une adresse https://....trycloudflare.com qui mene au tableau de bord : gratuit,
sans compte et sans ouvrir de port sur la box. L'adresse change a chaque redemarrage du tunnel : elle
est notee dans data/lien.json, affichee sur le tableau de bord et envoyee en notification. Depuis
Internet, la page exige en plus une cle secrete, comprise dans le lien (voir labo.web).
"""
import json
import logging
import re
import secrets
import subprocess
import sys
import time

from .config import ACCESS_SETTINGS, LOG_FORMAT, TUNNEL_STATUS

log = logging.getLogger("tunnel")
URL = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def access_key():
    """Cle secrete demandee aux visiteurs venus d'Internet ; tiree au hasard la premiere fois."""
    if ACCESS_SETTINGS.exists():
        return json.loads(ACCESS_SETTINGS.read_text())["cle"]
    key = secrets.token_urlsafe(18)
    ACCESS_SETTINGS.write_text(json.dumps({"cle": key}) + "\n")
    ACCESS_SETTINGS.chmod(0o600)
    return key


def link():
    """Lien complet du moment (avec la cle), ou None si le tunnel n'est pas ouvert."""
    try:
        return json.loads(TUNNEL_STATUS.read_text())["lien"]
    except (OSError, ValueError, KeyError):
        return None


def main():
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    TUNNEL_STATUS.unlink(missing_ok=True)
    proc = subprocess.Popen(["cloudflared", "tunnel", "--no-autoupdate", "--url", "http://127.0.0.1:8080"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    for line in proc.stderr:
        m = URL.search(line)
        if m and not TUNNEL_STATUS.exists():
            full = f"{m[0]}/?cle={access_key()}"
            TUNNEL_STATUS.write_text(json.dumps({"lien": full, "t": time.time()}) + "\n")
            TUNNEL_STATUS.chmod(0o600)
            log.info("tunnel ouvert : %s", m[0])
            from .veille import notify
            notify("Labo IA : lien du tableau de bord",
                   "Nouveau lien pour voir le labo depuis ton téléphone (garde-le pour toi) :\n" + full, 3, click=full)
        elif " ERR " in line:
            log.warning("cloudflared : %s", line.strip()[:300])
    TUNNEL_STATUS.unlink(missing_ok=True)
    sys.exit(proc.wait() or 1)  # systemd relance le tunnel


if __name__ == "__main__":
    main()
