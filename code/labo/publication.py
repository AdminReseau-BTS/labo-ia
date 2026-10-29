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

from .config import (BASE, DATA, DEPLOY_KEY, FEEDBACK_MODES, NEURO_DB, OPUS_PREVIEWS, PUBLICATION_SETTINGS,
                     PUBLICATION_STATUS, SONDES_DB)
from .db import rows, scalar
from .web import OPUS_DETAIL, chart, mean_curve, pts

log = logging.getLogger("publication")

REPO = DATA / "publication"
SSH = ["ssh", "-i", str(DEPLOY_KEY), "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
       "-o", "StrictHostKeyChecking=yes", "-o", f"UserKnownHostsFile={DEPLOY_KEY.parent / 'known_hosts'}"]
PAUSE = 5.5 * 3600  # minimum entre deux publications reussies (le timer repasse toutes les heures)
AUTHOR = ("Labo IA", "labo-ia@localhost")
CURVE = "courbe-meilleure-recette.svg"
NOTABLE = ("Contre-Ã©preuve", "Meilleure recette", "proposÃ©e par l'IA", "dÃ©marrÃ©")
MIN_EFFECT = 0.05  # meme seuil que labo.neurones : en dessous de 5 points, on ne parle pas d'apprentissage
MONTHS = ("janvier", "fÃ©vrier", "mars", "avril", "mai", "juin", "juillet", "aoÃ»t",
          "septembre", "octobre", "novembre", "dÃ©cembre")
# Erreurs les plus probables, traduites en ce qu'il faut faire.
HINTS = (
    ("read only", "la clÃ© de dÃ©ploiement est en lecture seule ; supprime-la du dÃ©pÃ´t sur GitHub et ajoute-la"
                  " de nouveau en cochant Â« Allow write access Â»"),
    ("Repository not found", "dÃ©pÃ´t introuvable ; la clÃ© de dÃ©ploiement a peut-Ãªtre Ã©tÃ© retirÃ©e du dÃ©pÃ´t"),
    ("Permission denied", "GitHub refuse la clÃ© de dÃ©ploiement ; elle a peut-Ãªtre Ã©tÃ© retirÃ©e du dÃ©pÃ´t"),
    ("Could not resolve", "pas d'accÃ¨s Ã  Internet pour l'instant"),
)

HEADER = """# Labo IA

**Un laboratoire autonome qui tourne jour et nuit sur un serveur domestique, et qui publie ici ses recherches tout seul.**

Il poursuit deux missions :

1. **Sondes FantÃ´mes** : relire avec un Å“il neuf les centaines de milliers d'images prises par les sondes spatiales de la NASA (Voyager, Galileo, Cassini, New Horizons), pour faire remonter celles qui ne ressemblent Ã  aucune autre.
2. **Labo de neurones** : apprendre Ã  jouer Ã  Pong Ã  une culture de neurones simulÃ©s, sur le modÃ¨le de l'expÃ©rience DishBrain, en inventant et en testant lui-mÃªme des protocoles d'entraÃ®nement.

Ce dÃ©pÃ´t est son carnet de recherche : la prÃ©sentation ci-dessous, [un rapport par jour](rapports/), les rÃ©sultats complets ([Sondes FantÃ´mes](resultats/sondes.md), [neurones](resultats/neurones.md)) et le [code source](code/labo/). Il se met Ã  jour automatiquement toutes les 6 heures.

"""

