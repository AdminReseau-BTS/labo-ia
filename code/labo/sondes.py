"""Mission 1 - Sondes Fantomes.

Parcourt les images d'archives des sondes spatiales via l'API publique OPUS
(PDS Ring-Moon Systems Node, NASA). Chaque image recoit une empreinte calculee par
un reseau de neurones de vision (ResNet18), puis est comparee a toutes les autres
images de la meme cible prises par le meme instrument. Les plus isolees deviennent
des "candidates", decrites par l'IA locale si elle est installee.
"""
import io
import logging
import time
from collections import deque
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
from .config import CAMPAIGNS, IMAGING_INSTRUMENTS, IMG_DIR, LOG_FORMAT, OPUS_API, OPUS_PREVIEWS, SONDES_DB

log = logging.getLogger("sondes")
RECENT = deque(maxlen=18)  # dernieres photos analysees, pour la page « En direct »


def show(status, camp=None):
    """Dit a la page « En direct » ce que fait la mission en ce moment."""
    direct.write("sondes", {"status": status, "target": camp["target"] if camp else None,
                            "instrument": camp["instrument"] if camp else None, "recent": list(RECENT)})

PAGE = 100
POLITE_DELAY = 0.5   # pause entre deux telechargements, pour menager les serveurs publics
TOP_N = 10           # candidates gardees (et decrites) par groupe
MIN_GROUP = 30       # en dessous, pas assez d'images pour savoir ce qui est "normal"
KNN_REF_MAX = 20000  # echantillon de reference pour les tres gros groupes
FILTER_VERSION = 3  # a augmenter quand le filtre d'images ratees change : les candidates y repasseront
FILL_GRAY = 105      # valeur des zones sans donnees dans les apercus OPUS
# Images techniques (calibration, poses dans le noir...) : leurs "anomalies" sont des defauts d'instrument.
SKIP_TARGET_WORDS = ("calibration", "dark", "plaque", "flat", "bias", "none", "unknown")
# Avis de l'IA locale sur chaque candidate : seules les "interessant" sont mises en avant sur GitHub.
VERDICTS = ("defaut", "connu", "interessant")
VERDICT_SCHEMA = {"type": "object", "required": ["description", "verdict"],
                  "properties": {"description": {"type": "string"}, "verdict": {"type": "string", "enum": list(VERDICTS)}}}

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
        added += 1
        RECENT.appendleft({"opus_id": oid, "small": small, "reason": reason, "time1": times.get(oid)})
        show(f"Analyse des photos de {camp['target']}", camp)
        time.sleep(POLITE_DELAY)
    con.commit()
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
        con.execute("UPDATE images SET score=NULL, rank=NULL WHERE campaign_id=?", (camp["id"],))
        if len(rows) < MIN_GROUP:
            con.commit()
            return []
        score = isolation(np.stack([np.frombuffer(r["emb"], dtype=np.float32) for r in rows]))
        order = np.argsort(-score)
        # Les meilleures candidates analysees avec un ancien filtre y repassent. S'il en tombe, on
        # reclasse sans elles, pour que "l'ordinaire" ne soit pas mesure avec des images ratees.
        stale = [rows[i] for i in order[:TOP_N] if (rows[i]["filtre"] or 0) < FILTER_VERSION]
        if not sum(recheck(con, r) for r in stale):
            break
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


def describe_pending(con, limit=1):
    """Fait decrire par l'IA locale les meilleures candidates pas encore decrites."""
    if not llm.available():
        return 0
    rows = con.execute(
        """SELECT i.opus_id, i.time1, i.small, c.instrument, c.target FROM images i
           JOIN campaigns c ON c.id = i.campaign_id
           LEFT JOIN descriptions d ON d.opus_id = i.opus_id
           WHERE i.rank <= ? AND d.opus_id IS NULL ORDER BY i.rank LIMIT ?""",
        (TOP_N, limit)).fetchall()
    for r in rows:
        show(f"L'IA locale décrit une photo bizarre de {r['target']}", r)
        try:
            path = fetch_preview(r["small"].replace("_small.", "_med."), r["opus_id"])
        except requests.RequestException:
            path = fetch_preview(r["small"], r["opus_id"])
        prompt = (
            f"Tu es planetologue. Cette image d'archive vient de l'instrument {r['instrument']}, "
            f"cible : {r['target']}, prise le {r['time1']}. Un algorithme l'a reperee comme "
            "inhabituelle par rapport aux autres images de cette cible. Dans 'description', en 3 ou 4 "
            "phrases simples en francais, comprehensibles par quelqu'un qui n'y connait rien : decris ce "
            "que tu vois et explique ton avis. Dans 'verdict', choisis : 'defaut' si c'est un defaut "
            "d'image (bruit, saturation, lignes perdues, image ratee ou vide), 'connu' si c'est quelque "
            "chose de banal ou deja connu (bord de la planete, anneaux, etoile, ombre, prise de vue "
            "inhabituelle), 'interessant' seulement si cela merite vraiment un regard humain. Dans le "
            "doute entre 'connu' et 'interessant', choisis 'connu'. N'invente aucun fait.")
        out = llm.ask(prompt, image_path=path, schema=VERDICT_SCHEMA)
        verdict = out["verdict"] if out.get("verdict") in VERDICTS else "connu"
        con.execute("INSERT OR REPLACE INTO descriptions VALUES (?,?,?,?)",
                    (r["opus_id"], str(out["description"]).strip(), time.time(), verdict))
        con.commit()
        if verdict == "interessant":
            db.journal(con, log, f"Trouvaille possible sur {r['target']} ({r['instrument']}) : {r['opus_id']}.")
    return len(rows)


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
            db.journal(con, log, f"Liste de départ terminée : {added} nouvelles cibles ajoutées à la fouille.")
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
    describe_pending(con)


def main():
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    con = connect()
    for inst, target in CAMPAIGNS:
        con.execute("INSERT OR IGNORE INTO campaigns(instrument, target) VALUES (?,?)", (inst, target))
    con.commit()
    embed = Embedder()
    db.journal(con, log, "Mission Sondes Fantômes démarrée.")
    reclassify(con)
    while True:
        try:
            run_once(con, embed)
        except (requests.RequestException, ValueError, KeyError) as e:
            log.warning("probleme reseau ou API (%s), nouvel essai dans 5 min", e)
            show("Problème de réseau ou de l'archive NASA : nouvel essai dans 5 minutes")
            time.sleep(300)


if __name__ == "__main__":
    main()
