"""Mission 2 - Labo de neurones simules.

Le labo cherche, jour et nuit, comment apprendre Pong a une culture de 20 000
neurones virtuels (labo.culture), sur le modele de l'experience DishBrain de
Cortical Labs (Kagan et al., Neuron 2022) faite avec de vrais neurones.

Chaque "recette" (facon de stimuler la culture et de lui signaler ses erreurs)
est jouee sur plusieurs cultures. Les meilleures sont mutees (algorithme
evolutionniste) ou parfois proposees par l'IA locale, puis verifiees par une
contre-epreuve : la meme recette sur des cultures sans plasticite, qui ne
peuvent pas apprendre. Tout passe par l'API officielle `cl` : le meme code
pourrait piloter une vraie puce CL1.
"""
import gc
import json
import logging
import os
import time
from collections import deque
from pathlib import Path

import numpy as np
import requests

os.environ.setdefault("CL_SDK_ACCELERATED_TIME", "1")  # aussi vite que le processeur le permet
os.environ.setdefault("CL_SDK_VISUALISATION", "0")
import cl  # noqa: E402
from cl import BurstDesign, ChannelSet, StimDesign  # noqa: E402
from cl._sim import _data_buffer  # noqa: E402

from . import culture, db, direct, llm  # noqa: E402
from .config import CULTURE_SIZE, FEEDBACK_MODES, LOG_FORMAT, NEURO_DB  # noqa: E402

log = logging.getLogger("neurones")

# En temps accelere, la boucle de cl-sdk n'attend que 0,1 s le processus qui calcule les neurones, puis
# abandonne la partie. Sur un serveur partage (IA locale, autres machines de l'hote), une simple pause du
# systeme suffit. On attend comme le reste du SDK (30 s) : le calcul est le meme, seule la patience change.
PRODUCER_GRACE_S = 30.0
_wait_for_timestamp = _data_buffer.SharedDataBuffer.wait_for_timestamp


def _patient_wait(self, target_timestamp, timeout_seconds=None):
    if timeout_seconds is not None:
        timeout_seconds = max(timeout_seconds, PRODUCER_GRACE_S)
    return _wait_for_timestamp(self, target_timestamp, timeout_seconds)


_data_buffer.SharedDataBuffer.wait_for_timestamp = _patient_wait

CULTURE_FILE = Path("/dev/shm") / f"labo-culture-{os.getpid()}.pkl"  # culture construite d'avance, en RAM

TICKS_PER_SECOND = 100
WARMUP_S = 60         # la culture vit seule une minute avant la partie
GAME_MIN = 15
WINDOW_MIN = 5        # "debut" = 5 premieres minutes, "fin" = 5 dernieres
SEARCH_SEEDS = (1, 2, 3)
CONFIRM_EVERY = 10    # une contre-epreuve toutes les 10 recettes
MIN_EFFECT = 0.05     # en dessous de 5 points, on ne parle pas d'apprentissage
FRAME_TICKS = 5       # page « En direct » : une image de la partie toutes les 50 ms simulees...
CLIP_FRAMES = 200     # ... soit les 10 dernieres secondes de jeu
LIVE_EVERY = 1.5      # ... envoyees toutes les 1,5 s (a 20 000 neurones, la simulation va a peu pres en temps reel)

# Disposition sur la puce (canal = ligne * 8 + colonne), inspiree de DishBrain :
# 8 electrodes sensorielles au centre, zones motrices "haut" et "bas" en diagonale.
SENSORY = (19, 20, 27, 28, 35, 36, 43, 44)
UP = (8, 9, 16, 17, 46, 47, 54, 55)
DOWN = (14, 15, 22, 23, 40, 41, 48, 49)