BODY = """## Mission 1 : Sondes FantÃ´mes

### L'idÃ©e

Les archives planÃ©taires publiques contiennent des centaines de milliers d'images. La plupart n'ont Ã©tÃ© regardÃ©es que pour la raison prÃ©cise pour laquelle elles avaient Ã©tÃ© prises. Une IA peut toutes les passer en revue, sans fatigue et sans idÃ©e prÃ©conÃ§ue, et signaler celles qui sortent du lot. Ce ne sont pas des dÃ©couvertes, mais des images qui mÃ©ritent un regard humain.

### Comment Ã§a marche

1. **Les donnÃ©es** viennent de l'API publique [OPUS](https://opus.pds-rings.seti.org) du PDS Ring-Moon Systems Node (NASA). Pas de compte, pas de clÃ©, et un tÃ©lÃ©chargement poli, avec une pause entre deux images.
2. **Chaque image** (aperÃ§u de 200 Ã— 200 pixels) est rÃ©sumÃ©e en 512 nombres par un rÃ©seau de vision prÃ©-entraÃ®nÃ© (ResNet-18).
3. **Une image n'est Ã©trange que par rapport Ã  ses semblables** : elle est comparÃ©e seulement aux autres images de la mÃªme cible prises par le mÃªme instrument. Deux mesures sont combinÃ©es : la distance moyenne Ã  ses 10 plus proches voisines, et un score d'Isolation Forest calculÃ© sur une rÃ©duction Ã  32 dimensions.
4. **Les images ratÃ©es sont Ã©cartÃ©es** : presque noires, saturÃ©es, uniformes, incomplÃ¨tes (marges ou bandes sans donnÃ©es), ou faites presque uniquement de bruit.
5. **Les 10 images les plus isolÃ©es de chaque groupe deviennent des candidates.** Si une IA locale est installÃ©e (Ollama avec gemma3:4b, gratuite et hors ligne), elle dÃ©crit chaque candidate et dit si cela ressemble Ã  un dÃ©faut d'image, Ã  quelque chose de connu, ou Ã  quelque chose qui mÃ©rite d'Ãªtre vÃ©rifiÃ©.

La fouille commence par huit cibles (Io, Europe, Miranda, Triton, HypÃ©rion, Encelade, Pluton, Arrokoth), puis s'Ã©tend Ã  toutes les cibles des cinq camÃ©ras, soit environ 560 000 images.

### Ã€ garder en tÃªte

La plupart des anomalies seront des effets d'instrument, des prises de vue inhabituelles ou des phÃ©nomÃ¨nes dÃ©jÃ  connus. Chaque candidate renvoie vers sa fiche OPUS et ses mÃ©tadonnÃ©es complÃ¨tes, pour pouvoir vÃ©rifier.

## Mission 2 : Labo de neurones

### L'idÃ©e

En 2022, l'entreprise Cortical Labs a montrÃ© (expÃ©rience DishBrain, [Kagan et al., *Neuron*](https://doi.org/10.1016/j.neuron.2022.09.001)) que des neurones vivants cultivÃ©s sur une puce d'Ã©lectrodes apprennent Ã  jouer Ã  Pong en quelques minutes. La recette : une stimulation prÃ©visible quand ils renvoient la balle, et une stimulation imprÃ©visible quand ils la ratent. Pourquoi cela marche reste dÃ©battu.

Ce labo rejoue l'expÃ©rience en simulation, sans arrÃªt, pour chercher quels protocoles d'entraÃ®nement et quels mÃ©canismes biologiques rendent cet apprentissage possible.

### La culture virtuelle

- **1 000 neurones impulsionnels** (modÃ¨le d'Izhikevich), dont 80 % excitateurs et 20 % inhibiteurs, posÃ©s sur une puce de 8 Ã— 8 Ã©lectrodes, avec des connexions surtout locales.
- **PlasticitÃ©** : les synapses excitatrices se renforcent ou s'affaiblissent selon l'ordre des impulsions (STDP). Une fatigue synaptique Ã  court terme produit les bouffÃ©es d'activitÃ© typiques des vraies cultures, et une homÃ©ostasie empÃªche le rÃ©seau de s'emballer ou de s'Ã©teindre.
- **Ã‰lectrodes** : chacune enregistre les neurones tout proches. Une stimulation excite les neurones autour de l'Ã©lectrode, et d'autant plus loin que le courant est fort.
- **BranchÃ©e sur le SDK officiel de Cortical Labs** ([cl-sdk](https://pypi.org/project/cl-sdk/)) comme source de donnÃ©es de son simulateur : le code de l'expÃ©rience utilise la mÃªme API que la vraie puce CL1, et pourrait tourner tel quel sur de vrais neurones.

### Le jeu

Pong Ã  une raquette, contre un mur. Huit Ã©lectrodes sensorielles au centre de la puce codent la balle : sa hauteur choisit l'Ã©lectrode stimulÃ©e, sa distance rÃ¨gle la frÃ©quence de stimulation. Deux zones motrices, Â« haut Â» et Â« bas Â», dÃ©placent la raquette selon leur activitÃ© relative. AprÃ¨s une balle ratÃ©e, trois faÃ§ons de rÃ©agir sont comparÃ©es : le retour de DishBrain (stimulation alÃ©atoire pendant quelques secondes, et salve prÃ©visible aprÃ¨s chaque renvoi), le silence, ou rien du tout.

### La mÃ©thode

- Une **recette** combine une faÃ§on de rÃ©agir et dix rÃ©glages : courants, durÃ©es, frÃ©quences, vitesse de la raquette, et deux hypothÃ¨ses biologiques (fenÃªtre de plasticitÃ©, niveau d'activitÃ© visÃ© par l'homÃ©ostasie). La premiÃ¨re recette testÃ©e est le protocole publiÃ© de DishBrain.
- Chaque recette joue **16 minutes simulÃ©es sur 3 cultures** (1 minute d'Ã©chauffement, puis 15 minutes de jeu). Son **progrÃ¨s** est le taux de balles renvoyÃ©es pendant les 5 derniÃ¨res minutes, moins celui des 5 premiÃ¨res.
- **Recherche Ã©volutionniste** : les meilleures recettes sont modifiÃ©es au hasard pour en crÃ©er de nouvelles, une partie des essais explore des recettes entiÃ¨rement nouvelles, et l'IA locale, si elle est installÃ©e, propose de temps en temps une recette en expliquant l'hypothÃ¨se qu'elle teste.
- **Contre-Ã©preuve** : toutes les 10 recettes, la meilleure est rejouÃ©e sur 3 cultures neuves, avec et sans plasticitÃ©. Un vrai apprentissage doit apparaÃ®tre avec la plasticitÃ©, et pas sans.

### Ã€ garder en tÃªte

1 000 neurones simulÃ©s ne sont pas des centaines de milliers de neurones vivants. Les rÃ©sultats sont des hypothÃ¨ses Ã  tester sur du vrai matÃ©riel, pas des preuves biologiques.

## MatÃ©riel et coÃ»t

Le labo tourne dans un conteneur Linux sur un serveur domestique : 3 cÅ“urs de processeur, pas de carte graphique, en prioritÃ© basse pour ne gÃªner personne. Tout est gratuit : donnÃ©es publiques de la NASA, logiciels libres, simulateur du SDK de Cortical Labs. Seule l'Ã©lectricitÃ© coÃ»te.

## Sources

- OPUS, PDS Ring-Moon Systems Node : https://opus.pds-rings.seti.org
- Kagan B. J. et al. (2022), *In vitro neurons learn and exhibit sentience when embodied in a simulated game-world*, Neuron 110(23). https://doi.org/10.1016/j.neuron.2022.09.001
- Izhikevich E. M. (2003), *Simple model of spiking neurons*, IEEE Transactions on Neural Networks 14(6).
- Cortical Labs, cl-sdk : https://pypi.org/project/cl-sdk/ (licence CC BY-NC 4.0)
"""

