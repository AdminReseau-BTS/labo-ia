"""Mission 1 - Sondes Fantomes.

Parcourt les images d'archives des sondes spatiales via l'API publique OPUS
(PDS Ring-Moon Systems Node, NASA). Chaque image recoit une empreinte calculee par
un reseau de neurones de vision (ResNet18), puis est comparee a toutes les autres
images de la meme cible prises par le meme instrument. Les plus isolees deviennent
des "candidates". Chacune recoit un contexte factuel (fiche officielle de la prise de vue,
comparaison avec les photos habituelles de l'astre, photos prises juste avant et apres),
puis est jugee par l'IA locale ; celles qui meritent un regard humain ont un dossier complet.
"""
import io
import json
import logging
import statistics
import threading
import time
from collections import Counter, deque
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import requests
import torch
from PIL import Image
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import NearestNeighbors
from torchvision.models import ResNet18_Weights, resnet18

from . import db, direct, llm
from .config import (CAMPAIGNS, IMAGING_INSTRUMENTS, IMG_DIR, LOG_FORMAT, OPUS_API, OPUS_DETAIL, OPUS_PREVIEWS,
                     PROBES, SEQUENCE_TEXT, SONDES_DB)

log = logging.getLogger("sondes")
RECENT = deque(maxlen=18)  # dernieres photos analysees, pour la page « En direct »
STATE = {"status": None, "target": None, "instrument": None, "ia": None}
LIVE_LOCK = threading.Lock()  # la fouille et l'IA locale ecrivent toutes deux l'etat en direct


def publish_state():
    with LIVE_LOCK:
        direct.write("sondes", {**STATE, "recent": list(RECENT)})


def show(status, camp=None):
    """Dit a la page « En direct » ce que fait la fouille en ce moment."""
    STATE.update(status=status, target=camp["target"] if camp else None,
                 instrument=camp["instrument"] if camp else None)
    publish_state()


def show_ai(text):
    """Dit a la page « En direct » ce que fait l'IA locale, en parallele de la fouille."""
    STATE["ia"] = text
    publish_state()

PAGE = 100
POLITE_DELAY = 0.5   # pause entre deux telechargements, pour menager les serveurs publics
TOP_N = 10           # candidates gardees (et decrites) par groupe
# L'IA examine d'abord le top 10 de chaque astre, puis, quand tout est fait, creuse plus loin dans le classement.
AI_DEPTHS = (TOP_N, 25, 50)
MIN_GROUP = 30       # en dessous, pas assez d'images pour savoir ce qui est "normal"
KNN_REF_MAX = 50000  # echantillon de reference pour les tres gros groupes (plus grand = « normal » mieux connu)
FILTER_VERSION = 3  # a augmenter quand le filtre d'images ratees change : les candidates y repasseront
FILL_GRAY = 105      # valeur des zones sans donnees dans les apercus OPUS
# Images techniques (calibration, poses dans le noir...) : leurs "anomalies" sont des defauts d'instrument.
SKIP_TARGET_WORDS = ("calibration", "dark", "plaque", "flat", "bias", "none", "unknown")
# Avis de l'IA locale sur chaque candidate : seules les "interessant" sont mises en avant sur GitHub.
VERDICTS = ("defaut", "connu", "interessant")
VERDICT_SCHEMA = {"type": "object", "required": ["description", "verdict"],
                  "properties": {"description": {"type": "string"}, "verdict": {"type": "string", "enum": list(VERDICTS)}}}
# Une petite IA se trompe souvent : une photo jugee "interessant" repasse une question independante,
# centree sur les defauts. Si elle y voit un defaut (bruit, lignes...), elle n'est pas mise en avant.
DEFECT_CHECK = ("Regarde cette image d'archive d'une sonde spatiale. Est-ce surtout un defaut technique plutot "
                "qu'une vraie scene : bruit ou grain aleatoire, parasites, points colores sans forme nette, lignes "
                "ou bandes, image floue, vide, coupee ou ratee ? Reponds true dans 'defaut' si c'est le cas, sinon false.")
