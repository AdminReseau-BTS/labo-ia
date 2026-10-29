"""Surveillance du labo, lancee toutes les 5 minutes par un timer systemd.

Elle releve les erreurs des missions dans leurs journaux, les services arretes ou
qui ont plante, une publication GitHub en echec, un disque presque plein et une
mission qui n'avance plus. Chaque probleme est garde dans data/veille.db (page
« Erreurs » du tableau de bord, avec le detail complet) et, s'il est nouveau,
envoye en notification sur le telephone par ntfy (gratuit, sans compte). Le sujet
ntfy est tire au hasard et reste dans data/notifications.json, jamais publie.
"""
import json
import logging
import re
import secrets
import shutil
import subprocess
import sys
import time
import traceback

import requests

from . import db
from .config import (DATA, LOG_FORMAT, NEURO_DB, NOTIFY_SETTINGS, NTFY_URL, PUBLICATION_STATUS, SERVICES,
                     SONDES_DB, VEILLE_DB)

log = logging.getLogger("veille")

SCHEMA = """
CREATE TABLE IF NOT EXISTS erreurs (
    id INTEGER PRIMARY KEY, cle TEXT, niveau TEXT, source TEXT, titre TEXT, detail TEXT,
    premiere REAL, derniere REAL, nombre INTEGER DEFAULT 1, vue INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS etat (k TEXT PRIMARY KEY, v TEXT);
"""
MAX_NOTIFS_PER_HOUR = 10
DISK_ALERT = 0.90
STALL_SONDES = 3 * 3600    # aucune nouvelle photo depuis 3 h
STALL_NEURONES = 2 * 3600  # aucune partie terminee depuis 2 h (une partie prend ~3 min)
STALL_PUBLICATION = 12 * 3600
# "2026-10-29 07:48:07,363 WARNING sondes message" (voir LOG_FORMAT)
LINE = re.compile(r"^\d{4}-\d\d-\d\d \S+ (DEBUG|INFO|WARNING|ERROR|CRITICAL) (\S+) (.*)$")


def get(con, k):
    row = con.execute("SELECT v FROM etat WHERE k=?", (k,)).fetchone()
    return row[0] if row else None


def put(con, k, v):
    con.execute("INSERT OR REPLACE INTO etat VALUES (?,?)", (k, str(v)))
    con.commit()


def settings():
    """Reglages des notifications ; le sujet ntfy est tire au hasard au premier lancement."""
    if NOTIFY_SETTINGS.exists():
        return json.loads(NOTIFY_SETTINGS.read_text())
    s = {"ntfy": f"labo-ia-{secrets.token_hex(8)}", "actif": True}
    NOTIFY_SETTINGS.write_text(json.dumps(s) + "\n")
    return s


def notify(title, message, priority=4, click=None):
    """Envoie une notification au telephone. Renvoie True si ntfy l'a acceptee."""
    s = settings()
    if not s.get("actif", True):
        return False
    msg = {"topic": s["ntfy"], "title": title, "message": message[:1500], "priority": priority,
           "tags": ["warning" if priority >= 4 else "link"]}
    if click:
        msg["click"] = click
    try:
        r = requests.post(NTFY_URL, json=msg, timeout=20)
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        log.warning("notification non envoyee : %s", e)
        return False


def may_notify(con):
    """Pas plus de 10 notifications par heure, meme si tout casse en meme temps."""
    now = time.time()
    sent = [t for t in json.loads(get(con, "notifs") or "[]") if now - t < 3600]
    if len(sent) >= MAX_NOTIFS_PER_HOUR:
        return False
    put(con, "notifs", json.dumps(sent + [now]))
    return True


def record(con, niveau, source, titre, detail="", resume=None):
    """Garde un probleme. Tant qu'il n'a pas ete vu, sa repetition ne fait que l'incrementer."""
    cle = f"{source}|{re.sub(r'[0-9]+', '#', titre)[:200]}"
    now = time.time()
    row = con.execute("SELECT id FROM erreurs WHERE cle=? AND vue=0 ORDER BY id DESC LIMIT 1", (cle,)).fetchone()
    if row:
        con.execute("UPDATE erreurs SET nombre=nombre+1, derniere=?, detail=? WHERE id=?", (now, detail, row[0]))
        con.commit()
        return
    con.execute("INSERT INTO erreurs(cle, niveau, source, titre, detail, premiere, derniere) VALUES (?,?,?,?,?,?,?)",
                (cle, niveau, source, titre, detail, now, now))
    con.commit()
    log.info("%s : %s : %s", niveau, source, titre)
    if niveau == "erreur" and may_notify(con):
        notify(f"Labo IA : problème dans {source}",
               f"{titre}\n{resume or ''}".strip() + "\n\nDétail : tableau de bord, page Erreurs.")


def run(*args):
    return subprocess.run(args, capture_output=True, text=True, timeout=120).stdout


def last_lines(unit, n=40):
    return run("journalctl", "-u", unit, "-n", str(n), "--no-pager", "-o", "cat")


def text(entry):
    msg = entry.get("MESSAGE", "")
    if isinstance(msg, list):  # message non UTF-8 : journald le donne en octets
        msg = bytes(msg).decode("utf-8", "replace")
    return msg.rstrip()