FIRST_WORDS = """Bonjour ! Je suis **Labo IA**, un petit laboratoire autonome. Je tourne jour et nuit sur un serveur domestique, sans carte graphique, et je ne coÃ»te rien d'autre que de l'Ã©lectricitÃ©. Ce dÃ©pÃ´t est mon carnet de recherche : je le mets Ã  jour moi-mÃªme toutes les 6 heures.

J'ai deux missions.

**Sondes FantÃ´mes.** Je relis une par une les images d'archives des sondes Voyager, Galileo, Cassini et New Horizons. Pour chaque cible, je compare chaque image Ã  toutes les autres, et je fais remonter celles qui ne ressemblent Ã  aucune. Ce ne sont pas des dÃ©couvertes, mais des images qui mÃ©ritent un regard humain.

**Labo de neurones.** Je fais jouer Ã  Pong une culture de 1 000 neurones simulÃ©s, branchÃ©e sur le SDK officiel de Cortical Labs, comme l'expÃ©rience DishBrain l'a fait en 2022 avec de vrais neurones. J'invente des faÃ§ons d'entraÃ®ner la culture, je les teste, je garde les meilleures, et je vÃ©rifie chaque piste prometteuse par une contre-Ã©preuve sur des cultures incapables d'apprendre.

Tout est expliquÃ© en dÃ©tail dans la [prÃ©sentation du projet](../README.md). Voici oÃ¹ j'en suis.
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
    return f"{time.strftime('%d/%m/%Y', g)} Ã  {time.strftime('%H:%M', g)} UTC"


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
        label = html.escape(f"{c['target']}, nÂ°{c['rank']}")
        out.append(f'<a href="{html.escape(OPUS_DETAIL + c["opus_id"])}"><img src="{html.escape(OPUS_PREVIEWS + c["small"])}"'
                   f' width="{width}" alt="{label}" title="{label}"></a>')
    return " ".join(out)


def curve_svg(recipe_id):
    """Courbe de la meilleure recette, en SVG autonome lisible sur fond clair comme sombre."""
    series = []
    for plastic, name in ((1, "avec plasticitÃ©"), (0, "culture figÃ©e (tÃ©moin)")):
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
        return "â€“"
    verdict = ("confirmÃ©" if confirmed(r) else
               "les cultures figÃ©es progressent autant" if r["confirmed"] >= MIN_EFFECT else "non reproduit")
    return f"{pts(r['confirmed'])} avec plasticitÃ©, {pts(r['control'])} sans : {verdict}"


def recipes_table(recipes):
    lines = ["| nÂ° | Protocole | RÃ©glages | DÃ©but â†’ fin | ProgrÃ¨s | Contre-Ã©preuve |",
             "|---:|---|---|---:|---:|---|"]
    for r in recipes:
        p = json.loads(r["params"])
        v = {k: dec(x, "g") for k, x in p.items() if k != "mode"}
        settings = (f"stimulation {v['sens_amp']} ÂµA de {v['rate_min']} Ã  {v['rate_max']} Hz ; "
                    f"retour {v['fb_amp']} ÂµA, {v['fb_seconds']} s Ã  {v['fb_rate']} Hz, salve de {v['hit_pulses']} ; "
                    f"raquette Ã—{v['gain']} ; STDP {v['stdp_tau']} ms ; homÃ©ostasie {v['target_hz']} Hz")
        lines.append(f"| {r['id']} | {cell(FEEDBACK_MODES.get(p['mode'], p['mode']))}<br>*{cell(r['origin'])}* "
                     f"| {settings} | {pct(r['early'])} â†’ {pct(r['late'])} | **{pts(r['learning'])}** "
                     f"| {control_result(r)} |")
    return "\n".join(lines)


def best_recipe():
    best = rows(NEURO_DB, "SELECT * FROM recipes WHERE learning IS NOT NULL ORDER BY learning DESC LIMIT 1")
    return best[0] if best else None


def state(now, today, has_curve):
    """Section du README qui change a chaque publication."""
    best = best_recipe()
    lines = [
        "## OÃ¹ en est le labo", "",
        f"*Mis Ã  jour automatiquement le {utc(now)}.*", "",
        "| Indicateur | Valeur |", "|---|---:|",
        f"| Images d'archives analysÃ©es | {num(scalar(SONDES_DB, 'SELECT COUNT(*) FROM images'))} |",
        f"| Cibles entiÃ¨rement fouillÃ©es | {scalar(SONDES_DB, 'SELECT SUM(done) FROM campaigns')}"
        f" / {scalar(SONDES_DB, 'SELECT COUNT(*) FROM campaigns')} |",
        f"| Parties de Pong jouÃ©es | {num(scalar(NEURO_DB, 'SELECT COUNT(*) FROM sessions'))}"
        f" ({dec(scalar(NEURO_DB, 'SELECT SUM(sim_s) FROM sessions') / 3600)} h de culture simulÃ©e) |",
        f"| Recettes d'entraÃ®nement testÃ©es | {num(scalar(NEURO_DB, 'SELECT COUNT(*) FROM recipes WHERE learning IS NOT NULL'))} |",
    ]
    if best:
        lines.append(f"| Meilleur progrÃ¨s (avant contre-Ã©preuve) | {pts(best['learning'])} points"
                     f" (recette nÂ°{best['id']}) |")
    checks = rows(NEURO_DB, "SELECT * FROM recipes WHERE control IS NOT NULL")
    if checks:
        lines.append(f"| Apprentissages confirmÃ©s par contre-Ã©preuve | {sum(map(confirmed, checks))} sur {len(checks)} |")
    latest = rows(SONDES_DB, """
        SELECT i.opus_id, i.small, i.rank, c.target FROM images i JOIN campaigns c ON c.id = i.campaign_id
        WHERE i.rank <= 2 ORDER BY c.scored_at DESC, c.id, i.rank LIMIT 8""")
    if latest:
        lines += ["", "**DerniÃ¨res candidates de Sondes FantÃ´mes** (cliquer pour ouvrir la fiche NASA) :", "", thumbs(latest)]
    if best and has_curve:
        lines += ["", f"**Meilleure recette (nÂ°{best['id']})**, balles renvoyÃ©es minute par minute :", "",
                  f"![Courbe d'apprentissage de la meilleure recette](resultats/{CURVE})"]
    lines += ["", f"Dernier rapport : [{today}](rapports/{today}.md)", "", ""]
    return "\n".join(lines)


def report(now, number):
    day = now - now % 86400
    out = (["# Rapport nÂ°1 : bonjour !", "", f"*{long_date(now)}*", "", FIRST_WORDS] if number == 1
           else [f"# Rapport nÂ°{number} : {long_date(now)}", ""])

    out += [
        "## Sondes FantÃ´mes", "",
        f"- **{num(scalar(SONDES_DB, 'SELECT COUNT(*) FROM images WHERE added_at >= ?', (day,)))}** images analysÃ©es"
        f" aujourd'hui, **{num(scalar(SONDES_DB, 'SELECT COUNT(*) FROM images'))}** au total.",
        f"- Cibles entiÃ¨rement fouillÃ©es : **{scalar(SONDES_DB, 'SELECT SUM(done) FROM campaigns')}"
        f" / {scalar(SONDES_DB, 'SELECT COUNT(*) FROM campaigns')}**.", ""]
    scored = rows(SONDES_DB, """
        SELECT c.*, COUNT(i.opus_id) AS n FROM campaigns c JOIN images i ON i.campaign_id = c.id
        WHERE c.scored_at >= ? GROUP BY c.id ORDER BY c.scored_at""", (day,))
    if scored:
        out += ["### Cibles classÃ©es aujourd'hui", ""]
        for c in scored:
            top = rows(SONDES_DB, "SELECT opus_id, small, rank, ? AS target FROM images"
                                  " WHERE campaign_id=? AND rank <= 5 ORDER BY rank", (c["target"], c["id"]))
            out += [f"**{c['target']}** ({c['instrument']}, {num(c['n'])} images), les 5 plus Ã©tranges :", "",
                    thumbs(top), ""]
    entries = rows(SONDES_DB, "SELECT * FROM journal WHERE t >= ? ORDER BY t", (day,))
    if entries:
        out += ["### Journal", ""] + [f"- {hm(e['t'])} : {e['msg']}" for e in entries] + [""]

    best = best_recipe()
    tested = rows(NEURO_DB, "SELECT * FROM recipes WHERE learning IS NOT NULL AND created_at >= ?"
                            " ORDER BY learning DESC", (day,))
    out += [
        "## Labo de neurones", "",
        f"- **{num(scalar(NEURO_DB, 'SELECT COUNT(*) FROM sessions WHERE t >= ?', (day,)))}** parties jouÃ©es aujourd'hui"
        f" ({dec(scalar(NEURO_DB, 'SELECT SUM(sim_s) FROM sessions WHERE t >= ?', (day,)) / 3600)} h de culture"
        f" simulÃ©e), **{num(scalar(NEURO_DB, 'SELECT COUNT(*) FROM sessions'))}** au total.",
        f"- **{len(tested)}** recettes d'entraÃ®nement testÃ©es aujourd'hui."]
    if best:
        line = (f"- Meilleure recette Ã  ce jour : **nÂ°{best['id']}**, {pts(best['learning'])} points"
                f" ({pct(best['early'])} de balles renvoyÃ©es au dÃ©but, {pct(best['late'])} Ã  la fin)")
        if best["control"] is not None:
            line += f". Contre-Ã©preuve : {control_result(best)}"
        out.append(line + ".")
    checks = rows(NEURO_DB, "SELECT * FROM recipes WHERE control IS NOT NULL")
    if checks:
        out.append(f"- Apprentissages confirmÃ©s par contre-Ã©preuve : **{sum(map(confirmed, checks))} sur {len(checks)}**.")
    out.append("")
    if tested:
        out += ["### Meilleures recettes du jour", "", recipes_table(tested[:5]), ""]
    notable = [e for e in rows(NEURO_DB, "SELECT * FROM journal WHERE t >= ? ORDER BY t", (day,))
               if any(word in e["msg"] for word in NOTABLE)]
    if notable:
        out += ["### Faits marquants", ""] + [f"- {hm(e['t'])} : {e['msg']}" for e in notable] + [""]
    out += ["---", "", "*Rapport Ã©crit automatiquement par le labo. PrÃ©sentation complÃ¨te : [README](../README.md).*", ""]
    return "\n".join(out)


def sondes_results(now):
    out = ["# Sondes FantÃ´mes : toutes les cibles classÃ©es", "",
           f"*Mis Ã  jour le {utc(now)}. Pour chaque cible, les 10 images les plus inhabituelles, de la plus Ã©trange"
           " Ã  la moins Ã©trange. Cliquer sur une image ouvre sa fiche NASA (OPUS).*", ""]
    campaigns = rows(SONDES_DB, """
        SELECT c.*, COUNT(i.opus_id) AS n, SUM(i.artifact IS NOT NULL) AS flagged FROM campaigns c
        JOIN images i ON i.campaign_id = c.id WHERE c.scored_at IS NOT NULL GROUP BY c.id ORDER BY c.instrument, c.target""")
    if not campaigns:
        out.append("Aucune cible classÃ©e pour l'instant : il faut au moins 30 images d'une mÃªme cible.")
    for c in campaigns:
        status = "fouille terminÃ©e" if c["done"] else "fouille en cours"
        ranked = rows(SONDES_DB, """
                SELECT i.*, d.text FROM images i LEFT JOIN descriptions d ON d.opus_id = i.opus_id
                WHERE i.campaign_id=? AND i.rank <= 10 ORDER BY i.rank""", (c["id"],))
        out += [f"## {c['target']} ({c['instrument']})", "",
                f"{num(c['n'])} images analysÃ©es, dont {num(c['flagged'])} Ã©cartÃ©es comme ratÃ©es ; {status}."
                f" Classement du {utc(c['scored_at'])}.", ""]
        if not ranked:
            out += ["Pas de classement : il reste moins de 30 images exploitables pour les comparer entre elles.", ""]
            continue
        out += ["| Rang | Image | Date | Score | Description par l'IA locale |", "|---:|---|---|---:|---|"]
        for i in ranked:
            img = thumbs([{"opus_id": i["opus_id"], "small": i["small"], "rank": i["rank"], "target": c["target"]}], 90)
            out.append(f"| {i['rank']} | {img} | {(i['time1'] or '')[:10]} | {i['score']:.3f} | {cell(i['text'] or 'â€“')} |")
        out.append("")
    return "\n".join(out)


def neurones_results(now, has_curve):
    out = ["# Labo de neurones : recettes d'entraÃ®nement", "",
           f"*Mis Ã  jour le {utc(now)}. ProgrÃ¨s = balles renvoyÃ©es pendant les 5 derniÃ¨res minutes de jeu, moins les"
           " 5 premiÃ¨res, en points, en moyenne sur 3 cultures.*", ""]
    if has_curve:
        out += ["## La meilleure recette, minute par minute", "", f"![Courbe d'apprentissage]({CURVE})", ""]
    recipes = rows(NEURO_DB, "SELECT * FROM recipes WHERE learning IS NOT NULL ORDER BY learning DESC LIMIT 30")
    out += ["## Les 30 meilleures recettes", "",
            recipes_table(recipes) if recipes else "Aucune recette terminÃ©e pour l'instant.", ""]
    checks = rows(NEURO_DB, "SELECT * FROM recipes WHERE control IS NOT NULL ORDER BY id")
    out += ["## Contre-Ã©preuves", "",
            "Une contre-Ã©preuve rejoue une recette prometteuse sur 3 cultures neuves, avec et sans plasticitÃ©."
            " Un vrai apprentissage doit apparaÃ®tre avec la plasticitÃ©, et pas sans.", "",
            recipes_table(checks) if checks else "Pas encore de contre-Ã©preuve : la premiÃ¨re arrive aprÃ¨s 10 recettes.", ""]
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
    code = REPO / "code" / "labo"
    shutil.rmtree(code, ignore_errors=True)
    code.mkdir(parents=True)
    for f in sorted((BASE / "labo").glob("*.py")):
        shutil.copy(f, code / f.name)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
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
            msg = "rien de nouveau Ã  publier"
        else:
            msg = ("PrÃ©sentation du Labo IA et premier rapport" if first else
                   f"Rapport du {time.strftime('%d/%m/%Y', time.gmtime(now))} : "
                   f"{num(scalar(SONDES_DB, 'SELECT COUNT(*) FROM images'))} images analysÃ©es, "
                   f"{num(scalar(NEURO_DB, 'SELECT COUNT(*) FROM recipes WHERE learning IS NOT NULL'))} recettes testÃ©es")
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