DEFECT_SCHEMA = {"type": "object", "required": ["defaut"], "properties": {"defaut": {"type": "boolean"}}}
# Mots des noms d'observation et des notes de la NASA, traduits en indices pour l'IA et pour le lecteur.
# Les noms d'observation sont colles (« 15ISECLIPS04 ») : on cherche donc des morceaux de mots, assez longs
# pour ne pas se tromper.
OBS_HINTS = (
    ("ECLIP", "prise pendant une éclipse : l'astre est dans l'ombre de sa planète, seules ses propres lueurs se voient"),
    ("AUROR", "observation d'aurores"),
    ("LIGHTN", "recherche d'éclairs"),
    ("PLUME", "recherche de panaches (volcans, geysers)"),
    ("LIMB", "vise le bord de l'astre (le limbe), là où l'atmosphère et les panaches se voient de profil"),
    ("TERMINAT", "vise le terminateur, la frontière entre le jour et la nuit, où les reliefs font de longues ombres"),
    ("NIGHT", "vise le côté nuit"),
    ("OPNAV", "image de navigation : sert à repérer la position de la sonde grâce aux étoiles"),
    ("CALIB", "image de calibration de l'appareil"),
    ("MOSAIC", "fait partie d'une mosaïque (plusieurs photos assemblées)"),
    ("HIGHEST RES", "une des photos les plus détaillées de cet astre"),
    ("HI RES", "photo à haute résolution"),
    ("HIRES", "photo à haute résolution"),
    ("GLOBAL", "vue de l'astre en entier"),
    ("COLOR", "fait partie d'une série en couleurs (plusieurs filtres)"),
    ("RINGS", "vise aussi les anneaux"),
)
SEQUENCE_HOURS = 2     # fenetre ou l'on cherche les photos prises juste avant et apres
ODD_SCORE = 0.95       # isolement au-dessus duquel une photo voisine est elle aussi inhabituelle
TYPICAL_SAMPLE = 8     # photos ordinaires tirees au hasard pour decrire "l'habitude" d'un astre
DOSSIER_SCHEMA = {
    "type": "object", "required": ["titre", "ce_quon_voit", "pourquoi", "hypotheses", "contexte", "a_verifier",
                                   "conclusion"],
    "properties": {
        "titre": {"type": "string"}, "ce_quon_voit": {"type": "string"}, "pourquoi": {"type": "string"},
        "hypotheses": {"type": "array", "items": {
            "type": "object", "required": ["idee", "pour", "contre", "probabilite"],
            "properties": {"idee": {"type": "string"}, "pour": {"type": "string"}, "contre": {"type": "string"},
                           "probabilite": {"type": "string", "enum": ["faible", "moyenne", "forte"]}}}},
        "contexte": {"type": "string"}, "a_verifier": {"type": "array", "items": {"type": "string"}},
        "conclusion": {"type": "string"}}}

HTTP = requests.Session()
HTTP.headers["User-Agent"] = "labo-ia-sondes-fantomes/1.0 (recherche d'anomalies, projet perso)"

SCHEMA = """
CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY, instrument TEXT, target TEXT,
    next_start INTEGER DEFAULT 1, available INTEGER, done INTEGER DEFAULT 0,
    since_score INTEGER DEFAULT 0, scored_at REAL,
    UNIQUE(instrument, target));
CREATE TABLE IF NOT EXISTS images (
    opus_id TEXT PRIMARY KEY, campaign_id INTEGER, time1 TEXT, small TEXT,
    emb BLOB, artifact TEXT, score REAL, rank INTEGER, added_at REAL, filtre INTEGER);
CREATE INDEX IF NOT EXISTS images_campaign ON images(campaign_id, rank);
CREATE TABLE IF NOT EXISTS descriptions (opus_id TEXT PRIMARY KEY, text TEXT, created_at REAL, verdict TEXT);
CREATE TABLE IF NOT EXISTS journal (t REAL, msg TEXT);
CREATE TABLE IF NOT EXISTS contexte (opus_id TEXT PRIMARY KEY, data TEXT, created_at REAL);
CREATE TABLE IF NOT EXISTS habitudes (campaign_id INTEGER PRIMARY KEY, data TEXT, created_at REAL);
CREATE TABLE IF NOT EXISTS dossiers (opus_id TEXT PRIMARY KEY, data TEXT, created_at REAL);
"""


class Embedder:
    """Transforme une image en vecteur de 512 nombres qui resume son contenu."""

    def __init__(self):
        torch.set_num_threads(2)
        weights = ResNet18_Weights.DEFAULT
        model = resnet18(weights=weights)
        model.fc = torch.nn.Identity()
        self.model = model.eval()
        self.prep = weights.transforms()

    @torch.no_grad()
    def __call__(self, img):
        v = self.model(self.prep(img.convert("RGB")).unsqueeze(0))[0].numpy().astype(np.float32)
        return v / (np.linalg.norm(v) + 1e-8)


def runs(mask):
    """Debut et fin de chaque suite de True."""
    edges = np.flatnonzero(np.diff(np.concatenate(([0], mask.astype(np.int8), [0]))))
    return zip(edges[::2], edges[1::2])


