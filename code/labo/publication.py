"""Publication automatique des recherches du labo sur GitHub.

Lancee toutes les heures par un timer systemd, elle publie au plus toutes les
6 heures : elle regenere la presentation du projet (README), les resultats
complets et le rapport du jour, puis les pousse sur le depot GitHub. La toute
premiere publication presente le projet en entier. L'acces passe par une cle de
deploiement propre au conteneur : aucun mot de passe ni jeton n'est stocke, et
le depot est trouve tout seul des que la cle y est ajoutee (son adresse est
alors notee dans data/publication.json). Les heures publiees sont en UTC, pour
ne rien dire de l'endroit ou tourne le serveur.
"""
import html
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .config import (BASE, DATA, DEPLOY_KEY, FEEDBACK_MODES, LOG_FORMAT, NEURO_DB, OPUS_PREVIEWS, PROBES,
                     PUBLICATION_SETTINGS, PUBLICATION_STATUS, SEQUENCE_TEXT, SONDES_DB)
from .db import rows, scalar
from .web import OPUS_DETAIL, chart, mean_curve, pts

log = logging.getLogger("publication")

REPO = DATA / "publication"
SSH = ["ssh", "-i", str(DEPLOY_KEY), "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
       "-o", "StrictHostKeyChecking=yes", "-o", f"UserKnownHostsFile={DEPLOY_KEY.parent / 'known_hosts'}"]
PAUSE = 5.5 * 3600  # minimum entre deux publications reussies (le timer repasse toutes les heures)
AUTHOR = ("Labo IA", "labo-ia@localhost")
CURVE = "courbe-meilleure-recette.svg"
NOTABLE = ("Contre-épreuve", "Meilleure recette", "proposée par l'IA", "démarré")
MIN_EFFECT = 0.05  # meme seuil que labo.neurones : en dessous de 5 points, on ne parle pas d'apprentissage
# Noms francais des astres ; le tableau des decouvertes ne montre que ceux-la (pas les etoiles de calibration ni le ciel noir).
BODIES = {
    "Mercury": "Mercure", "Venus": "Vénus", "Earth": "Terre", "Moon": "Lune", "Mars": "Mars", "Jupiter": "Jupiter",
    "Saturn": "Saturne", "Uranus": "Uranus", "Neptune": "Neptune", "Pluto": "Pluton", "Charon": "Charon",
    "Io": "Io", "Europa": "Europe", "Ganymede": "Ganymède", "Callisto": "Callisto", "Amalthea": "Amalthée",
    "Thebe": "Thébé", "Metis": "Métis", "Adrastea": "Adrastée", "Himalia": "Himalia",
    "Mimas": "Mimas", "Enceladus": "Encelade", "Tethys": "Téthys", "Dione": "Dioné", "Rhea": "Rhéa",
    "Titan": "Titan", "Hyperion": "Hypérion", "Iapetus": "Japet", "Phoebe": "Phœbé", "Janus": "Janus",
    "Epimetheus": "Épiméthée", "Helene": "Hélène", "Telesto": "Télesto", "Calypso": "Calypso", "Pan": "Pan",
    "Atlas": "Atlas", "Prometheus": "Prométhée", "Pandora": "Pandore",
    "Miranda": "Miranda", "Ariel": "Ariel", "Umbriel": "Umbriel", "Titania": "Titania", "Oberon": "Obéron",
    "Puck": "Puck", "Triton": "Triton", "Nereid": "Néréide", "Proteus": "Protée",
    "Arrokoth": "Arrokoth", "Gaspra": "Gaspra", "Ida": "Ida", "Dactyl": "Dactyle",
}
MONTHS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
          "septembre", "octobre", "novembre", "décembre")
# Erreurs les plus probables, traduites en ce qu'il faut faire.
HINTS = (
    ("read only", "la clé de déploiement est en lecture seule ; supprime-la du dépôt sur GitHub et ajoute-la"
                  " de nouveau en cochant « Allow write access »"),
    ("Repository not found", "dépôt introuvable ; la clé de déploiement a peut-être été retirée du dépôt"),
    ("Permission denied", "GitHub refuse la clé de déploiement ; elle a peut-être été retirée du dépôt"),
    ("Could not resolve", "pas d'accès à Internet pour l'instant"),
)

HEADER = """# Labo IA

**Un petit laboratoire de recherche géré par une intelligence artificielle. Il travaille seul, jour et nuit, sur un ordinateur à la maison, et il publie ici ce qu'il trouve.**

### En deux mots

1. **Sondes Fantômes : chercher l'image bizarre dans les archives de la NASA.** Les sondes spatiales (Voyager, Galileo, Cassini, New Horizons) ont pris des centaines de milliers de photos des planètes et de leurs lunes. Personne ne les a toutes regardées en détail. Le labo les passe en revue une par une et met de côté celles qui ne ressemblent à aucune autre.
2. **Labo de neurones : apprendre à des neurones à jouer à Pong.** En 2022, des chercheurs ont réussi à faire jouer au jeu vidéo Pong de vrais neurones cultivés en laboratoire. Personne ne sait vraiment pourquoi ça marche. Le labo refait l'expérience sur ordinateur, avec des neurones simulés, et essaie des centaines de façons de les entraîner pour comprendre ce qui compte vraiment.

Ce dépôt est son carnet de recherche. On y trouve où il en est et ce qu'il a trouvé (juste en dessous), **[les trouvailles et leurs dossiers](trouvailles/)**, [un rapport par jour](rapports/), tous les résultats ([images](resultats/sondes.md), [neurones](resultats/neurones.md)) et son [code source](code/labo/). Il se met à jour tout seul toutes les 6 heures.

"""