def check_journal(con):
    """Erreurs et avertissements ecrits par les missions depuis le dernier passage."""
    args = ["journalctl", "-o", "json", "--no-pager"]
    for unit in SERVICES:
        args += ["-u", unit]
    cursor = get(con, "curseur")
    args += ["--after-cursor", cursor] if cursor else ["--since", "-10min"]
    entries = [json.loads(line) for line in run(*args).splitlines() if line.strip()]
    blocks = {}  # une erreur en cours de lecture (message + trace Python) par service

    def flush(unit):
        b = blocks.pop(unit, None)
        if b:
            last = b["lines"][-1] if len(b["lines"]) > 1 else ""
            titre = b["titre"] or f"plantage : {last}"
            record(con, "erreur", SERVICES.get(unit, unit), titre[:300], "\n".join(b["lines"]),
                   resume=last if b["titre"] else None)

    for e in entries:
        unit = (e.get("_SYSTEMD_UNIT") or e.get("UNIT") or "?").removesuffix(".service")
        msg = text(e)
        m = LINE.match(msg)
        if m:
            flush(unit)
            if m[1] in ("ERROR", "CRITICAL"):
                blocks[unit] = {"titre": m[3], "lines": [msg], "trace": False}
            elif m[1] == "WARNING":
                record(con, "avertissement", SERVICES.get(unit, unit), m[3][:300], msg)
        elif msg.startswith("Traceback"):
            b = blocks.get(unit)
            if b is None or b["trace"]:
                flush(unit)
                b = blocks[unit] = {"titre": None, "lines": []}
            b["trace"] = True
            b["lines"].append(msg)
        elif unit in blocks:
            b = blocks[unit]
            b["lines"].append(msg)
            # La trace finit sur la ligne de l'exception, non indentee ("ValueError: ...").
            chained = msg.startswith(("During handling", "The above exception")) or not msg
            if b.get("trace") and not msg.startswith(" ") and not chained:
                flush(unit)
    for unit in list(blocks):
        flush(unit)
    if entries:
        put(con, "curseur", entries[-1]["__CURSOR"])


def check_services(con):
    """Services arretes, ou qui ont plante et redemarre tout seuls depuis le dernier passage."""
    for unit, name in SERVICES.items():
        if unit == "labo-publication":  # lancee par son timer, elle n'est active que quelques secondes
            unit, name = "labo-publication.timer", "Publication GitHub (minuterie)"
        props = dict(line.split("=", 1) for line in
                     run("systemctl", "show", unit, "-p", "LoadState", "-p", "ActiveState", "-p", "NRestarts").splitlines()
                     if "=" in line)
        if props.get("LoadState") != "loaded":
            continue  # pas installe (l'IA locale est facultative)
        restarts = int(props.get("NRestarts") or 0)
        before = get(con, f"redemarrages:{unit}")
        if before is not None and restarts > int(before):
            record(con, "erreur", name, "a planté et a redémarré tout seul", last_lines(unit),
                   resume="Il tourne de nouveau, mais regarde pourquoi il s'est arrêté.")
        put(con, f"redemarrages:{unit}", restarts)
        if props.get("ActiveState") not in ("active", "activating", "reloading"):
            record(con, "erreur", name, "est arrêté", last_lines(unit),
                   resume=f"État : {props.get('ActiveState')}. La mission ne travaille plus.")


def check_publication(con):
    if not PUBLICATION_STATUS.exists():
        return
    s = json.loads(PUBLICATION_STATUS.read_text())
    if not s["ok"] and str(s["t"]) != get(con, "publication_vue"):
        put(con, "publication_vue", s["t"])
        record(con, "erreur", "Publication GitHub", "la publication a échoué", s["msg"], resume=s["msg"])
    ok_t = float(get(con, "publication_ok") or 0)
    if s["ok"]:
        put(con, "publication_ok", s["t"])
    elif ok_t and time.time() - ok_t > STALL_PUBLICATION:
        record(con, "erreur", "Publication GitHub", "rien n'a été publié depuis plus de 12 h", s["msg"])


def check_disk(con):
    du = shutil.disk_usage(DATA)
    if du.used / du.total >= DISK_ALERT:
        record(con, "erreur", "Serveur", f"le disque est plein à {du.used / du.total:.0%}",
               f"{du.free / 1e9:.1f} Go libres sur {du.total / 1e9:.0f} Go.")


def check_progress(con):
    now = time.time()
    last = db.scalar(SONDES_DB, "SELECT MAX(added_at) FROM images")
    todo = db.scalar(SONDES_DB, "SELECT COUNT(*) FROM campaigns WHERE done=0")
    if last and todo and now - last > STALL_SONDES:
        record(con, "erreur", "Sondes Fantômes", "n'a analysé aucune photo depuis plus de 3 h",
               last_lines("labo-sondes"), resume="Le service tourne peut-être, mais il est bloqué.")
    last = db.scalar(NEURO_DB, "SELECT MAX(t) FROM sessions")
    if last and now - last > STALL_NEURONES:
        record(con, "erreur", "Labo de neurones", "n'a terminé aucune partie depuis plus de 2 h",
               last_lines("labo-neurones"), resume="Le service tourne peut-être, mais il est bloqué.")


def main():
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    con = db.connect(VEILLE_DB)
    con.executescript(SCHEMA)
    if "--test" in sys.argv:
        ok = notify("Labo IA : test", "Les notifications marchent. Tu seras prévenu ici si quelque chose casse.", 3)
        print("notification envoyée" if ok else "échec de l'envoi")
        return
    for check in (check_journal, check_services, check_publication, check_disk, check_progress):
        try:
            check(con)
        except Exception:  # la surveillance ne doit jamais se taire sans le dire
            record(con, "erreur", "Surveillance", f"la vérification « {check.__name__} » a échoué",
                   traceback.format_exc())
    con.execute("DELETE FROM erreurs WHERE vue=1 AND derniere < ?", (time.time() - 30 * 86400,))
    con.commit()


if __name__ == "__main__":
    main()