def missing_data(gray):
    """Donnees manquantes : (part en marges grises des apercus OPUS, part en lignes perdues,
    nombre de bandes perdues en plein milieu de l'image).

    Une bande sombre et uniforme n'est une perte de donnees que si elle coupe l'image net : claire
    juste au-dessus et juste au-dessous, sur les memes colonnes. Le ciel noir autour d'un astre, lui,
    a des bords courbes.
    """
    rs, cs, rm = gray.std(axis=1), gray.std(axis=0), gray.mean(axis=1)
    fill = max(((rs < 1.5) & (np.abs(rm - FILL_GRAY) <= 2)).mean(),
               ((cs < 1.5) & (np.abs(gray.mean(axis=0) - FILL_GRAY) <= 2)).mean())
    lost, inner = 0, 0
    for a, b in runs((rs < 1.5) & (rm < 12)):
        sides = [np.median(s, axis=0) >= rm[a:b].mean() + 8 for s in (gray[max(a - 4, 0):a], gray[b:b + 4]) if len(s)]
        if len(sides) == 2 and (sides[0] & sides[1]).mean() >= 0.3:
            lost, inner = lost + b - a, inner + 1
        elif len(sides) == 1 and sides[0].mean() >= 0.5:
            lost += b - a
    return fill, lost / len(gray), inner


def anisotropy(gray):
    """Ecart entre lignes voisines rapporte a l'ecart entre colonnes voisines (ou l'inverse).
    ~1,3 pour une vraie scene, jusqu'a ~3,5 pour les bandes de Saturne, plus pour une image striee."""
    v = np.abs(np.diff(gray, axis=0)).mean() + 0.5
    h = np.abs(np.diff(gray, axis=1)).mean() + 0.5
    return max(v / h, h / v)


def artifact_reason(gray):
    """Ecarte les images ratees, qui sont 'bizarres' sans etre interessantes."""
    if gray.std() < 3:
        return "image presque uniforme"
    if (gray < 6).mean() > 0.995:
        return "image presque noire"
    if (gray > 250).mean() > 0.5:
        return "image saturee"
    fill, lost, inner = missing_data(gray)
    # Les apercus Voyager ont souvent un mince bord noir en haut : on ne compte une bande au bord qu'au-dela de 6 %.
    if fill >= 0.04 or lost >= 0.06 or inner:
        return "image incomplete"
    if anisotropy(gray) >= 3.8:
        return "image striee"
    # Ecart moyen entre pixels voisins rapporte au contraste : ~0.1 pour une vraie scene,
    # ~1 pour du bruit pur. Seuil volontairement haut pour garder les images bruitees mais structurees.
    fine = (np.abs(np.diff(gray, axis=0)).mean() + np.abs(np.diff(gray, axis=1)).mean()) / 2
    if fine > 0.8 * gray.std():
        return "image dominee par le bruit"
    return None


def get_json(path, **params):
    r = HTTP.get(f"{OPUS_API}/{path}", params=params, timeout=90)
    r.raise_for_status()
    return r.json()


def fetch_page(instrument, target, start):
    q = {"instrument": instrument, "target": target, "startobs": start, "limit": PAGE}
    meta = get_json("data.json", cols="opusid,time1", **q)
    imgs = get_json("images/small.json", **q)
    times = {row[0]: row[1] for row in meta["page"]}
    return imgs["data"], times, imgs["available"]


def fetch_preview(preview, opus_id):
    """Copie locale d'un apercu, pour le montrer a l'IA locale."""
    dest = IMG_DIR / f"{opus_id}{Path(preview).suffix or '.jpg'}"
    if not dest.exists():
        r = HTTP.get(OPUS_PREVIEWS + preview, timeout=60)
        r.raise_for_status()
        dest.write_bytes(r.content)
    return dest


def download(small):
    r = HTTP.get(OPUS_PREVIEWS + small, timeout=60)
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content))
    img.load()
    return img