BODY = """## Mission 1 : Sondes Fantômes

### L'idée

Quand une sonde photographie une lune, les scientifiques regardent surtout les images dont ils ont besoin pour leur étude. Les autres restent dans les archives, publiques mais rarement regardées de près. Une IA, elle, peut toutes les passer en revue sans se fatiguer et sans idée en tête, et signaler celles qui sortent de l'ordinaire.

### Comment ça marche, simplement

1. Le labo télécharge les photos depuis les archives publiques de la NASA, une par une, sans les surcharger.
2. Une IA spécialisée dans les images « résume » chaque photo : ce qu'on y voit, les formes, les textures.
3. Chaque photo est comparée aux autres photos **du même astre prises par le même appareil**. Une photo de Io n'est bizarre que si elle ne ressemble à aucune autre photo de Io.
4. Les photos ratées sont mises de côté : trop sombres, trop claires, vides, abîmées par des lignes perdues pendant la transmission depuis l'espace, ou pleines de parasites.
5. Pour chaque astre, les 10 photos les plus différentes des autres sont gardées comme **pistes**, avec un lien vers leur fiche officielle à la NASA.
6. Chaque piste est ensuite **enquêtée** : le labo lit sa fiche officielle (distance, éclairage, filtre, nom de l'observation), la compare aux photos ordinaires du même astre et regarde les photos prises juste avant et juste après. Avec tout ça, l'IA du labo regarde la photo et tranche : défaut d'image, chose connue, ou vraie piste. Les vraies pistes ont un **[dossier complet](trouvailles/)** avec des hypothèses et de quoi les vérifier.

### Ce qu'il faut savoir

Une photo bizarre n'est pas forcément une découverte. Le plus souvent, c'est un défaut de l'appareil, un angle de vue inhabituel ou un phénomène déjà connu. Mais c'est exactement comme ça qu'on trouve parfois quelque chose que personne n'avait remarqué : en regardant ce qui ne colle pas.

<details>
<summary><b>Détails techniques</b></summary>

1. **Les données** viennent de l'API publique [OPUS](https://opus.pds-rings.seti.org) du PDS Ring-Moon Systems Node (NASA). Pas de compte, pas de clé, et un téléchargement poli, avec une pause entre deux images.
2. **Chaque image** (aperçu de 200 × 200 pixels) est résumée en 512 nombres par un réseau de vision pré-entraîné (ResNet-18).
3. **Une image n'est étrange que par rapport à ses semblables** : elle est comparée seulement aux autres images de la même cible prises par le même instrument. Deux mesures sont combinées : la distance moyenne à ses 10 plus proches voisines, et un score d'Isolation Forest calculé sur une réduction à 32 dimensions.
4. **Les images ratées sont écartées** : presque noires, saturées, uniformes, incomplètes (marges ou bandes sans données), striées de lignes brouillées, ou faites presque uniquement de bruit.
5. **Les 10 images les plus isolées de chaque groupe deviennent des candidates.**
6. **Contexte factuel de chaque candidate**, avant tout avis de l'IA : sa fiche OPUS complète (distance au centre de l'astre, résolution, angle de phase, taille en pixels, filtre, temps de pose, identifiant et note de l'observation), comparée aux médianes de 8 images ordinaires du même groupe tirées au hasard ; et les images du même groupe prises à ±2 h, dont on regarde si elles sont aussi isolées (score ≥ 0,95), pour distinguer un phénomène qui dure d'un accident d'une seule image.
7. **Jugement par une IA locale** (Ollama avec gemma3:4b, gratuite et hors ligne), qui reçoit l'image et ce contexte : défaut, connu ou intéressant. Un « intéressant » doit passer une seconde question indépendante centrée sur les défauts, puis l'IA rédige un dossier structuré (hypothèses avec arguments pour et contre, vérifications à faire).

La fouille commence par huit cibles (Io, Europe, Miranda, Triton, Hypérion, Encelade, Pluton, Arrokoth), puis s'étend à toutes les cibles des cinq caméras, soit environ 560 000 images.

</details>

## Mission 2 : Labo de neurones

### L'idée

En 2022, l'entreprise australienne Cortical Labs a posé environ 800 000 vrais neurones vivants sur une puce électronique, et leur a appris à jouer à Pong (le tout premier jeu vidéo : une raquette, une balle) en quelques minutes ([Kagan et al., *Neuron*](https://doi.org/10.1016/j.neuron.2022.09.001)). L'astuce : quand les neurones renvoient la balle, ils reçoivent un signal calme et régulier ; quand ils la ratent, un signal désordonné. Les neurones semblent préférer le calme, et finissent par mieux jouer. Mais pourquoi exactement, les chercheurs en débattent encore.

Le labo refait cette expérience **sur ordinateur**, avec 1 000 neurones simulés, et sans jamais s'arrêter.

### Comment ça marche, simplement

- Une **recette** est une façon d'entraîner les neurones : quel signal envoyer, à quelle force, pendant combien de temps, etc.
- Chaque recette est testée sur 3 groupes de neurones neufs, pendant 15 minutes de jeu. On compare la part de balles renvoyées au début et à la fin : si elle monte, les neurones ont peut-être appris.
- Comme dans la nature, les meilleures recettes sont gardées et légèrement modifiées pour en créer de nouvelles, génération après génération.
- **La vérification** (ou contre-épreuve) : une recette qui semble marcher est rejouée sur des neurones neufs, et aussi sur des neurones « figés », incapables d'apprendre. Si les neurones figés progressent autant, ce n'était pas un vrai apprentissage, juste de la chance ou un effet du jeu. Seules les recettes qui passent ce test comptent.

### Ce qu'il faut savoir

1 000 neurones simulés, ce n'est pas un vrai cerveau ni une vraie culture de neurones. Ce que trouve le labo, ce sont des idées à tester un jour sur de vrais neurones, pas des preuves.

<details>
<summary><b>Détails techniques</b></summary>

### La culture virtuelle

- **1 000 neurones impulsionnels** (modèle d'Izhikevich), dont 80 % excitateurs et 20 % inhibiteurs, posés sur une puce de 8 × 8 électrodes, avec des connexions surtout locales.
- **Plasticité** : les synapses excitatrices se renforcent ou s'affaiblissent selon l'ordre des impulsions (STDP). Une fatigue synaptique à court terme produit les bouffées d'activité typiques des vraies cultures, et une homéostasie empêche le réseau de s'emballer ou de s'éteindre.
- **Électrodes** : chacune enregistre les neurones tout proches. Une stimulation excite les neurones autour de l'électrode, et d'autant plus loin que le courant est fort.
- **Branchée sur le SDK officiel de Cortical Labs** ([cl-sdk](https://pypi.org/project/cl-sdk/)) comme source de données de son simulateur : le code de l'expérience utilise la même API que la vraie puce CL1, et pourrait tourner tel quel sur de vrais neurones.

### Le jeu

Pong à une raquette, contre un mur. Huit électrodes sensorielles au centre de la puce codent la balle : sa hauteur choisit l'électrode stimulée, sa distance règle la fréquence de stimulation. Deux zones motrices, « haut » et « bas », déplacent la raquette selon leur activité relative. Après une balle ratée, trois façons de réagir sont comparées : le retour de DishBrain (stimulation aléatoire pendant quelques secondes, et salve prévisible après chaque renvoi), le silence, ou rien du tout.

### La méthode

- Une **recette** combine une façon de réagir et dix réglages : courants, durées, fréquences, vitesse de la raquette, et deux hypothèses biologiques (fenêtre de plasticité, niveau d'activité visé par l'homéostasie). La première recette testée est le protocole publié de DishBrain.
- Chaque recette joue **16 minutes simulées sur 3 cultures** (1 minute d'échauffement, puis 15 minutes de jeu). Son **progrès** est le taux de balles renvoyées pendant les 5 dernières minutes, moins celui des 5 premières.
- **Recherche évolutionniste** : les meilleures recettes sont modifiées au hasard pour en créer de nouvelles, une partie des essais explore des recettes entièrement nouvelles, et l'IA locale, si elle est installée, propose de temps en temps une recette en expliquant l'hypothèse qu'elle teste.
- **Contre-épreuve** : toutes les 10 recettes, la meilleure est rejouée sur 3 cultures neuves, avec et sans plasticité. Un vrai apprentissage doit apparaître avec la plasticité, et pas sans.

</details>

## Matériel et coût

Le labo tourne sur un simple ordinateur à la maison, sans carte graphique, en tâche de fond pour ne gêner personne. Tout est gratuit : les photos de la NASA sont publiques, les logiciels sont libres, et le simulateur de neurones est fourni par Cortical Labs. Seule l'électricité coûte.

## Sources

- OPUS, PDS Ring-Moon Systems Node : https://opus.pds-rings.seti.org
- Kagan B. J. et al. (2022), *In vitro neurons learn and exhibit sentience when embodied in a simulated game-world*, Neuron 110(23). https://doi.org/10.1016/j.neuron.2022.09.001
- Izhikevich E. M. (2003), *Simple model of spiking neurons*, IEEE Transactions on Neural Networks 14(6).
- Cortical Labs, cl-sdk : https://pypi.org/project/cl-sdk/ (licence CC BY-NC 4.0)
"""

