"""Acces au tableau de bord depuis le telephone, par le VPN Tailscale (voir deploy/05_tailscale.sh).

Rien n'est expose sur Internet : seuls les appareils relies au meme compte Tailscale voient le labo.
"""
import json
import subprocess


def links():
    """Adresses du tableau de bord par le VPN, ou None si le labo n'y est pas (encore) relie."""
    try:
        out = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, timeout=5)
        status = json.loads(out.stdout)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    me = status.get("Self") or {}
    if status.get("BackendState") != "Running" or not me.get("TailscaleIPs"):
        return None
    name = me.get("DNSName", "").split(".")[0]
    return {"nom": f"http://{name}:8080" if name else None, "ip": f"http://{me['TailscaleIPs'][0]}:8080"}