SPACE = {
    "sens_amp": (0.3, 2.5),    # courant des stimulations sensorielles (uA)
    "fb_amp": (0.3, 2.5),      # courant des stimulations de retour (uA)
    "fb_seconds": (0.5, 6.0),  # duree du retour apres une balle ratee (s)
    "fb_rate": (2.0, 30.0),    # frequence du retour imprevisible (Hz)
    "hit_pulses": (0, 20),     # impulsions du retour previsible apres un renvoi
    "rate_min": (2.0, 10.0),   # frequence sensorielle quand la balle est loin (Hz)
    "rate_max": (15.0, 50.0),  # ... et quand elle arrive sur la raquette
    "gain": (0.5, 4.0),        # vitesse de la raquette
    "stdp_tau": (10.0, 80.0),  # hypothese biologique : fenetre de plasticite (ms)
    "target_hz": (0.8, 3.0),   # hypothese biologique : activite visee par l'homeostasie (Hz)
}
# Point de depart : le protocole publie de DishBrain.
DISHBRAIN = {"mode": "fep", "sens_amp": 1.0, "fb_amp": 1.0, "fb_seconds": 4.0, "fb_rate": 5.0,
             "hit_pulses": 10, "rate_min": 4.0, "rate_max": 40.0, "gain": 2.0,
             "stdp_tau": 20.0, "target_hz": 1.5}

SCHEMA = """
CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY, params TEXT, origin TEXT, created_at REAL,
    early REAL, late REAL, learning REAL, hit_rate REAL, confirmed REAL, control REAL, neurons INTEGER);
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY, recipe_id INTEGER, seed INTEGER, plastic INTEGER, t REAL,
    sim_s REAL, wall REAL, hits INTEGER, misses INTEGER, early REAL, late REAL,
    curve TEXT, spikes_per_s REAL);
CREATE TABLE IF NOT EXISTS journal (t REAL, msg TEXT);
"""

LLM_SCHEMA = {
    "type": "object",
    "properties": {
        "hypothese": {"type": "string"},
        "recette": {
            "type": "object",
            "properties": {"mode": {"type": "string", "enum": list(FEEDBACK_MODES)},
                           **{k: {"type": "number"} for k in SPACE}},
            "required": ["mode", *SPACE],
        },
    },
    "required": ["hypothese", "recette"],
}