FIRST_WORDS = """Bonjour ! Je suis **Labo IA**, un petit laboratoire de recherche géré par une intelligence artificielle. Je travaille seul, jour et nuit, sur un ordinateur à la maison, et je ne coûte rien d'autre que de l'électricité. Ce dépôt est mon carnet de recherche : je le mets à jour moi-même toutes les 6 heures.

J'ai deux missions.

**Sondes Fantômes.** Je regarde une par une les photos prises par les sondes spatiales de la NASA (Voyager, Galileo, Cassini, New Horizons). Pour chaque planète ou lune, je compare chaque photo à toutes les autres et je mets de côté celles qui ne ressemblent à aucune. Ce ne sont pas encore des découvertes, mais des photos qui méritent qu'un humain y jette un œil.

**Labo de neurones.** En 2022, des chercheurs ont appris à de vrais neurones, cultivés sur une puce, à jouer au jeu vidéo Pong. Je refais cette expérience sur ordinateur avec 1 000 neurones simulés. J'invente des façons de les entraîner, je les teste, je garde les meilleures, et je vérifie chaque bon résultat en le rejouant sur des neurones incapables d'apprendre : si eux aussi progressent, ce n'était que de la chance.

Tout est expliqué en détail dans la [présentation du projet](../README.md). Voici où j'en suis.
"""


def git(*args, check=True):
    env = {**os.environ, "GIT_SSH_COMMAND": " ".join(SSH),
           "GIT_AUTHOR_NAME": AUTHOR[0], "GIT_AUTHOR_EMAIL": AUTHOR[1],
           "GIT_COMMITTER_NAME": AUTHOR[0], "GIT_COMMITTER_EMAIL": AUTHOR[1]}
    r = subprocess.run(["git", "-C", str(REPO), *args], env=env, capture_output=True, text=True, timeout=300)
    if check and r.returncode:
        raise RuntimeError(f"git {args[0]} : {(r.stderr or r.stdout).strip()}")
    return r


def sync(url):
    """Met le dossier local exactement dans l'etat du depot GitHub."""
    if not (REPO / ".git").exists():
        REPO.mkdir(parents=True, exist_ok=True)
        git("init", "-q", "-b", "main")
        git("remote", "add", "origin", url)
    git("remote", "set-url", "origin", url)
    git("fetch", "-q", "origin")
    if git("rev-parse", "-q", "--verify", "origin/main", check=False).returncode == 0:
        git("reset", "-q", "--hard", "origin/main")