def process_page(con, embed, camp, items, times):
    added = 0
    for it in items:
        oid, small = it["opus_id"], it.get("small")
        if not small or con.execute("SELECT 1 FROM images WHERE opus_id=?", (oid,)).fetchone():
            continue
        try:
            img = download(small)
        except (requests.RequestException, OSError) as e:
            log.warning("image %s ignoree : %s", oid, e)
            continue
        reason = artifact_reason(np.asarray(img.convert("L"), dtype=np.float32))
        con.execute(
            "INSERT INTO images(opus_id, campaign_id, time1, small, emb, artifact, filtre, added_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (oid, camp["id"], times.get(oid), small, embed(img).tobytes(), reason, FILTER_VERSION, time.time()))
        con.commit()  # tout de suite : l'IA locale ecrit dans la meme base, en parallele
        added += 1
        with LIVE_LOCK:
            RECENT.appendleft({"opus_id": oid, "small": small, "reason": reason, "time1": times.get(oid)})
        show(f"Analyse des photos de {camp['target']}", camp)
        time.sleep(POLITE_DELAY)
    return added


def pct_rank(a):
    return a.argsort().argsort() / max(len(a) - 1, 1)


def recheck(con, r):
    """Repasse une image au filtre actuel ; renvoie True si elle est ratee."""
    try:
        reason = artifact_reason(np.asarray(download(r["small"]).convert("L"), dtype=np.float32))
    except (requests.RequestException, OSError) as e:
        log.warning("image %s non reverifiee : %s", r["opus_id"], e)
        return False
    time.sleep(POLITE_DELAY)
    con.execute("UPDATE images SET artifact=?, filtre=? WHERE opus_id=?", (reason, FILTER_VERSION, r["opus_id"]))
    return reason is not None


def isolation(X):
    """Isolement de chaque image : distance a ses plus proches voisines et Isolation Forest, combines."""
    rng = np.random.default_rng(0)
    ref = X if len(X) <= KNN_REF_MAX else X[rng.choice(len(X), KNN_REF_MAX, replace=False)]
    k = min(10, len(ref) - 1)
    dist, _ = NearestNeighbors(n_neighbors=k + 1, metric="cosine").fit(ref).kneighbors(X)
    # Une image de reference a pour plus proche voisine elle-meme (distance 0) : on l'ignore.
    knn = np.where(dist[:, 0] < 1e-6, dist[:, 1:].mean(axis=1), dist[:, :k].mean(axis=1))
    Xp = PCA(n_components=min(32, len(X) - 1), random_state=0).fit_transform(X)
    iso = -IsolationForest(n_estimators=200, random_state=0).fit(Xp).score_samples(Xp)
    return (pct_rank(knn) + pct_rank(iso)) / 2


def score_campaign(con, camp, touch=True):
    """Classe les images du groupe de la plus ordinaire a la plus isolee."""
    show(f"Comparaison de toutes les photos de {camp['target']} entre elles", camp)
    if touch:
        con.execute("UPDATE campaigns SET since_score=0, scored_at=? WHERE id=?", (time.time(), camp["id"]))
        con.commit()
    while True:
        rows = con.execute("SELECT opus_id, emb, small, filtre FROM images WHERE campaign_id=? AND artifact IS NULL",
                           (camp["id"],)).fetchall()
        if len(rows) < MIN_GROUP:
            con.execute("UPDATE images SET score=NULL, rank=NULL WHERE campaign_id=?", (camp["id"],))
            con.commit()
            return []
        score = isolation(np.stack([np.frombuffer(r["emb"], dtype=np.float32) for r in rows]))
        order = np.argsort(-score)
        # Les meilleures candidates analysees avec un ancien filtre y repassent. S'il en tombe, on
        # reclasse sans elles, pour que "l'ordinaire" ne soit pas mesure avec des images ratees.
        stale = [rows[i] for i in order[:TOP_N] if (rows[i]["filtre"] or 0) < FILTER_VERSION]
        dropped = sum(recheck(con, r) for r in stale)
        con.commit()
        if not dropped:
            break
    # Ecritures groupees a la fin, une fois le calcul fait : la base n'est bloquee qu'un instant.
    con.execute("UPDATE images SET score=NULL, rank=NULL WHERE campaign_id=?", (camp["id"],))
    con.executemany("UPDATE images SET score=?, rank=? WHERE opus_id=?",
                    [(float(score[i]), pos + 1, rows[i]["opus_id"]) for pos, i in enumerate(order)])
    con.commit()
    return [rows[i]["opus_id"] for i in order[:TOP_N]]


def reclassify(con):
    """Apres un changement de filtre, repasse les candidates des cibles deja classees."""
    camps = con.execute("""SELECT DISTINCT c.* FROM campaigns c JOIN images i ON i.campaign_id = c.id
                           WHERE i.rank <= ? AND COALESCE(i.filtre, 0) < ?""", (TOP_N, FILTER_VERSION)).fetchall()
    if not camps:
        return
    count = "SELECT COUNT(*) FROM images WHERE artifact IS NOT NULL"
    before = con.execute(count).fetchone()[0]
    for camp in camps:
        score_campaign(con, camp, touch=False)
    removed = con.execute(count).fetchone()[0] - before
    db.journal(con, log, f"Filtre des images incomplètes ou striées (v{FILTER_VERSION}) : {len(camps)} cibles reclassées,"
                         f" {removed} candidates écartées.")


def connect():
    con = db.connect(SONDES_DB)
    con.executescript(SCHEMA)
    if "filtre" not in [c[1] for c in con.execute("PRAGMA table_info(images)")]:
        con.execute("ALTER TABLE images ADD COLUMN filtre INTEGER")
    if "verdict" not in [c[1] for c in con.execute("PRAGMA table_info(descriptions)")]:
        con.execute("ALTER TABLE descriptions ADD COLUMN verdict TEXT")
    return con


def metadata(opus_id):
    """Fiche officielle complete d'une image (OPUS), ou None si l'archive ne la donne pas."""
    try:
        return get_json(f"metadata/{opus_id}.json")
    except (requests.RequestException, ValueError):
        return None
    finally:
        time.sleep(POLITE_DELAY)


def as_number(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def summarize(meta, target):
    """Ce que la fiche dit de la prise de vue : quelques nombres et le nom de l'observation."""
    if not meta:
        return {}
    flat = {k: v for sec in meta.values() for k, v in sec.items() if v not in (None, "")}
    geo = meta.get(f"{target} Surface Geometry Constraints") or {}

    def pick(d, *suffixes):
        return next((v for k, v in d.items() for s in suffixes if k.lower().endswith(s) and v not in (None, "")), None)

    note = flat.get("note") or ""
    return {
        "date": flat.get("time1"), "pose_s": as_number(flat.get("observationduration")),
        "filtre": pick(flat, "filter", "filter1"), "camera": pick(flat, "camera"),
        "distance_km": as_number(pick(geo, "_centerdistance1")),
        "resolution_km": as_number(pick(geo, "_centerresolution1")),
        "phase_deg": as_number(pick(geo, "_centerphaseangle1")),
        "taille_px": as_number(pick(geo, "_diameterpixels")),
        "observation": pick(flat, "observationid", "activityname"),
        "phase_mission": pick(flat, "missionphasename", "missionphase"), "orbite": pick(flat, "orbitnumber"),
        "note": None if note.startswith("VICAR") else note,
    }


def hints(fiche):
    text = f"{fiche.get('observation') or ''} {fiche.get('note') or ''}".upper()
    return list(dict.fromkeys(h for key, h in OBS_HINTS if key in text))


def typical(con, camp, target):
    """Ce qui est habituel pour cet astre : fiches de quelques photos ordinaires tirees au hasard (une fois par astre)."""
    row = con.execute("SELECT data FROM habitudes WHERE campaign_id=?", (camp,)).fetchone()
    if row:
        return json.loads(row[0])
    sample = con.execute("SELECT opus_id, small FROM images WHERE campaign_id=? AND artifact IS NULL AND score < 0.5"
                         " ORDER BY random() LIMIT ?", (camp, TYPICAL_SAMPLE)).fetchall()
    fiches = [f for f in (summarize(metadata(s["opus_id"]), target) for s in sample) if f]
    data = {"images": [{"opus_id": s["opus_id"], "small": s["small"]} for s in sample[:4]]}
    for k in ("pose_s", "distance_km", "resolution_km", "phase_deg", "taille_px"):
        values = [f[k] for f in fiches if f.get(k) is not None]
        data[k] = statistics.median(values) if values else None
    filters = Counter(f["filtre"] for f in fiches if f.get("filtre"))
    data["filtre"] = filters.most_common(1)[0][0] if filters else None
    con.execute("INSERT OR REPLACE INTO habitudes VALUES (?,?,?)", (camp, json.dumps(data), time.time()))
    return data


def km(x):
    return f"{x:,.0f} km".replace(",", " ")


def differences(f, usual):
    """Ce qui distingue cette prise de vue des photos habituelles de l'astre, en phrases simples."""
    out = []
    d, u = f.get("distance_km"), usual.get("distance_km")
    if d and u and (d < u / 3 or d > u * 3):
        out.append(f"prise {'beaucoup plus près' if d < u else 'beaucoup plus loin'} que d'habitude"
                   f" ({km(d)} contre {km(u)} en général)")
    p, up = f.get("phase_deg"), usual.get("phase_deg")
    if p is not None and p >= 150:
        out.append(f"prise à contre-jour (angle de phase {p:.0f}° : le Soleil est presque derrière l'astre)")
    elif p is not None and up is not None and abs(p - up) >= 40:
        out.append(f"éclairage très différent de d'habitude (angle de phase {p:.0f}° contre {up:.0f}° ;"
                   " 0° = Soleil dans le dos de la sonde, 180° = contre-jour)")
    t, ut = f.get("pose_s"), usual.get("pose_s")
    if t and ut and (t > ut * 5 or t < ut / 5):
        out.append(f"temps de pose {'bien plus long' if t > ut else 'bien plus court'} que d'habitude"
                   f" ({t:.3g} s contre {ut:.3g} s)")
    if f.get("filtre") and usual.get("filtre") and f["filtre"] != usual["filtre"]:
        out.append(f"filtre « {f['filtre']} », alors que la plupart des photos sont prises en « {usual['filtre']} »")
    size = f.get("taille_px")
    if size is not None and size < 15:
        out.append(f"l'astre ne mesure que {size:.0f} pixels sur la photo : presque un point")
    return out


def sequence(con, camp, opus_id, time1):
    """Photos du meme astre prises juste avant et juste apres. Si elles sont aussi inhabituelles, le
    phenomene dure ; si elles sont normales, c'est bref, ou c'est un accident de cette seule image."""
    try:
        t = datetime.fromisoformat(time1)
    except (TypeError, ValueError):
        return None
    lo, hi = ((t + timedelta(hours=h)).isoformat() for h in (-SEQUENCE_HOURS, SEQUENCE_HOURS))
    near = con.execute("SELECT opus_id, small, time1, score, artifact FROM images WHERE campaign_id=?"
                       " AND time1 BETWEEN ? AND ? AND opus_id != ?", (camp, lo, hi, opus_id)).fetchall()
    found = []
    for n in near:
        try:
            found.append((round((datetime.fromisoformat(n["time1"]) - t).total_seconds() / 60, 1), n))
        except ValueError:
            continue
    found.sort(key=lambda x: x[0])
    picked = [x for x in found if x[0] < 0][-2:] + [x for x in found if x[0] > 0][:2]
    neighbours = [{"opus_id": n["opus_id"], "small": n["small"], "minutes": m, "ratee": n["artifact"] is not None,
                   "inhabituelle": n["score"] is not None and n["score"] >= ODD_SCORE} for m, n in picked]
    usable = [n for n in neighbours if not n["ratee"]]
    if not usable:
        verdict = "seule"
    elif sum(n["inhabituelle"] for n in usable) * 2 >= len(usable):
        verdict = "dure"
    else:
        verdict = "isolee"
    return {"voisines": neighbours, "verdict": verdict}


def build_context(con, r):
    """Tout ce qu'on sait de la prise de vue, avant de demander l'avis de l'IA."""
    fiche = summarize(metadata(r["opus_id"]), r["target"])
    usual = typical(con, r["campaign_id"], r["target"])
    ctx = {"fiche": fiche, "indices": hints(fiche), "differences": differences(fiche, usual), "habituel": usual,
           "sequence": sequence(con, r["campaign_id"], r["opus_id"], r["time1"]), "rang": r["rank"], "groupe": r["n"]}
    con.execute("INSERT OR REPLACE INTO contexte VALUES (?,?,?)", (r["opus_id"], json.dumps(ctx), time.time()))
    con.commit()
    return ctx


def context_text(ctx):
    """Le contexte en quelques lignes, pour l'IA."""
    f, lines = ctx["fiche"], []
    if f.get("observation"):
        lines.append(f"nom de l'observation à la NASA : {f['observation']}")
    if f.get("note"):
        lines.append(f"note de la NASA : {f['note']}")
    if f.get("phase_mission") or f.get("orbite"):
        lines.append(f"moment de la mission : {f.get('phase_mission') or 'orbite ' + str(f['orbite'])}")
    if f.get("filtre"):
        lines.append(f"filtre : {f['filtre']}")
    if f.get("pose_s") is not None:
        lines.append(f"temps de pose : {f['pose_s']:.3g} s")
    if f.get("distance_km"):
        lines.append(f"distance à l'astre : {km(f['distance_km'])}")
    if f.get("phase_deg") is not None:
        lines.append(f"angle de phase : {f['phase_deg']:.0f}°")
    lines += [f"indice : {h}" for h in ctx["indices"]] + [f"différence : {d}" for d in ctx["differences"]]
    if ctx["sequence"]:
        lines.append("photos voisines : " + SEQUENCE_TEXT[ctx["sequence"]["verdict"]])
    lines.append(f"rang : n°{ctx['rang']} sur {ctx['groupe']} photos de cet astre, de la plus étrange à la plus banale")
    return "\n".join(f"- {line}" for line in lines)


def write_dossier(r, ctx, description):
    """Dossier complet d'une trouvaille : hypotheses pour et contre, contexte, verifications."""
    prompt = (
        f"Tu es planetologue et tu ecris pour le grand public, en francais simple. Une photo de {r['target']} prise par "
        f"la camera {r['instrument']} {PROBES.get(r['instrument'], 'd une sonde spatiale')} le {r['time1']} a ete "
        "reperee comme inhabituelle, puis jugee digne d'un regard humain.\n"
        f"Ce qu'on y voit (description faite en regardant la photo) : {description}\n"
        f"Informations sur la prise de vue :\n{context_text(ctx)}\n\n"
        "Ecris son dossier. 'titre' : un titre court et parlant. 'ce_quon_voit' : 2 ou 3 phrases. 'pourquoi' : pourquoi "
        "elle sort du lot, en t'appuyant sur les informations ci-dessus. 'hypotheses' : 3 explications possibles, de la "
        "plus banale (defaut de l'appareil, angle de vue) a la plus interessante, chacune avec un argument pour, un "
        "argument contre et une probabilite. 'contexte' : ce que la science sait deja de cet astre et qui aide a "
        "comprendre la photo ; uniquement des faits generaux tres connus, et dis-le si tu n'es pas sur. 'a_verifier' : "
        "2 a 4 verifications concretes qu'un humain pourrait faire (par exemple regarder les photos voisines, la photo "
        "brute, d'autres filtres, des articles). 'conclusion' : 1 ou 2 phrases honnetes. N'invente ni nom de cratere, "
        "ni date, ni chiffre qui ne soit pas donne ici.")
    return llm.ask(prompt, schema=DOSSIER_SCHEMA)


def pending(con, limit):
    """Prochaines pistes a examiner : le top 10 de chaque astre d'abord, puis plus loin dans le classement."""
    for depth in AI_DEPTHS:
        rows = con.execute(
            """SELECT i.opus_id, i.time1, i.small, i.rank, i.campaign_id, c.instrument, c.target,
                      (SELECT COUNT(*) FROM images j WHERE j.campaign_id = i.campaign_id AND j.artifact IS NULL) AS n
               FROM images i JOIN campaigns c ON c.id = i.campaign_id
               LEFT JOIN descriptions d ON d.opus_id = i.opus_id
               WHERE i.rank <= ? AND d.opus_id IS NULL ORDER BY i.rank LIMIT ?""", (depth, limit)).fetchall()
        if rows:
            return rows
    return []


def describe_pending(con, limit=1):
    """Fait examiner par l'IA locale les meilleures pistes pas encore examinees."""
    if not llm.available():
        return 0
    rows = pending(con, limit)
    for r in rows:
        show_ai(f"le labo rassemble la fiche NASA d'une photo bizarre de {r['target']} (n°{r['rank']})")
        ctx = build_context(con, r)
        show_ai(f"l'IA locale examine une photo bizarre de {r['target']} (n°{r['rank']})")
        try:
            path = fetch_preview(r["small"].replace("_small.", "_med."), r["opus_id"])
        except requests.RequestException:
            path = fetch_preview(r["small"], r["opus_id"])
        prompt = (
            f"Tu es planetologue. Cette image d'archive vient de la camera {r['instrument']} "
            f"{PROBES.get(r['instrument'], 'd une sonde spatiale')}, cible : {r['target']}, prise le {r['time1']}. "
            "Ne cite pas d'autre engin spatial ni d'autre instrument. Un algorithme l'a reperee comme "
            "inhabituelle par rapport aux autres images de cette cible.\n"
            f"Informations officielles sur la prise de vue :\n{context_text(ctx)}\n\n"
            "Dans 'description', en 3 ou 4 phrases simples en francais, comprehensibles par quelqu'un qui n'y connait "
            "rien : decris ce que tu vois et explique ton avis, en t'aidant des informations ci-dessus. Dans 'verdict', "
            "choisis : 'defaut' si c'est un defaut d'image (bruit, saturation, lignes perdues, image ratee ou vide), "
            "'connu' si c'est banal ou si les informations l'expliquent (eclipse, contre-jour, astre minuscule, "
            "calibration, navigation, bord de la planete, anneaux, etoile, ombre, angle de vue inhabituel), "
            "'interessant' seulement si cela merite vraiment un regard humain. Dans le doute entre 'connu' et "
            "'interessant', choisis 'connu'. N'invente aucun fait.")
        try:
            out = llm.ask(prompt, image_path=path, schema=VERDICT_SCHEMA)
            description = str(out["description"]).strip()
        except (ValueError, KeyError):
            # Reponse illisible : on passe a la suite plutot que de bloquer l'examen sur cette photo.
            log.warning("reponse illisible de l'IA pour %s, piste mise de cote", r["opus_id"])
            con.execute("INSERT OR REPLACE INTO descriptions VALUES (?,?,?,?)",
                        (r["opus_id"], "L'IA du labo n'a pas réussi à examiner cette photo.", time.time(), None))
            con.commit()
            continue
        verdict = out["verdict"] if out.get("verdict") in VERDICTS else "connu"
        if verdict == "interessant" and llm.ask(DEFECT_CHECK, image_path=path, schema=DEFECT_SCHEMA).get("defaut"):
            verdict = "defaut"
        con.execute("INSERT OR REPLACE INTO descriptions VALUES (?,?,?,?)", (r["opus_id"], description, time.time(), verdict))
        con.commit()
        if verdict == "interessant":
            show_ai(f"l'IA locale écrit le dossier d'une trouvaille sur {r['target']}")
            dossier = write_dossier(r, ctx, description)
            con.execute("INSERT OR REPLACE INTO dossiers VALUES (?,?,?)", (r["opus_id"], json.dumps(dossier), time.time()))
            con.commit()
            title = str(dossier.get("titre") or f"trouvaille possible sur {r['target']}")
            db.journal(con, log, f"Trouvaille sur {r['target']} ({r['instrument']}) : « {title} » ({r['opus_id']}).")
            from .veille import notify
            notify(f"Labo IA : {title}", f"{r['target']} : {description}", 3, click=OPUS_DETAIL + r["opus_id"])
    return len(rows)


def examine_forever():
    """L'IA locale examine les pistes une par une, en parallele de la fouille (qui ne l'attend plus)."""
    con = connect()
    con.execute("PRAGMA busy_timeout = 600000")  # la fouille peut tenir la base quelques minutes en classant un astre
    while True:
        try:
            if not describe_pending(con):
                show_ai("l'IA locale attend de nouvelles pistes" if llm.available() else None)
                time.sleep(300)
        except (requests.RequestException, OSError) as e:
            log.warning("IA locale ou archive NASA injoignable (%s), nouvel essai dans 5 min", e)
            show_ai("IA locale ou archive NASA injoignable : nouvel essai dans 5 minutes")
            time.sleep(300)
        except Exception:  # l'examen ne doit jamais s'arreter pour de bon
            log.exception("examen d'une piste interrompu")
            time.sleep(300)


def discover_campaigns(con):
    """Une fois la liste de depart finie, etend la fouille a toute l'archive d'imagerie."""
    added = 0
    for inst in IMAGING_INSTRUMENTS:
        mults = get_json("meta/mults/target.json", instrument=inst)["mults"]
        for target, n in sorted(mults.items(), key=lambda kv: kv[1]):
            if n < MIN_GROUP or any(w in target.lower() for w in SKIP_TARGET_WORDS):
                continue
            cur = con.execute("INSERT OR IGNORE INTO campaigns(instrument, target) VALUES (?,?)", (inst, target))
            added += cur.rowcount
    con.commit()
    return added


def run_once(con, embed):
    camp = con.execute("SELECT * FROM campaigns WHERE done=0 ORDER BY id LIMIT 1").fetchone()
    if camp is None:
        added = discover_campaigns(con)
        if added:
            db.journal(con, log, f"{added} nouvelles cibles ajoutées à la fouille.")
        else:
            db.journal(con, log, "Toute l'archive d'imagerie est fouillée. Nouvelle vérification dans 24 h.")
            show("Toute l'archive est fouillée : en attente de nouvelles photos (vérification toutes les 24 h)")
            time.sleep(86400)
        return

    items, times, available = fetch_page(camp["instrument"], camp["target"], camp["next_start"])
    added = process_page(con, embed, camp, items, times)
    next_start = camp["next_start"] + PAGE
    done = int(not items or next_start > available)
    con.execute("UPDATE campaigns SET next_start=?, available=?, done=?, since_score=since_score+? WHERE id=?",
                (next_start, available, done, added, camp["id"]))
    con.commit()

    camp = con.execute("SELECT * FROM campaigns WHERE id=?", (camp["id"],)).fetchone()
    total = con.execute("SELECT COUNT(*) FROM images WHERE campaign_id=?", (camp["id"],)).fetchone()[0]
    if done or camp["since_score"] >= max(1000, total // 10):
        top = score_campaign(con, camp)
        name = f"{camp['target']} ({camp['instrument']})"
        end = " Fouille terminée." if done else ""
        if top:
            db.journal(con, log, f"{name} : {total} images analysées, candidate n°1 : {top[0]}.{end}")
        elif done:
            db.journal(con, log, f"{name} : seulement {total} images, trop peu pour comparer.{end}")


def main():
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    con = connect()
    con.execute("PRAGMA busy_timeout = 120000")  # l'IA locale ecrit aussi dans la base, en parallele
    for inst, target in CAMPAIGNS:
        con.execute("INSERT OR IGNORE INTO campaigns(instrument, target) VALUES (?,?)", (inst, target))
    con.commit()
    embed = Embedder()
    db.journal(con, log, "Mission Sondes Fantômes démarrée.")
    reclassify(con)
    threading.Thread(target=examine_forever, name="examen", daemon=True).start()
    while True:
        try:
            run_once(con, embed)
        except (requests.RequestException, ValueError, KeyError) as e:
            log.warning("probleme reseau ou API (%s), nouvel essai dans 5 min", e)
            show("Problème de réseau ou de l'archive NASA : nouvel essai dans 5 minutes")
            time.sleep(300)


if __name__ == "__main__":
    main()