class Pong:
    """Pong a une raquette contre un mur. La culture voit la balle par ses
    electrodes sensorielles et bouge la raquette par ses zones motrices."""

    PADDLE = 0.25  # hauteur de la raquette (fraction du terrain)
    SPEED = 0.6    # vitesse horizontale de la balle (terrains par seconde)

    def __init__(self, recipe, rng, info=None):
        self.r, self.rng, self.info = recipe, rng, info
        self.dt = 1 / TICKS_PER_SECOND
        self.region = np.zeros(64, np.int8)
        self.region[list(UP)] = 1
        self.region[list(DOWN)] = -1
        self.sens = StimDesign(160, -recipe["sens_amp"], 160, recipe["sens_amp"])
        self.fb = StimDesign(160, -recipe["fb_amp"], 160, recipe["fb_amp"])
        self.paddle, self.pause, self.phase = 0.5, 0.0, 0.0
        self.hits = np.zeros(GAME_MIN, int)
        self.misses = np.zeros(GAME_MIN, int)
        self.spikes = 0
        self.act = np.zeros(64, int)  # impulsions par electrode depuis la derniere image en direct
        self.frames = deque(maxlen=CLIP_FRAMES)
        self.event, self.n, self.shown = 0, 0, 0.0
        self.serve()

    def serve(self):
        self.x, self.y = 1.0, self.rng.uniform(0.1, 0.9)
        self.vx = -self.SPEED
        self.vy = self.rng.choice((-1, 1)) * self.rng.uniform(0.2, 0.6)

    def tick(self, neurons, t, spikes):
        """t : secondes depuis le debut de la partie (negatif pendant l'echauffement)."""
        self.spikes += len(spikes)
        if self.info is not None:
            for s in spikes:
                self.act[s.channel] += 1
            self.n += 1
            if self.n % FRAME_TICKS == 0:
                self.record(t)
        if t < 0:
            return
        r = self.r
        if self.pause > 0:
            self.pause -= self.dt
            if r["mode"] == "fep" and self.rng.random() < r["fb_rate"] * self.dt:
                neurons.stim(int(self.rng.choice(SENSORY)), self.fb)  # retour imprevisible
            if self.pause <= 0:
                self.serve()
            return

        up = down = 0
        for s in spikes:
            side = self.region[s.channel]
            up += side > 0
            down += side < 0
        if up + down:
            half = self.PADDLE / 2
            move = r["gain"] * (down - up) / (up + down) * self.dt
            self.paddle = min(max(self.paddle + move, half), 1 - half)

        self.x += self.vx * self.dt
        self.y += self.vy * self.dt
        if not 0 <= self.y <= 1:
            self.vy = -self.vy
            self.y = min(max(self.y, 0.0), 1.0)
        if self.x >= 1:
            self.vx = -self.SPEED
        elif self.x <= 0:
            minute = min(int(t // 60), GAME_MIN - 1)
            if abs(self.y - self.paddle) <= self.PADDLE / 2:
                self.hits[minute] += 1
                self.event = 1
                self.x, self.vx = 0.0, self.SPEED
                if r["mode"] == "fep" and r["hit_pulses"]:  # retour previsible
                    neurons.stim(ChannelSet(*SENSORY), self.fb, BurstDesign(r["hit_pulses"], 100))
            else:
                self.misses[minute] += 1
                self.event = 2
                if r["mode"] == "none":
                    self.serve()
                else:
                    self.pause = r["fb_seconds"]
            return

        # La balle est codee par la position (quelle electrode) et la distance (frequence).
        self.phase += (r["rate_min"] + (r["rate_max"] - r["rate_min"]) * (1 - self.x)) * self.dt
        if self.phase >= 1:
            self.phase -= 1
            neurons.stim(SENSORY[min(int(self.y * 8), 7)], self.sens)

    def record(self, t):
        """Garde une image de la partie (balle, raquette, activite des 64 electrodes) pour la page
        « En direct », et y envoie regulierement les 10 dernieres secondes de jeu."""
        self.frames.append([round(self.x, 3), round(self.y, 3), round(self.paddle, 3), self.event,
                            int(self.pause > 0), "".join(str(min(int(a), 9)) for a in self.act)])
        self.act[:] = 0
        self.event = 0
        if time.time() - self.shown < LIVE_EVERY:
            return
        self.shown = time.time()
        direct.write("neurones", {
            **self.info, "sim_t": round(t, 1), "hits": int(self.hits.sum()), "misses": int(self.misses.sum()),
            "curve": [round(float(a / (a + b)), 3) if a + b else None for a, b in zip(self.hits, self.misses)],
            "frame_s": FRAME_TICKS / TICKS_PER_SECOND, "frames": list(self.frames),
            "sensory": SENSORY, "up": UP, "down": DOWN})

    def result(self):
        h, m = self.hits, self.misses

        def rate(sl):
            n = h[sl].sum() + m[sl].sum()
            return float(h[sl].sum() / n) if n else 0.0

        return {
            "hits": int(h.sum()), "misses": int(m.sum()),
            "early": rate(slice(0, WINDOW_MIN)), "late": rate(slice(GAME_MIN - WINDOW_MIN, GAME_MIN)),
            "curve": [round(float(a / (a + b)), 3) if a + b else None for a, b in zip(h, m)],
            "spikes_per_s": self.spikes / (WARMUP_S + GAME_MIN * 60),
        }


def run_session(recipe, seed, plastic, info=None):
    config = {"seed": int(seed), "plastic": bool(plastic), "n": CULTURE_SIZE,
              "stdp_tau_ms": float(recipe["stdp_tau"]), "target_hz": float(recipe["target_hz"])}
    start = time.time()
    culture.prepare(CULTURE_FILE, **config)
    cl.sim.set_simulator_data_source("labo.culture:create_source", config={**config, "path": str(CULTURE_FILE)},
                                     metadata=culture.METADATA)
    game = Pong(recipe, np.random.default_rng(seed), info)
    sim_s = WARMUP_S + GAME_MIN * 60
    try:
        with cl.open(wait_until_recordable=False) as neurons:
            for tick in neurons.loop(TICKS_PER_SECOND, stop_after_seconds=sim_s, ignore_jitter=True):
                game.tick(neurons, tick.iteration / TICKS_PER_SECOND - WARMUP_S, tick.analysis.spikes)
    finally:
        CULTURE_FILE.unlink(missing_ok=True)
    gc.collect()
    return {**game.result(), "sim_s": sim_s, "wall": time.time() - start}


def play(con, recipe_id, recipe, seed, plastic, what="Test"):
    info = {"what": f"{what} de la recette n°{recipe_id}", "recipe": describe(recipe),
            "seed": int(seed), "plastic": bool(plastic)}
    try:
        try:
            res = run_session(recipe, seed, plastic, info)
        except TimeoutError:
            # Le simulateur abandonne s'il prend trop de retard quand le processeur est tres occupe
            # (IA locale, autre mission) : on rejoue la meme session une fois, apres une pause.
            log.warning("simulateur en retard (recette %s, culture %s) : session rejouée", recipe_id, seed)
            time.sleep(60)
            res = run_session(recipe, seed, plastic, info)
    except Exception:  # le labo tourne 24 h/24 : une session ratee ne doit pas l'arreter
        log.exception("session interrompue (recette %s, culture %s)", recipe_id, seed)
        time.sleep(30)
        return None
    con.execute(
        "INSERT INTO sessions(recipe_id, seed, plastic, t, sim_s, wall, hits, misses, early, late,"
        " curve, spikes_per_s) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (recipe_id, seed, int(plastic), time.time(), res["sim_s"], res["wall"], res["hits"],
         res["misses"], res["early"], res["late"], json.dumps(res["curve"]), res["spikes_per_s"]))
    con.commit()
    return res


def describe(recipe):
    return (f"{FEEDBACK_MODES[recipe['mode']]}, stimulation {recipe['sens_amp']:.1f} µA, "
            f"plasticité {recipe['stdp_tau']:.0f} ms, activité visée {recipe['target_hz']:.1f} Hz")


def clean(recipe):
    out = {"mode": recipe["mode"] if recipe.get("mode") in FEEDBACK_MODES else "fep"}
    for k, (lo, hi) in SPACE.items():
        x = min(max(float(recipe[k]), lo), hi)
        out[k] = int(round(x)) if isinstance(lo, int) else round(x, 2)
    return out


def random_recipe(rng):
    r = {k: rng.uniform(lo, hi) for k, (lo, hi) in SPACE.items()}
    r["mode"] = str(rng.choice(list(FEEDBACK_MODES)))
    return clean(r)


def mutate(parent, rng):
    child = dict(parent)
    for k, (lo, hi) in SPACE.items():
        if rng.random() < 0.4:
            child[k] = parent[k] + rng.normal(0, 0.15 * (hi - lo))
    if rng.random() < 0.15:
        child["mode"] = str(rng.choice(list(FEEDBACK_MODES)))
    return clean(child)


def ask_llm(rows):
    lines = [f"- n°{r['id']} : {r['params']} -> {r['learning'] * 100:+.0f} points" for r in rows[:12]]
    prompt = (
        f"Tu diriges un labo qui essaie d'apprendre Pong a une culture de {CULTURE_SIZE} neurones simules "
        "(comme l'experience DishBrain). Voici les meilleures recettes deja testees, avec le gain "
        "de balles renvoyees entre le debut et la fin de la partie :\n" + "\n".join(lines) +
        f"\nBornes des parametres : {json.dumps(SPACE)}. Modes : {json.dumps(FEEDBACK_MODES, ensure_ascii=False)}."
        "\nPropose UNE nouvelle recette, differente des precedentes, et resume en une phrase en "
        "francais l'hypothese qu'elle teste.")
    out = llm.ask(prompt, schema=LLM_SCHEMA)
    return clean(out["recette"]), f"proposée par l'IA : {out['hypothese']}"


def propose(con, rng):
    rows = con.execute("SELECT id, params, learning FROM recipes WHERE learning IS NOT NULL AND neurons=?"
                       " ORDER BY learning DESC", (CULTURE_SIZE,)).fetchall()
    if not rows:
        return dict(DISHBRAIN), "protocole DishBrain"
    if len(rows) % 5 == 4 and llm.available():
        try:
            return ask_llm(rows)
        except (requests.RequestException, ValueError, KeyError, TypeError) as e:
            log.warning("proposition de l'IA inutilisable : %s", e)
    if len(rows) < 8 or rng.random() < 0.2:
        return random_recipe(rng), "tirée au hasard"
    i, j = rng.choice(min(8, len(rows)), 2, replace=False)
    parent = rows[min(i, j)]
    return mutate(json.loads(parent["params"]), rng), f"variante de la n°{parent['id']}"


def mean_learning(results):
    return float(np.mean([r["late"] - r["early"] for r in results]))


def evaluate(con, recipe, origin):
    rid = con.execute("INSERT INTO recipes(params, origin, created_at, neurons) VALUES (?,?,?,?)",
                      (json.dumps(recipe), origin, time.time(), CULTURE_SIZE)).lastrowid
    con.commit()
    results = [r for r in (play(con, rid, recipe, s, True) for s in SEARCH_SEEDS) if r]
    if not results:
        db.journal(con, log, f"Recette n°{rid} abandonnée : sessions interrompues.")
        return rid
    early = float(np.mean([r["early"] for r in results]))
    late = float(np.mean([r["late"] for r in results]))
    hits = sum(r["hits"] for r in results)
    total = hits + sum(r["misses"] for r in results)
    best = con.execute("SELECT MAX(learning) FROM recipes WHERE neurons=?", (CULTURE_SIZE,)).fetchone()[0]
    con.execute("UPDATE recipes SET early=?, late=?, learning=?, hit_rate=? WHERE id=?",
                (early, late, late - early, hits / total if total else 0.0, rid))
    con.commit()
    msg = (f"Recette n°{rid} ({origin} ; {describe(recipe)}) : {early:.0%} de balles renvoyées "
           f"au début, {late:.0%} à la fin ({(late - early) * 100:+.0f} points).")
    if best is None or late - early > best:
        msg += " Meilleure recette jusqu'ici."
    db.journal(con, log, msg)
    return rid


def confirm_best(con):
    """Rejoue la meilleure recette sur des cultures neuves, avec et sans plasticite."""
    row = con.execute("SELECT * FROM recipes WHERE learning IS NOT NULL AND control IS NULL AND neurons=?"
                      " ORDER BY learning DESC LIMIT 1", (CULTURE_SIZE,)).fetchone()
    if row is None or row["learning"] < MIN_EFFECT:
        return
    recipe = json.loads(row["params"])
    seeds = [100 + 3 * row["id"] + k for k in range(3)]  # cultures jamais vues
    plastic = [r for r in (play(con, row["id"], recipe, s, True, "Vérification") for s in seeds) if r]
    frozen = [r for r in (play(con, row["id"], recipe, s, False, "Vérification") for s in seeds) if r]
    if not plastic or not frozen:
        return
    lp, lf = mean_learning(plastic), mean_learning(frozen)
    con.execute("UPDATE recipes SET confirmed=?, control=? WHERE id=?", (lp, lf, row["id"]))
    con.commit()
    if lp >= MIN_EFFECT and lp - lf >= MIN_EFFECT:
        verdict = "l'apprentissage se confirme, et il vient bien des synapses"
    elif lp >= MIN_EFFECT:
        verdict = "les cultures figées progressent autant : ce n'est pas un apprentissage synaptique"
    else:
        verdict = "l'effet ne se reproduit pas sur des cultures neuves (sans doute du hasard)"
    db.journal(con, log, f"Contre-épreuve de la recette n°{row['id']} sur 3 cultures neuves : "
                         f"{lp * 100:+.0f} points avec plasticité, {lf * 100:+.0f} sans → {verdict}.")


def main():
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    con = db.connect(NEURO_DB)
    con.executescript(SCHEMA)
    if "neurons" not in {c[1] for c in con.execute("PRAGMA table_info(recipes)")}:
        # Les recettes d'avant la taille reglable ont toutes ete jouees sur 1 000 neurones.
        con.execute("ALTER TABLE recipes ADD COLUMN neurons INTEGER DEFAULT 1000")
        con.commit()
    rng = np.random.default_rng()
    db.journal(con, log, f"Labo de neurones démarré ({CULTURE_SIZE:,} neurones par culture).".replace(",", " "))
    while True:
        recipe, origin = propose(con, rng)
        if evaluate(con, recipe, origin) % CONFIRM_EVERY == 0:
            confirm_best(con)


if __name__ == "__main__":
    import sys

    if sys.argv[1:] == ["--essai"]:
        # Partie courte pour verifier l'installation, sans rien ecrire en base.
        WARMUP_S, GAME_MIN, WINDOW_MIN = 10, 2, 1
        logging.basicConfig(level=logging.INFO)
        print(run_session(DISHBRAIN, seed=1, plastic=True))
    else:
        main()