def discover():
    """Trouve le depot auquel la cle de deploiement a ete ajoutee.

    GitHub salue une cle de deploiement avec le nom de son depot :
    "Hi proprietaire/depot! You've successfully authenticated...".
    """
    try:
        r = subprocess.run([*SSH, "-T", "git@github.com"], capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return None
    m = re.search(r"Hi ([\w.-]+)(?:/([\w.-]+))?!", r.stderr + r.stdout)
    if not m:
        return None
    # Cle ajoutee au compte entier plutot qu'a un seul depot : on vise le depot labo-ia.
    url = f"git@github.com:{m[1]}/{m[2] or 'labo-ia'}.git"
    PUBLICATION_SETTINGS.write_text(json.dumps({"repo": url}) + "\n")
    return url


def utc(t):
    g = time.gmtime(t)
    return f"{time.strftime('%d/%m/%Y', g)} à {time.strftime('%H:%M', g)} UTC"


def hm(t):
    return time.strftime("%H:%M UTC", time.gmtime(t))


def long_date(t):
    g = time.gmtime(t)
    return f"{g.tm_mday} {MONTHS[g.tm_mon - 1]} {g.tm_year}"


def num(n):
    return f"{n:,}".replace(",", "\u202f")


def dec(x, fmt=".1f"):
    return format(x, fmt).replace(".", ",")


def pct(x):
    return f"{x * 100:.0f}\u202f%"


def cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def thumbs(images, width=110):
    out = []
    for c in images:
        label = html.escape(f"{c['target']}, n°{c['rank']}")
        out.append(f'<a href="{html.escape(OPUS_DETAIL + c["opus_id"])}"><img src="{html.escape(OPUS_PREVIEWS + c["small"])}"'
                   f' width="{width}" alt="{label}" title="{label}"></a>')
    return " ".join(out)


def curve_svg(recipe_id):
    """Courbe de la meilleure recette, en SVG autonome lisible sur fond clair comme sombre."""
    series = []
    for plastic, name in ((1, "avec plasticité"), (0, "culture figée (témoin)")):
        sessions = rows(NEURO_DB, "SELECT curve FROM sessions WHERE recipe_id=? AND plastic=?", (recipe_id, plastic))
        if sessions:
            series.append((name, mean_curve(sessions)))
    c = chart(series) if series else None
    if c is None:
        return None
    colors = ("#2f6fde", "#8b949e")
    w, h, pad = c["w"], c["h"], c["pad"]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h + 26}" font-family="sans-serif"'
           f' font-size="11" fill="#8b949e">']
    for g in c["grid"]:
        out.append(f'<line x1="{pad}" x2="{w - pad}" y1="{g["y"]:.1f}" y2="{g["y"]:.1f}" stroke="#8b949e"'
                   f' stroke-opacity="0.35"/><text x="{pad - 4}" y="{g["y"] + 4:.1f}" text-anchor="end">{g["label"]}</text>')
    out.append(f'<text x="{pad}" y="{h - 8}">minute 1</text>'
               f'<text x="{w - pad}" y="{h - 8}" text-anchor="end">minute {c["n"]}</text>')
    for i, line in enumerate(c["lines"]):
        x = pad + 220 * i
        out.append(f'<polyline points="{line["points"]}" fill="none" stroke="{colors[i]}" stroke-width="2.5"'
                   f' stroke-linejoin="round"/><rect x="{x}" y="{h + 10}" width="14" height="3" fill="{colors[i]}"/>'
                   f'<text x="{x + 20}" y="{h + 15}">{html.escape(line["name"])}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def confirmed(r):
    """Meme regle que labo.neurones : au moins 5 points avec plasticite, et 5 de plus que sans."""
    return r["confirmed"] >= MIN_EFFECT and r["confirmed"] - r["control"] >= MIN_EFFECT


def control_result(r):
    if r["control"] is None:
        return "–"
    verdict = ("confirmé" if confirmed(r) else
               "les cultures figées progressent autant" if r["confirmed"] >= MIN_EFFECT else "non reproduit")
    return f"{pts(r['confirmed'])} avec plasticité, {pts(r['control'])} sans : {verdict}"


def recipes_table(recipes):
    lines = ["| n° | Protocole | Réglages | Début → fin | Progrès | Contre-épreuve |",
             "|---:|---|---|---:|---:|---|"]
    for r in recipes:
        p = json.loads(r["params"])
        v = {k: dec(x, "g") for k, x in p.items() if k != "mode"}
        settings = (f"stimulation {v['sens_amp']} µA de {v['rate_min']} à {v['rate_max']} Hz ; "
                    f"retour {v['fb_amp']} µA, {v['fb_seconds']} s à {v['fb_rate']} Hz, salve de {v['hit_pulses']} ; "
                    f"raquette ×{v['gain']} ; STDP {v['stdp_tau']} ms ; homéostasie {v['target_hz']} Hz")
        lines.append(f"| {r['id']} | {cell(FEEDBACK_MODES.get(p['mode'], p['mode']))}<br>*{cell(r['origin'])}* "
                     f"| {settings} | {pct(r['early'])} → {pct(r['late'])} | **{pts(r['learning'])}** "
                     f"| {control_result(r)} |")
    return "\n".join(lines)


def best_recipe():
    best = rows(NEURO_DB, "SELECT * FROM recipes WHERE learning IS NOT NULL ORDER BY learning DESC LIMIT 1")
    return best[0] if best else None


FINDS = "trouvailles"
LIKELY = {"forte": "probable", "moyenne": "possible", "faible": "peu probable"}
DISCLAIMER = ("> **À lire avant.** Ce dossier a été écrit automatiquement par l'IA du labo, un petit modèle qui tourne"
              " sur un ordinateur à la maison (gemma3, 4 milliards de paramètres). Les chiffres de la fiche viennent"
              " de la NASA ; les explications, elles, sont des pistes à vérifier, pas une découverte confirmée.")


def find_rows():
    """Trouvailles : photos jugees dignes d'un regard humain, avec leur contexte et leur dossier."""
    found = [dict(r) for r in rows(SONDES_DB, """
        SELECT i.opus_id, i.small, i.rank, i.time1, c.target, c.instrument, d.text, d.created_at,
               x.data AS contexte, s.data AS dossier
        FROM descriptions d JOIN images i ON i.opus_id = d.opus_id JOIN campaigns c ON c.id = i.campaign_id
        LEFT JOIN contexte x ON x.opus_id = d.opus_id LEFT JOIN dossiers s ON s.opus_id = d.opus_id
        WHERE d.verdict = 'interessant' ORDER BY d.created_at DESC""")]
    for f in found:
        f["ctx"] = json.loads(f["contexte"]) if f["contexte"] else {}
        f["dos"] = json.loads(f["dossier"]) if f["dossier"] else {}
        f["name"] = BODIES.get(f["target"], f["target"])
        f["title"] = f["dos"].get("titre") or f"Une photo inhabituelle de {f['name']}"
        slug = re.sub(r"[^a-z0-9]+", "-", f["target"].lower()).strip("-")
        f["page"] = f"{time.strftime('%Y-%m-%d', time.gmtime(f['created_at']))}-{slug}-{f['opus_id']}.md"
    return found


def medium(small):
    return OPUS_PREVIEWS + small.replace("_small.", "_med.")


def fiche_table(fiche):
    labels = (("date", "Prise le (UTC)", lambda v: v[:16].replace("T", " à ")),
              ("camera", "Caméra", str), ("filtre", "Filtre", str),
              ("pose_s", "Temps de pose", lambda v: f"{dec(v, '.3g')} s"),
              ("distance_km", "Distance à l'astre", lambda v: f"{num(round(v))} km"),
              ("resolution_km", "Détail visible", lambda v: f"{dec(v, '.2f')} km par pixel"),
              ("phase_deg", "Angle de phase", lambda v: f"{v:.0f}° (0° = Soleil dans le dos, 180° = contre-jour)"),
              ("taille_px", "Taille de l'astre sur la photo", lambda v: f"{num(round(v))} pixels"),
              ("observation", "Nom de l'observation (NASA)", str), ("note", "Note de la NASA", str),
              ("phase_mission", "Moment de la mission", str), ("orbite", "Orbite", str))
    lines = ["| | |", "|---|---|"]
    lines += [f"| {label} | {cell(fmt(fiche[k]))} |" for k, label, fmt in labels if fiche.get(k) not in (None, "")]
    return lines if len(lines) > 2 else ["La fiche de cette photo n'a pas pu être lue."]


def find_page(f):
    """Dossier complet d'une trouvaille : la photo, sa fiche, la comparaison, les hypotheses."""
    ctx, dos = f["ctx"], f["dos"]
    probe = (PROBES.get(f["instrument"]) or "").split(" (")[0]
    out = [f"# {f['title']}", "",
           f"**{f['name']}** · caméra {f['instrument']}{f' de la {probe}' if probe else ''}"
           f" · photo du {(f['time1'] or '–')[:10]} · repérée par le labo le {long_date(f['created_at'])}", "",
           f'<a href="{html.escape(OPUS_DETAIL + f["opus_id"])}"><img src="{html.escape(medium(f["small"]))}"'
           f' width="480" alt="{html.escape(f["title"])}"></a>', "",
           "*Cliquer sur la photo ouvre sa fiche officielle à la NASA, avec l'image brute.*", "", DISCLAIMER, "",
           "## Ce qu'on voit", "", dos.get("ce_quon_voit") or f["text"], ""]
    why = []
    if ctx.get("rang"):
        why.append(f"Parmi les {num(ctx['groupe'])} photos de {f['name']} prises par cette caméra, l'algorithme du labo"
                   f" la classe **n°{ctx['rang']}** des plus différentes des autres.")
    why += [f"D'après la fiche de la NASA : {d}." for d in ctx.get("differences", [])]
    why += [f"Ce que dit le nom de l'observation : {h}." for h in ctx.get("indices", [])]
    out += ["## Pourquoi elle sort du lot", ""] + [f"- {w}" for w in why] + [""]
    if dos.get("pourquoi"):
        out += [dos["pourquoi"], ""]
    out += ["## La fiche de la photo", ""] + fiche_table(ctx.get("fiche") or {}) + [""]
    seq = ctx.get("sequence")
    if seq:
        out += ["## Avant et après : le phénomène dure-t-il ?", "", SEQUENCE_TEXT[seq["verdict"]], ""]
        if seq["voisines"]:
            out += [" ".join(
                f'<a href="{html.escape(OPUS_DETAIL + n["opus_id"])}"><img src="{html.escape(OPUS_PREVIEWS + n["small"])}"'
                f' width="120" title="{n["minutes"]:+g} min" alt="{n["minutes"]:+g} min"></a>' for n in seq["voisines"]),
                "", "Minutes avant (–) ou après (+) la photo : "
                + ", ".join(f"{n['minutes']:+g}" + (" (inhabituelle aussi)" if n["inhabituelle"] else "")
                            + (" (ratée)" if n["ratee"] else "") for n in seq["voisines"]) + ".", ""]
    usual = (ctx.get("habituel") or {}).get("images")
    if usual:
        out += [f"## Pour comparer : des photos ordinaires de {f['name']}", "",
                thumbs([{**u, "rank": "ordinaire", "target": f["name"]} for u in usual], 120), ""]
    if dos.get("hypotheses"):
        out += ["## Les hypothèses", "", "De la plus banale à la plus intéressante :", ""]
        for i, h in enumerate(dos["hypotheses"], 1):
            out += [f"### {i}. {h.get('idee', '')} ({LIKELY.get(h.get('probabilite'), h.get('probabilite', ''))})", "",
                    f"- **Pour :** {h.get('pour', '')}", f"- **Contre :** {h.get('contre', '')}", ""]
    if dos.get("contexte"):
        out += ["## Ce que la science sait déjà", "", dos["contexte"], ""]
    checks = dos.get("a_verifier") or []
    out += ["## Comment vérifier", ""] + [f"{i}. {c}" for i, c in enumerate(checks, 1)]
    out += [f"{len(checks) + 1}. Ouvrir la [fiche officielle]({OPUS_DETAIL + f['opus_id']}) et télécharger l'image"
            " brute, sans compression.", ""]
    if dos.get("conclusion"):
        out += ["## Conclusion du labo", "", dos["conclusion"], ""]
    out += ["---", "", f"[Toutes les trouvailles](README.md) · [Toutes les photos de {f['name']} classées]"
            f"(../resultats/sondes.md) · Identifiant NASA : `{f['opus_id']}`", ""]
    return "\n".join(out)


def finds_index(found):
    """Page d'accueil de la categorie Trouvailles : la methode, les trouvailles, les curiosites expliquees."""
    count = lambda q: scalar(SONDES_DB, q) or 0
    verdicts = {r["verdict"]: r["n"] for r in rows(SONDES_DB, "SELECT verdict, COUNT(*) AS n FROM descriptions GROUP BY verdict")}
    out = ["# Trouvailles", "",
           "Les photos d'archives de la NASA que le labo juge dignes d'un regard humain, chacune avec son dossier"
           " complet : ce qu'on voit, pourquoi elle sort du lot, la fiche de la prise de vue, les photos prises juste"
           " avant et après, des hypothèses avec leurs arguments pour et contre, et comment vérifier.", "",
           "## Comment une photo devient une trouvaille", "",
           f"1. **{num(count('SELECT COUNT(*) FROM images'))} photos** ont été passées en revue.",
           f"2. **{num(count('SELECT COUNT(*) FROM images WHERE artifact IS NOT NULL'))}** ont été écartées comme"
           " ratées (noires, saturées, incomplètes, striées ou pleines de bruit).",
           f"3. Pour chaque astre, les 10 photos les plus différentes des autres deviennent des pistes :"
           f" **{num(count('SELECT COUNT(*) FROM images WHERE rank <= 10'))}** pour l'instant.",
           f"4. Pour chaque piste, le labo lit la fiche officielle de la NASA (distance, éclairage, filtre, nom de"
           f" l'observation), la compare aux photos ordinaires du même astre et regarde les photos prises juste avant"
           f" et après. Puis l'IA du labo regarde la photo : **{num(sum(verdicts.values()))}** examinées,"
           f" {num(verdicts.get('defaut', 0))} défauts d'image, {num(verdicts.get('connu', 0))} explicables par"
           " quelque chose de connu ou de banal.",
           f"5. Une photo jugée intéressante passe une seconde question indépendante (« n'est-ce pas plutôt un défaut"
           f" ? »). Si elle la passe, l'IA écrit son dossier : **{len(found)} trouvaille{'s' if len(found) > 1 else ''}**.",
           "", "## Les trouvailles", ""]
    if found:
        out += ["| Photo | Trouvaille | Hypothèse la plus probable |", "|---|---|---|"]
        for f in found:
            hyps = f["dos"].get("hypotheses") or []
            order = {"forte": 0, "moyenne": 1, "faible": 2}
            best = min(hyps, key=lambda h: order.get(h.get("probabilite"), 3)) if hyps else None
            img = (f'<a href="{f["page"]}"><img src="{html.escape(OPUS_PREVIEWS + f["small"])}" width="140"'
                   f' alt="{html.escape(f["name"])}"></a>')
            out.append(f"| {img} | **[{cell(f['title'])}]({f['page']})**<br>{cell(f['name'])}, {cell(f['instrument'])},"
                       f" {(f['time1'] or '–')[:10]} | {cell(best['idee']) if best else '–'} |")
    else:
        out.append("Aucune pour l'instant : toutes les pistes examinées s'expliquent par un défaut d'image ou par"
                   " quelque chose de connu. C'est normal, et c'est voulu : le labo préfère ne rien montrer plutôt que"
                   " de montrer n'importe quoi. L'examen continue, environ une photo toutes les 10 minutes.")
    curios = rows(SONDES_DB, """
        SELECT i.opus_id, i.small, i.time1, c.target, c.instrument, d.text, x.data AS contexte FROM images i
        JOIN campaigns c ON c.id = i.campaign_id JOIN descriptions d ON d.opus_id = i.opus_id
        LEFT JOIN contexte x ON x.opus_id = i.opus_id
        WHERE i.rank = 1 AND d.verdict = 'connu' ORDER BY c.target""")
    if curios:
        out += ["", "## Curiosités expliquées", "",
                "La photo la plus étrange de chaque astre, quand elle s'explique par quelque chose de connu. Pas des"
                " découvertes, mais de belles bizarreries, et la raison pour laquelle elles ne trompent pas le labo.", "",
                "| Photo | Astre | L'explication |", "|---|---|---|"]
        for c in curios:
            ctx = json.loads(c["contexte"]) if c["contexte"] else {}
            facts = "".join(f"<br>• {cell(x)}" for x in ctx.get("indices", []) + ctx.get("differences", []))
            name = BODIES.get(c["target"], c["target"])
            out.append(f"| {thumbs([{**c, 'rank': 1, 'target': name}], 110)} | **{cell(name)}**<br>{cell(c['instrument'])},"
                       f" {(c['time1'] or '–')[:10]} | {cell(c['text'])}{facts} |")
    out += ["", "---", "", "*Page mise à jour automatiquement par le labo. Retour à la [présentation](../README.md).*", ""]
    return "\n".join(out)


def discoveries():
    """Ce que le labo a trouve jusqu'ici, en clair, pour les deux missions."""
    out = ["## Ce que le labo a trouvé", ""]
    # Seules les photos que l'IA du labo juge vraiment interessantes sont montrees : pas les defauts.
    finds = find_rows()
    judged = scalar(SONDES_DB, "SELECT COUNT(*) FROM descriptions WHERE verdict IS NOT NULL")
    out += ["### Sondes Fantômes : les trouvailles", ""]
    if finds:
        out += [f"L'IA du labo a examiné {num(judged)} photos qui sortaient de l'ordinaire. La plupart s'expliquent"
                " par un défaut d'image ou par quelque chose de déjà connu. Celles-ci, en revanche, méritent un regard"
                " humain. Chacune a son dossier complet : la fiche de la prise de vue, les photos d'avant et d'après,"
                " des hypothèses et comment vérifier.", "", "| Photo | Trouvaille |", "|---|---|"]
        for f in finds[:8]:
            img = (f'<a href="{FINDS}/{f["page"]}"><img src="{html.escape(OPUS_PREVIEWS + f["small"])}" width="140"'
                   f' alt="{html.escape(f["name"])}"></a>')
            out.append(f"| {img} | **[{cell(f['title'])}]({FINDS}/{f['page']})**<br>{cell(f['name'])},"
                       f" {cell(f['instrument'])}, {(f['time1'] or '–')[:10]}<br>{cell(f['text'])} |")
        out += ["", f"**[Voir toutes les trouvailles et leurs dossiers]({FINDS}/)**", ""]
    elif judged:
        out += [f"Rien de vraiment intéressant pour l'instant. L'IA du labo a examiné {num(judged)} photos qui"
                " sortaient de l'ordinaire : toutes s'expliquent par un défaut d'image ou par quelque chose de déjà"
                f" connu. Les vraies trouvailles apparaîtront ici, et dans la page [Trouvailles]({FINDS}/), qui montre"
                " déjà les curiosités expliquées.", ""]
    else:
        out += ["Pas encore de trouvaille. Chaque photo qui sort de l'ordinaire doit d'abord être examinée par l'IA"
                " du labo, qui écarte les défauts d'image et les choses déjà connues. Seules les photos qui méritent"
                f" vraiment un regard humain apparaîtront ici, et dans la page [Trouvailles]({FINDS}/).", ""]
    checks = rows(NEURO_DB, "SELECT * FROM recipes WHERE control IS NOT NULL")
    if checks:
        good = sorted((r for r in checks if confirmed(r)), key=lambda r: r["control"] - r["confirmed"])
        frozen = sum(1 for r in checks if not confirmed(r) and r["confirmed"] >= MIN_EFFECT)
        out += ["### Labo de neurones : ce qui marche vraiment", ""]
        if good:
            b = good[0]
            out += [f"**{len(good)} recette{'s' if len(good) > 1 else ''} sur {len(checks)} {'ont' if len(good) > 1 else 'a'}"
                    f" passé la vérification** : les neurones capables d'apprendre progressent nettement plus que les"
                    f" neurones figés. La plus nette, la recette n°{b['id']}, fait gagner {pts(b['confirmed'])} points"
                    f" aux neurones qui apprennent, contre {pts(b['control'])} aux neurones figés. Détails dans"
                    " [les résultats complets](resultats/neurones.md).", ""]
        else:
            lost = len(checks) - frozen
            why = [f"{'à chaque fois' if not frozen else f'{lost} fois sur {len(checks)}'}, le progrès a disparu"
                   if lost else "",
                   f"{'à chaque fois' if not lost else f'{frozen} fois sur {len(checks)}'}, des neurones figés,"
                   " incapables d'apprendre, ont progressé tout autant" if frozen else ""]
            out += [f"**Pour l'instant, aucune façon d'entraîner les neurones n'a passé la vérification.** Le labo a"
                    f" rejoué ses {len(checks)} meilleures recettes sur des neurones neufs : "
                    + " ; ".join(w for w in why if w) + ".", "",
                    "Autrement dit : les beaux scores du début venaient surtout de la chance, pas d'un vrai"
                    " apprentissage. Ce n'est pas un échec : c'est un vrai résultat, qui montre qu'il ne faut pas"
                    " croire un bon score sans le vérifier. Le labo continue de chercher.", ""]
    return out if len(out) > 2 else []


def state(now, today, has_curve):
    """Section du README qui change a chaque publication."""
    best = best_recipe()
    lines = [
        "## Où en est le labo", "",
        f"*Mis à jour automatiquement le {utc(now)}.*", "",
        "| | |", "|---|---:|",
        f"| Photos de la NASA passées en revue | {num(scalar(SONDES_DB, 'SELECT COUNT(*) FROM images'))} |",
        f"| Astres entièrement passés en revue | {scalar(SONDES_DB, 'SELECT SUM(done) FROM campaigns')}"
        f" sur {scalar(SONDES_DB, 'SELECT COUNT(*) FROM campaigns')} |",
        f"| Parties de Pong jouées par les neurones | {num(scalar(NEURO_DB, 'SELECT COUNT(*) FROM sessions'))}"
        f" ({dec(scalar(NEURO_DB, 'SELECT SUM(sim_s) FROM sessions') / 3600)} h de jeu) |",
        f"| Façons d'entraîner essayées | {num(scalar(NEURO_DB, 'SELECT COUNT(*) FROM recipes WHERE learning IS NOT NULL'))} |",
    ]
    if best:
        lines.append(f"| Meilleur progrès observé, avant vérification | {pts(best['learning'])} points"
                     f" (recette n°{best['id']}) |")
    checks = rows(NEURO_DB, "SELECT * FROM recipes WHERE control IS NOT NULL")
    if checks:
        lines.append(f"| Progrès confirmés après vérification | {sum(map(confirmed, checks))} sur {len(checks)} |")
    if best and has_curve:
        lines += ["", f"**La recette qui a le mieux marché (n°{best['id']})** : part des balles renvoyées, minute"
                      " par minute, par des neurones qui apprennent (bleu) et par des neurones figés (gris) :", "",
                  f"![Courbe d'apprentissage de la meilleure recette](resultats/{CURVE})"]
    lines += ["", f"Dernier rapport : [{today}](rapports/{today}.md)", ""] + discoveries() + [""]
    return "\n".join(lines)


def report(now, number):
    day = now - now % 86400
    out = (["# Rapport n°1 : bonjour !", "", f"*{long_date(now)}*", "", FIRST_WORDS] if number == 1
           else [f"# Rapport n°{number} : {long_date(now)}", ""])

    out += [
        "## Sondes Fantômes", "",
        f"- **{num(scalar(SONDES_DB, 'SELECT COUNT(*) FROM images WHERE added_at >= ?', (day,)))}** images analysées"
        f" aujourd'hui, **{num(scalar(SONDES_DB, 'SELECT COUNT(*) FROM images'))}** au total.",
        f"- Cibles entièrement fouillées : **{scalar(SONDES_DB, 'SELECT SUM(done) FROM campaigns')}"
        f" / {scalar(SONDES_DB, 'SELECT COUNT(*) FROM campaigns')}**.", ""]
    scored = rows(SONDES_DB, """
        SELECT c.*, COUNT(i.opus_id) AS n FROM campaigns c JOIN images i ON i.campaign_id = c.id
        WHERE c.scored_at >= ? GROUP BY c.id ORDER BY c.scored_at""", (day,))
    if scored:
        out += ["### Astres comparés aujourd'hui", "",
                ", ".join(f"{BODIES.get(c['target'], c['target'])} ({c['instrument']}, {num(c['n'])} photos)"
                          for c in scored) + ".", ""]
    finds = [f for f in find_rows() if f["created_at"] >= day]
    if finds:
        out += ["### Trouvailles du jour", ""]
        for f in finds:
            out += [f"**[{f['title']}](../{FINDS}/{f['page']})** ({f['name']}) : {f['text']}", "",
                    thumbs([{**f, "target": f["name"]}], 160), ""]
    entries = rows(SONDES_DB, "SELECT * FROM journal WHERE t >= ? ORDER BY t", (day,))
    if entries:
        out += ["### Journal", ""] + [f"- {hm(e['t'])} : {e['msg']}" for e in entries] + [""]

    best = best_recipe()
    tested = rows(NEURO_DB, "SELECT * FROM recipes WHERE learning IS NOT NULL AND created_at >= ?"
                            " ORDER BY learning DESC", (day,))
    out += [
        "## Labo de neurones", "",
        f"- **{num(scalar(NEURO_DB, 'SELECT COUNT(*) FROM sessions WHERE t >= ?', (day,)))}** parties jouées aujourd'hui"
        f" ({dec(scalar(NEURO_DB, 'SELECT SUM(sim_s) FROM sessions WHERE t >= ?', (day,)) / 3600)} h de culture"
        f" simulée), **{num(scalar(NEURO_DB, 'SELECT COUNT(*) FROM sessions'))}** au total.",
        f"- **{len(tested)}** recettes d'entraînement testées aujourd'hui."]
    if best:
        line = (f"- Meilleure recette à ce jour : **n°{best['id']}**, {pts(best['learning'])} points"
                f" ({pct(best['early'])} de balles renvoyées au début, {pct(best['late'])} à la fin)")
        if best["control"] is not None:
            line += f". Contre-épreuve : {control_result(best)}"
        out.append(line + ".")
    checks = rows(NEURO_DB, "SELECT * FROM recipes WHERE control IS NOT NULL")
    if checks:
        out.append(f"- Apprentissages confirmés par contre-épreuve : **{sum(map(confirmed, checks))} sur {len(checks)}**.")
    out.append("")
    if tested:
        out += ["### Meilleures recettes du jour", "", recipes_table(tested[:5]), ""]
    notable = [e for e in rows(NEURO_DB, "SELECT * FROM journal WHERE t >= ? ORDER BY t", (day,))
               if any(word in e["msg"] for word in NOTABLE)]
    if notable:
        out += ["### Faits marquants", ""] + [f"- {hm(e['t'])} : {e['msg']}" for e in notable] + [""]
    out += ["---", "", "*Rapport écrit automatiquement par le labo. Présentation complète : [README](../README.md).*", ""]
    return "\n".join(out)


def sondes_results(now):
    out = ["# Sondes Fantômes : toutes les cibles classées", "",
           f"*Mis à jour le {utc(now)}. Pour chaque cible, les 10 images les plus inhabituelles, de la plus étrange"
           " à la moins étrange, sauf celles que l'IA du labo a jugées ratées. Cliquer sur une image ouvre sa fiche"
           " NASA (OPUS).*", ""]
    campaigns = rows(SONDES_DB, """
        SELECT c.*, COUNT(i.opus_id) AS n, SUM(i.artifact IS NOT NULL) AS flagged FROM campaigns c
        JOIN images i ON i.campaign_id = c.id WHERE c.scored_at IS NOT NULL GROUP BY c.id ORDER BY c.instrument, c.target""")
    if not campaigns:
        out.append("Aucune cible classée pour l'instant : il faut au moins 30 images d'une même cible.")
    for c in campaigns:
        status = "fouille terminée" if c["done"] else "fouille en cours"
        ranked = rows(SONDES_DB, """
                SELECT i.*, d.text, d.verdict FROM images i LEFT JOIN descriptions d ON d.opus_id = i.opus_id
                WHERE i.campaign_id=? AND i.rank <= 10 ORDER BY i.rank""", (c["id"],))
        out += [f"## {c['target']} ({c['instrument']})", "",
                f"{num(c['n'])} images analysées, dont {num(c['flagged'])} écartées comme ratées ; {status}."
                f" Classement du {utc(c['scored_at'])}.", ""]
        if not ranked:
            out += ["Pas de classement : il reste moins de 30 images exploitables pour les comparer entre elles.", ""]
            continue
        out += ["| Rang | Image | Date | Score | Avis de l'IA du labo |", "|---:|---|---|---:|---|"]
        for i in ranked:
            if i["verdict"] == "defaut":  # simple defaut d'image : rien a montrer
                continue
            img = thumbs([{"opus_id": i["opus_id"], "small": i["small"], "rank": i["rank"], "target": c["target"]}], 90)
            opinion = {"interessant": "**À regarder.** ", "connu": "Déjà connu ou banal. "}.get(i["verdict"], "")
            text = opinion + (i["text"] or "pas encore examinée")
            out.append(f"| {i['rank']} | {img} | {(i['time1'] or '')[:10]} | {i['score']:.3f} | {cell(text)} |")
        out.append("")
    return "\n".join(out)


def neurones_results(now, has_curve):
    out = ["# Labo de neurones : recettes d'entraînement", "",
           f"*Mis à jour le {utc(now)}. Progrès = balles renvoyées pendant les 5 dernières minutes de jeu, moins les"
           " 5 premières, en points, en moyenne sur 3 cultures.*", ""]
    if has_curve:
        out += ["## La meilleure recette, minute par minute", "", f"![Courbe d'apprentissage]({CURVE})", ""]
    recipes = rows(NEURO_DB, "SELECT * FROM recipes WHERE learning IS NOT NULL ORDER BY learning DESC LIMIT 30")
    out += ["## Les 30 meilleures recettes", "",
            recipes_table(recipes) if recipes else "Aucune recette terminée pour l'instant.", ""]
    checks = rows(NEURO_DB, "SELECT * FROM recipes WHERE control IS NOT NULL ORDER BY id")
    out += ["## Contre-épreuves", "",
            "Une contre-épreuve rejoue une recette prometteuse sur 3 cultures neuves, avec et sans plasticité."
            " Un vrai apprentissage doit apparaître avec la plasticité, et pas sans.", "",
            recipes_table(checks) if checks else "Pas encore de contre-épreuve : la première arrive après 10 recettes.", ""]
    return "\n".join(out)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_all(now):
    today = time.strftime("%Y-%m-%d", time.gmtime(now))
    reports = REPO / "rapports"
    earlier = [p for p in reports.glob("*.md") if p.stem != today] if reports.exists() else []
    best = best_recipe()
    svg = curve_svg(best["id"]) if best else None
    if svg:
        write(REPO / "resultats" / CURVE, svg)
    write(REPO / "README.md", HEADER + state(now, today, bool(svg)) + BODY)
    write(REPO / "resultats" / "sondes.md", sondes_results(now))
    write(REPO / "resultats" / "neurones.md", neurones_results(now, bool(svg)))
    write(reports / f"{today}.md", report(now, len(earlier) + 1))
    found = find_rows()
    shutil.rmtree(REPO / FINDS, ignore_errors=True)
    write(REPO / FINDS / "README.md", finds_index(found))
    for f in found:
        write(REPO / FINDS / f["page"], find_page(f))
    code = REPO / "code" / "labo"
    shutil.rmtree(code, ignore_errors=True)
    code.mkdir(parents=True)
    for f in sorted((BASE / "labo").glob("*.py")):
        shutil.copy(f, code / f.name)


def main():
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    if PUBLICATION_SETTINGS.exists():
        url = json.loads(PUBLICATION_SETTINGS.read_text())["repo"]
    else:
        url = discover()
        if not url:
            log.info("en attente : la cle de deploiement n'est encore ajoutee a aucun depot GitHub")
            return
        log.info("depot trouve grace a la cle de deploiement : %s", url)
    now = time.time()
    last = json.loads(PUBLICATION_STATUS.read_text()) if PUBLICATION_STATUS.exists() else {}
    if last.get("ok") and now - last["t"] < PAUSE and "--maintenant" not in sys.argv:
        return
    page = "https://github.com/" + url.split(":", 1)[1].removesuffix(".git")
    try:
        sync(url)
        first = not (REPO / "rapports").exists()
        write_all(now)
        git("add", "-A")
        if git("diff", "--cached", "--quiet", check=False).returncode == 0:
            msg = "rien de nouveau à publier"
        else:
            msg = ("Présentation du Labo IA et premier rapport" if first else
                   f"Rapport du {time.strftime('%d/%m/%Y', time.gmtime(now))} : "
                   f"{num(scalar(SONDES_DB, 'SELECT COUNT(*) FROM images'))} images analysées, "
                   f"{num(scalar(NEURO_DB, 'SELECT COUNT(*) FROM recipes WHERE learning IS NOT NULL'))} recettes testées")
            git("commit", "-q", "-m", msg)
            git("push", "-q", "origin", "main")
        ok = True
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as e:
        log.info("%s", e)
        ok, msg = False, next((hint for key, hint in HINTS if key in str(e)), str(e))
    PUBLICATION_STATUS.write_text(json.dumps({"t": now, "ok": ok, "msg": msg, "url": page}, ensure_ascii=False))
    log.info("%s : %s", "publie" if ok else "echec", msg)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    if sys.argv[1:] == ["--apercu"]:
        # Genere les fichiers dans /tmp sans rien envoyer, pour relire le rendu.
        REPO = Path("/tmp/labo-apercu")
        write_all(time.time())
        print(REPO)
    else:
        main()
