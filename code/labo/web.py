"""Tableau de bord du labo, sur le port 8080 : visible sur le reseau local et, depuis le telephone,
par le VPN Tailscale (voir labo.vpn). Rien n'est expose sur Internet."""
import json
import time

from flask import Flask, abort, jsonify, redirect, render_template_string, request

from . import direct, vpn
from .config import (DEPLOY_KEY, FEEDBACK_MODES, NEURO_DB, OPUS_DETAIL, OPUS_PREVIEWS, PUBLICATION_STATUS,
                     SONDES_DB, VEILLE_DB)
from .db import connect, rows, scalar

app = Flask(__name__)


@app.context_processor
def unseen_errors():
    """Nombre d'erreurs pas encore vues, affiche dans le menu de chaque page."""
    return {"unseen": scalar(VEILLE_DB, "SELECT COUNT(*) FROM erreurs WHERE vue=0 AND niveau='erreur'")}


@app.template_filter("when")
def when(t):
    return time.strftime("%d/%m %H:%M", time.localtime(t))


@app.template_filter("pts")
def pts(x):
    return "–" if x is None else f"{x * 100:+.0f}"


def mean_curve(sessions):
    curves = [json.loads(s["curve"]) for s in sessions]
    out = []
    for vals in zip(*curves):
        vals = [v for v in vals if v is not None]
        out.append(sum(vals) / len(vals) if vals else None)
    return out


def chart(series, w=640, h=200, pad=30):
    """Courbes de taux de renvoi par minute, en SVG."""
    values = [v for _, curve in series for v in curve if v is not None]
    if not values:
        return None
    top = max(0.5, -(-max(values) * 10 // 1) / 10)
    n = max(len(curve) for _, curve in series)

    def xy(i, v):
        return pad + i * (w - 2 * pad) / max(n - 1, 1), h - pad - v / top * (h - 2 * pad)

    lines = [{"name": name, "points": " ".join(f"{x:.1f},{y:.1f}" for x, y in
                                               (xy(i, v) for i, v in enumerate(curve) if v is not None))}
             for name, curve in series]
    grid = [{"y": xy(0, f * top)[1], "label": f"{f * top:.0%}"} for f in (0, 0.5, 1)]
    return {"w": w, "h": h, "pad": pad, "lines": lines, "grid": grid, "n": n}


@app.route("/")
def index():
    now = time.time()
    sondes = {
        "images": scalar(SONDES_DB, "SELECT COUNT(*) FROM images"),
        "last_hour": scalar(SONDES_DB, "SELECT COUNT(*) FROM images WHERE added_at > ?", (now - 3600,)),
        "total": scalar(SONDES_DB, "SELECT COUNT(*) FROM campaigns"),
        "done": scalar(SONDES_DB, "SELECT SUM(done) FROM campaigns"),
        "described": scalar(SONDES_DB, "SELECT COUNT(*) FROM descriptions"),
        "current": (rows(SONDES_DB, "SELECT * FROM campaigns WHERE done=0 ORDER BY id LIMIT 1") or [None])[0],
    }
    candidates = rows(SONDES_DB, """
        SELECT i.*, c.instrument, c.target, d.text, d.verdict FROM images i
        JOIN campaigns c ON c.id = i.campaign_id LEFT JOIN descriptions d ON d.opus_id = i.opus_id
        WHERE i.rank <= 3 ORDER BY c.scored_at DESC, c.id, i.rank LIMIT 24""")
    # Trouvailles : photos que l'IA du labo juge dignes d'un regard humain (apres sa double verification).
    finds = rows(SONDES_DB, """
        SELECT i.*, c.instrument, c.target, d.text, d.created_at,
               json_extract(s.data, '$.titre') AS titre, json_extract(s.data, '$.conclusion') AS conclusion
        FROM descriptions d JOIN images i ON i.opus_id = d.opus_id JOIN campaigns c ON c.id = i.campaign_id
        LEFT JOIN dossiers s ON s.opus_id = d.opus_id
        WHERE d.verdict = 'interessant' ORDER BY d.created_at DESC LIMIT 12""")
    verdicts = {r[0]: r[1] for r in rows(SONDES_DB, "SELECT verdict, COUNT(*) FROM descriptions GROUP BY verdict")}
    to_judge = scalar(SONDES_DB, """SELECT COUNT(*) FROM images i LEFT JOIN descriptions d ON d.opus_id = i.opus_id
                                    WHERE i.rank <= 10 AND d.opus_id IS NULL""")
    alerts = rows(VEILLE_DB, "SELECT * FROM erreurs WHERE vue=0 ORDER BY niveau='erreur' DESC, derniere DESC LIMIT 6")
    groups = rows(SONDES_DB, """
        SELECT c.*, COUNT(i.opus_id) AS n FROM campaigns c JOIN images i ON i.campaign_id = c.id
        WHERE c.scored_at IS NOT NULL GROUP BY c.id ORDER BY c.scored_at DESC LIMIT 15""")

    neuro = {
        "sessions": scalar(NEURO_DB, "SELECT COUNT(*) FROM sessions"),
        "sim_hours": scalar(NEURO_DB, "SELECT SUM(sim_s) FROM sessions") / 3600,
        "recipes": scalar(NEURO_DB, "SELECT COUNT(*) FROM recipes WHERE learning IS NOT NULL"),
    }
    recipes = []
    for r in rows(NEURO_DB, "SELECT * FROM recipes WHERE learning IS NOT NULL ORDER BY learning DESC LIMIT 8"):
        p = json.loads(r["params"])
        recipes.append({**dict(r), "mode": FEEDBACK_MODES.get(p["mode"], p["mode"]), "p": p})
    best_chart = None
    if recipes:
        series = []
        for plastic, name in ((1, "avec plasticité"), (0, "culture figée (témoin)")):
            sessions = rows(NEURO_DB, "SELECT curve FROM sessions WHERE recipe_id=? AND plastic=?",
                            (recipes[0]["id"], plastic))
            if sessions:
                series.append((name, mean_curve(sessions)))
        best_chart = chart(series) if series else None

    pub = json.loads(PUBLICATION_STATUS.read_text()) if PUBLICATION_STATUS.exists() else None
    # Tant que rien n'est publie, la page montre la cle a ajouter sur GitHub.
    key = DEPLOY_KEY.with_suffix(".pub")
    deploy_key = key.read_text().strip() if pub is None and key.exists() else None
    return render_template_string(
        PAGE, now=when(now), sondes=sondes, candidates=candidates, groups=groups, neuro=neuro,
        finds=finds, verdicts=verdicts, to_judge=to_judge, alerts=alerts,
        recipes=recipes, best_chart=best_chart, previews=OPUS_PREVIEWS, opus_detail=OPUS_DETAIL, pub=pub,
        deploy_key=deploy_key,
        journal_sondes=rows(SONDES_DB, "SELECT * FROM journal ORDER BY t DESC LIMIT 12"),
        journal_neuro=rows(NEURO_DB, "SELECT * FROM journal ORDER BY t DESC LIMIT 12"))


@app.route("/sondes/<int:cid>")
def campaign(cid):
    camp = rows(SONDES_DB, "SELECT * FROM campaigns WHERE id=?", (cid,))
    if not camp:
        abort(404)
    images = rows(SONDES_DB, """
        SELECT i.*, d.text FROM images i LEFT JOIN descriptions d ON d.opus_id = i.opus_id
        WHERE i.campaign_id=? AND i.rank IS NOT NULL ORDER BY i.rank LIMIT 40""", (cid,))
    flagged = scalar(SONDES_DB, "SELECT COUNT(*) FROM images WHERE campaign_id=? AND artifact IS NOT NULL", (cid,))
    total = scalar(SONDES_DB, "SELECT COUNT(*) FROM images WHERE campaign_id=?", (cid,))
    return render_template_string(CAMPAIGN, now=when(time.time()), c=camp[0], images=images, flagged=flagged,
                                  total=total, previews=OPUS_PREVIEWS, opus_detail=OPUS_DETAIL)


@app.route("/direct")
def live():
    return render_template_string(LIVE, previews=OPUS_PREVIEWS, opus_detail=OPUS_DETAIL)


@app.route("/api/direct")
def live_api():
    return jsonify(now=time.time(), neurones=direct.read("neurones"), sondes=direct.read("sondes"))


@app.route("/erreurs")
def errors():
    from . import veille  # importe ici : la surveillance n'est utile qu'a cette page
    show_all = request.args.get("tout") == "1"
    return render_template_string(
        ERRORS, now=when(time.time()), topic=veille.settings()["ntfy"], test=request.args.get("test"),
        phone=vpn.links(),
        # Par defaut : les erreurs pas encore vues ou de la semaine, et tout ce qui date de moins de 24 h.
        show_all=show_all, errors=rows(VEILLE_DB, "SELECT * FROM erreurs" + ("" if show_all else
                                       " WHERE (niveau='erreur' AND (vue=0 OR derniere > unixepoch() - 7 * 86400))"
                                       " OR derniere > unixepoch() - 86400")
                                       + " ORDER BY vue, derniere DESC LIMIT 200"))


@app.post("/erreurs/vu")
def errors_seen():
    if VEILLE_DB.exists():
        con = connect(VEILLE_DB)
        con.execute("UPDATE erreurs SET vue=1 WHERE vue=0")
        con.commit()
        con.close()
    return redirect("/erreurs")


@app.post("/erreurs/test")
def notify_test():
    from . import veille
    ok = veille.notify("Labo IA : test", "Les notifications marchent. Tu seras prévenu ici si quelque chose casse.", 3)
    return redirect(f"/erreurs?test={'ok' if ok else 'echec'}")


STYLE = """
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root { --bg:#f5f6f8; --card:#fff; --ink:#1b1f24; --muted:#5d6876; --line:#e1e5ea;
        --accent:#2f6fde; --ok:#1d8048; --warn:#a85f00; --bad:#c62f2f; --c2:#9aa4b1; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#0f1216; --card:#171b21; --ink:#e6e9ee; --muted:#95a1b0; --line:#272d36;
          --accent:#79a6ff; --ok:#52c48c; --warn:#e2a54b; --bad:#ff6b6b; --c2:#5d6876; } }
.nav { display:flex; gap:6px; flex-wrap:wrap; margin:0 0 14px; }
.nav a { padding:5px 12px; border:1px solid var(--line); border-radius:999px; background:var(--card);
         color:var(--ink); text-decoration:none; font-size:14px; }
.nav a.on { border-color:var(--accent); color:var(--accent); }
.badge { display:inline-block; min-width:20px; padding:0 6px; border-radius:999px; background:var(--bad); color:#fff;
         font-size:12px; font-weight:700; text-align:center; }
.alert { margin:10px 0 0; padding:10px 12px; border:1px solid var(--bad); border-radius:10px; color:var(--bad); }
button { font:inherit; padding:6px 12px; border-radius:8px; border:1px solid var(--line); background:var(--card);
         color:var(--ink); cursor:pointer; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
       font:15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
header, main { max-width:1240px; margin:auto; padding:0 16px; }
header { padding-top:22px; padding-bottom:10px; }
h1 { margin:0; font-size:26px; } h2 { margin:0 0 4px; font-size:20px; }
h3 { margin:22px 0 8px; font-size:13px; color:var(--muted); text-transform:uppercase; letter-spacing:.05em; }
.sub { color:var(--muted); margin:4px 0 0; }
.key { margin:8px 0 0; padding:8px 10px; border:1px solid var(--line); border-radius:8px; background:var(--card);
       font:12.5px/1.4 ui-monospace, Consolas, monospace; overflow-wrap:anywhere; user-select:all; }
main { display:grid; gap:16px; grid-template-columns:repeat(auto-fit, minmax(min(460px, 100%), 1fr));
       padding-bottom:40px; }
section { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:18px; min-width:0; }
section.wide { grid-column:1 / -1; }
.grid.finds { grid-template-columns:repeat(auto-fill, minmax(min(260px, 100%), 1fr)); }
.stats { display:grid; grid-template-columns:repeat(auto-fit, minmax(120px, 1fr)); gap:10px; margin-top:14px; }
.stat { border:1px solid var(--line); border-radius:10px; padding:10px 12px; }
.stat b { display:block; font-size:22px; font-variant-numeric:tabular-nums; }
.stat span { color:var(--muted); font-size:13px; }
.grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(150px, 1fr)); gap:10px; }
figure { margin:0; border:1px solid var(--line); border-radius:10px; overflow:hidden; }
figure img { width:100%; aspect-ratio:1; object-fit:cover; display:block; background:#000; }
figcaption { padding:6px 8px 8px; font-size:12.5px; color:var(--muted); overflow-wrap:anywhere; }
figcaption strong { color:var(--ink); }
.wrap { overflow-x:auto; }
table { width:100%; border-collapse:collapse; font-size:13.5px; }
th, td { text-align:left; padding:7px 6px; border-bottom:1px solid var(--line); vertical-align:top; }
th { color:var(--muted); font-weight:600; }
td.num { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
.pos { color:var(--ok); font-weight:600; } .neg { color:var(--warn); }
ol.journal { list-style:none; padding:0; margin:0; font-size:13.5px; }
ol.journal li { padding:7px 0; border-bottom:1px solid var(--line); }
ol.journal time { color:var(--muted); margin-right:8px; font-variant-numeric:tabular-nums; }
a { color:var(--accent); }
.note { color:var(--muted); font-size:13.5px; }
svg { width:100%; height:auto; display:block; }
svg text { fill:var(--muted); font-size:11px; }
.legend { display:flex; gap:16px; flex-wrap:wrap; font-size:13px; color:var(--muted); }
.legend i { display:inline-block; width:14px; height:3px; vertical-align:middle; margin-right:6px; border-radius:2px; }
footer { max-width:1240px; margin:auto; padding:0 16px 30px; }
</style>
"""

def nav(page):
    """Menu commun ; la pastille rouge compte les erreurs pas encore vues."""
    links = (("/", "Tableau de bord"), ("/direct", "En direct"), ("/erreurs", "Erreurs"))
    return '<nav class="nav">' + "".join(
        f'<a href="{href}"{" class=on" if href == page else ""}>{label}'
        + ('{% if unseen %} <span class="badge">{{ unseen }}</span>{% endif %}' if href == "/erreurs" else "")
        + "</a>" for href, label in links) + "</nav>"


PAGE = """<!doctype html>
<html lang="fr"><head>""" + STYLE + """
<meta http-equiv="refresh" content="60">
<title>Labo IA</title>
</head><body>
<header>
  """ + nav("/") + """
  <h1>Labo IA</h1>
  <p class="sub">Deux missions qui tournent jour et nuit sur ton Proxmox · mis à jour le {{ now }}</p>
  {% if unseen %}<p class="alert">⚠ {{ unseen }} erreur{{ "s" if unseen > 1 }} à regarder : <a href="/erreurs">voir le détail</a>.</p>{% endif %}
  {% if pub and pub.ok %}
  <p class="sub">Recherches publiées sur <a href="{{ pub.url }}" target="_blank" rel="noopener">GitHub</a> · dernière publication le {{ pub.t|when }}</p>
  {% elif pub %}
  <p class="sub">Publication GitHub en échec le {{ pub.t|when }} : {{ pub.msg }}. Nouvel essai dans l'heure.</p>
  {% elif deploy_key %}
  <p class="sub">Publication GitHub en attente : crée un dépôt public, puis ajoute-lui cette clé de déploiement
    (Settings → Deploy keys) en cochant « Allow write access ». Le labo trouvera le dépôt tout seul dans l'heure.</p>
  <p class="key">{{ deploy_key }}</p>
  {% endif %}
</header>
<main>
<section class="wide">
  <h2>Trouvailles</h2>
  <p class="sub">L'IA du labo examine une par une les photos qui sortent de l'ordinaire, et met de côté les défauts
  d'image et les choses déjà connues. Seules celles qui méritent un regard humain apparaissent ici.</p>
  <div class="stats">
    <div class="stat"><b>{{ verdicts.get("interessant", 0) }}</b><span>à regarder</span></div>
    <div class="stat"><b>{{ verdicts.get("connu", 0) }}</b><span>déjà connues ou banales</span></div>
    <div class="stat"><b>{{ verdicts.get("defaut", 0) }}</b><span>défauts d'image</span></div>
    <div class="stat"><b>{{ to_judge }}</b><span>en attente d'examen</span></div>
  </div>
  {% if finds %}
  <div class="grid finds" style="margin-top:14px">
  {% for f in finds %}
    <figure>
      <a href="{{ opus_detail }}{{ f.opus_id }}" target="_blank" rel="noopener">
        <img src="{{ previews }}{{ f.small }}" alt="{{ f.target }}, {{ f.instrument }}" loading="lazy"></a>
      <figcaption>{% if f.titre %}<strong class="pos">{{ f.titre }}</strong><br>{% endif %}
      <strong>{{ f.target }}</strong> · {{ f.instrument }} · {{ (f.time1 or "")[:10] }}<br>{{ f.text }}
      {% if f.conclusion %}<br><em>{{ f.conclusion }}</em>{% endif %}</figcaption>
    </figure>
  {% endfor %}
  </div>
  {% if pub and pub.url %}<p class="note">Dossiers complets (fiche NASA, photos d'avant et d'après, hypothèses) :
  <a href="{{ pub.url }}/tree/main/trouvailles" target="_blank" rel="noopener">page Trouvailles sur GitHub</a>.</p>{% endif %}
  {% else %}
  <p class="note">Pas encore de trouvaille. {% if to_judge %}L'IA examine les photos en ce moment (environ
  10 minutes par photo, sans carte graphique).{% else %}Rien à examiner pour l'instant.{% endif %}</p>
  {% endif %}
</section>

<section class="wide">
  <h2>Alertes {% if alerts %}<span class="badge">{{ alerts|length }}</span>{% endif %}</h2>
  {% if alerts %}
  <ol class="journal">
  {% for a in alerts %}<li><time>{{ a.derniere|when }}</time><strong class="{{ 'neg' if a.niveau == 'erreur' }}">{{ a.source }}</strong> : {{ a.titre }}{% if a.nombre > 1 %} <span class="note">({{ a.nombre }} fois)</span>{% endif %}</li>{% endfor %}
  </ol>
  <p class="note"><a href="/erreurs">Voir le détail et marquer comme vu</a></p>
  {% else %}
  <p class="note">Aucune alerte : tout tourne normalement. <a href="/erreurs">Historique</a></p>
  {% endif %}
</section>

<section>
  <h2>Sondes Fantômes</h2>
  <p class="sub">Une IA de vision compare chaque image d'archive des sondes (Voyager, Galileo, Cassini,
  New Horizons) à toutes celles de la même cible, et fait remonter les plus inhabituelles.</p>
  <div class="stats">
    <div class="stat"><b>{{ sondes.images }}</b><span>images analysées</span></div>
    <div class="stat"><b>{{ sondes.last_hour }}</b><span>dans la dernière heure</span></div>
    <div class="stat"><b>{{ sondes.done }}/{{ sondes.total }}</b><span>cibles terminées</span></div>
    <div class="stat"><b>{{ sondes.described }}</b><span>candidates décrites par l'IA</span></div>
  </div>
  {% if sondes.current %}
  <p class="note">En cours : {{ sondes.current.target }} ({{ sondes.current.instrument }}),
  {{ [sondes.current.next_start - 1, sondes.current.available or 0]|min }} / {{ sondes.current.available or "?" }} images parcourues.</p>
  {% endif %}

  <h3>Les plus étranges</h3>
  {% if candidates %}
  <div class="grid">
  {% for c in candidates %}
    <figure>
      <a href="{{ opus_detail }}{{ c.opus_id }}" target="_blank" rel="noopener">
        <img src="{{ previews }}{{ c.small }}" alt="{{ c.target }}, {{ c.instrument }}" loading="lazy"></a>
      <figcaption><strong>{{ c.target }}</strong> · n°{{ c.rank }}<br>{{ c.instrument }} · {{ (c.time1 or "")[:10] }}
      {% if c.verdict %}<br><span class="{{ 'pos' if c.verdict == 'interessant' else '' }}">{{ {"interessant": "À regarder", "connu": "Déjà connu ou banal", "defaut": "Défaut d'image"}[c.verdict] }}</span>{% endif %}
      {% if c.text %}<br>{{ c.text|truncate(180) }}{% endif %}</figcaption>
    </figure>
  {% endfor %}
  </div>
  {% else %}
  <p class="note">Pas encore de classement : il faut au moins 30 images d'une même cible pour savoir ce qui est normal.</p>
  {% endif %}

  {% if groups %}
  <h3>Cibles classées</h3>
  <div class="wrap"><table>
    <tr><th>Cible</th><th>Instrument</th><th class="num">Images</th><th>Classée le</th></tr>
    {% for g in groups %}
    <tr><td><a href="/sondes/{{ g.id }}">{{ g.target }}</a></td><td>{{ g.instrument }}</td>
        <td class="num">{{ g.n }}</td><td>{{ g.scored_at|when }}</td></tr>
    {% endfor %}
  </table></div>
  {% endif %}

  <h3>Journal</h3>
  <ol class="journal">
  {% for j in journal_sondes %}<li><time>{{ j.t|when }}</time>{{ j.msg }}</li>{% else %}<li class="note">Rien pour l'instant.</li>{% endfor %}
  </ol>
</section>

<section>
  <h2>Labo de neurones</h2>
  <p class="sub">Une culture de 1000 neurones simulés, branchée sur le SDK officiel de Cortical Labs,
  apprend à jouer à Pong. Le labo invente des protocoles d'entraînement, les teste et garde les meilleurs.</p>
  <div class="stats">
    <div class="stat"><b>{{ neuro.sessions }}</b><span>parties jouées</span></div>
    <div class="stat"><b>{{ ("%.1f" if neuro.sim_hours < 10 else "%.0f")|format(neuro.sim_hours)|replace(".", ",") }} h</b><span>de vie de culture simulée</span></div>
    <div class="stat"><b>{{ neuro.recipes }}</b><span>recettes testées</span></div>
    <div class="stat"><b class="{{ 'pos' if recipes and recipes[0].learning > 0 else '' }}">{{ recipes[0].learning|pts if recipes else "–" }}</b><span>meilleur progrès (points)</span></div>
  </div>

  {% if best_chart %}
  <h3>Balles renvoyées, minute par minute (recette n°{{ recipes[0].id }})</h3>
  <svg viewBox="0 0 {{ best_chart.w }} {{ best_chart.h }}" role="img" aria-label="Taux de balles renvoyées par minute">
    {% for g in best_chart.grid %}
    <line x1="{{ best_chart.pad }}" x2="{{ best_chart.w - best_chart.pad }}" y1="{{ g.y }}" y2="{{ g.y }}" stroke="var(--line)"/>
    <text x="{{ best_chart.pad - 4 }}" y="{{ g.y + 4 }}" text-anchor="end">{{ g.label }}</text>
    {% endfor %}
    <text x="{{ best_chart.pad }}" y="{{ best_chart.h - 8 }}">minute 1</text>
    <text x="{{ best_chart.w - best_chart.pad }}" y="{{ best_chart.h - 8 }}" text-anchor="end">minute {{ best_chart.n }}</text>
    {% for l in best_chart.lines %}
    <polyline points="{{ l.points }}" fill="none" stroke="{{ 'var(--accent)' if loop.first else 'var(--c2)' }}" stroke-width="2.5" stroke-linejoin="round"/>
    {% endfor %}
  </svg>
  <div class="legend">{% for l in best_chart.lines %}<span><i style="background:{{ 'var(--accent)' if loop.first else 'var(--c2)' }}"></i>{{ l.name }}</span>{% endfor %}</div>
  {% endif %}

  {% if recipes %}
  <h3>Meilleures recettes</h3>
  <div class="wrap"><table>
    <tr><th>n°</th><th>Protocole</th><th class="num">Début → fin</th><th class="num">Progrès</th><th class="num">Contre-épreuve</th></tr>
    {% for r in recipes %}
    <tr title="{{ r.params }}">
      <td>{{ r.id }}</td>
      <td>{{ r.mode }}<br><span class="note">{{ r.p.sens_amp }} µA · plasticité {{ r.p.stdp_tau|round|int }} ms · {{ r.origin }}</span></td>
      <td class="num">{{ "%.0f"|format(r.early * 100) }} % → {{ "%.0f"|format(r.late * 100) }} %</td>
      <td class="num {{ 'pos' if r.learning > 0 else 'neg' }}">{{ r.learning|pts }}</td>
      <td class="num">{% if r.control is not none %}{{ r.confirmed|pts }} / {{ r.control|pts }} figée{% else %}–{% endif %}</td>
    </tr>
    {% endfor %}
  </table></div>
  <p class="note">Progrès = balles renvoyées dans les 5 dernières minutes moins les 5 premières, en points.
  La contre-épreuve rejoue la recette sur des cultures neuves, avec et sans plasticité : un vrai apprentissage
  n'apparaît qu'avec.</p>
  {% endif %}

  <h3>Journal</h3>
  <ol class="journal">
  {% for j in journal_neuro %}<li><time>{{ j.t|when }}</time>{{ j.msg }}</li>{% else %}<li class="note">Rien pour l'instant.</li>{% endfor %}
  </ol>
</section>
</main>
<footer class="note">Page libre sur ton réseau local ; depuis Internet, seulement avec le lien secret (page Erreurs).
Elle se recharge toute seule chaque minute.</footer>
</body></html>
"""

CAMPAIGN = """<!doctype html>
<html lang="fr"><head>""" + STYLE + """
<title>{{ c.target }} – Sondes Fantômes</title>
</head><body>
<header>
  """ + nav("") + """
  <h1>{{ c.target }} <span class="note">· {{ c.instrument }}</span></h1>
  <p class="sub">{{ total }} images analysées, dont {{ flagged }} écartées comme ratées (noires, saturées, vides, incomplètes, striées).
  Classement du {{ c.scored_at|when if c.scored_at else "–" }} : de la plus inhabituelle à la plus banale.</p>
</header>
<main style="display:block">
<section>
  <div class="grid">
  {% for i in images %}
    <figure>
      <a href="{{ opus_detail }}{{ i.opus_id }}" target="_blank" rel="noopener">
        <img src="{{ previews }}{{ i.small }}" alt="{{ c.target }}, image n°{{ i.rank }}" loading="lazy"></a>
      <figcaption><strong>n°{{ i.rank }}</strong> · {{ (i.time1 or "")[:10] }} · score {{ "%.3f"|format(i.score) }}
      {% if i.text %}<br>{{ i.text }}{% endif %}</figcaption>
    </figure>
  {% else %}
    <p class="note">Pas encore classée.</p>
  {% endfor %}
  </div>
</section>
</main>
</body></html>
"""

LIVE = """<!doctype html>
<html lang="fr"><head>""" + STYLE + """
<title>En direct – Labo IA</title>
<style>
canvas { width:100%; display:block; border-radius:10px; background:#0b0e12; }
#chip { max-width:320px; margin:auto; }
.row { display:flex; gap:12px; flex-wrap:wrap; align-items:baseline; justify-content:space-between; }
.big { font-size:18px; font-weight:600; }
.tag { display:inline-block; padding:1px 8px; border-radius:999px; font-size:12px; border:1px solid var(--line); }
.tag.ok { color:var(--ok); border-color:var(--ok); } .tag.no { color:var(--muted); }
figure.no img { opacity:.45; filter:grayscale(1); }
.keys { display:flex; gap:14px; flex-wrap:wrap; font-size:13px; color:var(--muted); justify-content:center; margin-top:8px; }
.keys i { display:inline-block; width:12px; height:12px; border-radius:3px; margin-right:6px; vertical-align:-1px; }
</style>
</head><body>
<header>
  """ + nav("/direct") + """
  <h1>En direct</h1>
  <p class="sub">Ce que font les deux missions en ce moment. La page se met à jour toute seule.</p>
</header>
<main>
<section>
  <h2>Labo de neurones</h2>
  <p class="sub" id="n-what">En attente des neurones…</p>
  <h3>La partie de Pong</h3>
  <canvas id="pong" width="640" height="400"></canvas>
  <div class="row" style="margin-top:8px"><span class="big" id="n-score"></span><span class="note" id="n-time"></span></div>
  <p class="note">La raquette (à gauche) est pilotée uniquement par l'activité des neurones. La simulation tourne
  environ 6 fois plus vite que la réalité : la page rejoue des extraits de 10 secondes à vitesse normale.</p>
  <h3>La puce : 64 électrodes sous les neurones</h3>
  <canvas id="chip" width="320" height="320"></canvas>
  <div class="keys"><span><i style="background:#3b82f6"></i>voient la balle</span>
    <span><i style="background:#22c55e"></i>font monter la raquette</span>
    <span><i style="background:#f59e0b"></i>la font descendre</span></div>
  <p class="note">Chaque case est une électrode. Elle s'allume quand les neurones juste au-dessus s'activent.
  Le labo envoie la position de la balle aux électrodes bleues ; ce que font les zones verte et orange déplace la raquette.</p>
</section>
<section>
  <h2>Sondes Fantômes</h2>
  <p class="sub" id="s-status">En attente…</p>
  <h3>Les dernières photos regardées</h3>
  <div class="grid" id="s-grid"></div>
  <p class="note">Les photos ratées (trop sombres, vides, abîmées pendant la transmission…) sont écartées.
  Les autres sont comparées entre elles pour trouver les plus bizarres. Cliquer sur une photo ouvre sa fiche à la NASA.</p>
</section>
</main>
<script>
const PREVIEWS = {{ previews|tojson }}, DETAIL = {{ opus_detail|tojson }};
const REASONS = {"image presque uniforme": "vide", "image presque noire": "trop sombre", "image saturee": "trop claire",
  "image incomplete": "incomplète", "image striee": "striée", "image dominee par le bruit": "parasites"};
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const $ = id => document.getElementById(id);
let latest = null, clip = null, frame = 0, lastSondes = null, level = new Float32Array(64), flash = 0, flashColor = "";

function ago(s) { return s < 90 ? Math.round(s) + " s" : Math.round(s / 60) + " min"; }

async function poll() {
  try {
    const d = await (await fetch("/api/direct", {cache: "no-store"})).json();
    latest = d.neurones ? {...d.neurones, age: d.now - d.neurones.t} : null;
    showSondes(d.sondes, d.now);
  } catch (e) { $("n-what").textContent = "Tableau de bord injoignable…"; }
}

function showSondes(s, now) {
  if (!s) return;
  const age = now - s.t;
  $("s-status").textContent = (s.status || "") + (age > 900 ? " (pas de nouvelles depuis " + ago(age) + " : voir la page Erreurs)" : "");
  const key = s.recent.length ? s.recent[0].opus_id : "";
  if (key === lastSondes) return;
  lastSondes = key;
  $("s-grid").innerHTML = s.recent.map(r => {
    const no = r.reason ? " class=no" : "";
    const tag = r.reason ? '<span class="tag no">écartée : ' + esc(REASONS[r.reason] || r.reason) + "</span>"
                         : '<span class="tag ok">gardée</span>';
    return "<figure" + no + '><a href="' + esc(DETAIL + r.opus_id) + '" target="_blank" rel="noopener"><img src="'
      + esc(PREVIEWS + r.small) + '" alt=""></a><figcaption>' + tag + "<br>" + esc((r.time1 || "").slice(0, 10)) + "</figcaption></figure>";
  }).join("");
}

function startClip() {
  if (!latest || !latest.frames || !latest.frames.length || (clip && latest.t === clip.t)) return false;
  clip = latest; frame = 0;
  const who = clip.plastic ? "neurones capables d'apprendre" : "neurones figés, incapables d'apprendre (vérification)";
  $("n-what").innerHTML = "<strong>" + esc(clip.what) + "</strong> · culture n°" + esc(clip.seed) + ", " + who
    + "<br>Recette : " + esc(clip.recipe);
  return true;
}

function drawPong(f) {
  const c = $("pong"), g = c.getContext("2d"), W = c.width, H = c.height;
  const [x, y, paddle, event, pause] = f;
  if (event) { flash = 12; flashColor = event === 1 ? "34,197,94" : "239,68,68"; }
  g.fillStyle = "#0b0e12"; g.fillRect(0, 0, W, H);
  if (flash > 0) { g.fillStyle = "rgba(" + flashColor + "," + (flash / 40) + ")"; g.fillRect(0, 0, W, H); flash--; }
  g.fillStyle = "#2a313b"; g.fillRect(W - 8, 0, 8, H);
  g.setLineDash([6, 10]); g.strokeStyle = "#2a313b"; g.beginPath(); g.moveTo(W / 2, 0); g.lineTo(W / 2, H); g.stroke(); g.setLineDash([]);
  g.fillStyle = "#e6e9ee"; const ph = 0.25 * H; g.fillRect(10, paddle * H - ph / 2, 10, ph);
  if (!pause) { g.beginPath(); g.arc(24 + x * (W - 40), 8 + y * (H - 16), 8, 0, 7); g.fill(); }
  g.font = "16px system-ui"; g.textAlign = "center";
  if (clip.sim_t < 0) { g.fillStyle = "#95a1b0"; g.fillText("Échauffement : la culture vit seule avant la partie", W / 2, 30); }
  else if (pause) { g.fillStyle = "#ef4444"; g.fillText("Balle ratée : petite pause avant la suivante", W / 2, 30); }
}

function drawChip(f) {
  const c = $("chip"), g = c.getContext("2d"), n = 8, s = c.width / n, act = f[5];
  const color = ch => clip.sensory.includes(ch) ? [59,130,246] : clip.up.includes(ch) ? [34,197,94] : clip.down.includes(ch) ? [245,158,11] : [120,130,145];
  g.fillStyle = "#0b0e12"; g.fillRect(0, 0, c.width, c.height);
  for (let ch = 0; ch < 64; ch++) {
    level[ch] = Math.max(level[ch] * 0.85, Math.min(+act[ch] / 3, 1));
    const [r, gg, b] = color(ch), cx = (ch % n) * s, cy = Math.floor(ch / n) * s;
    g.fillStyle = "rgba(" + r + "," + gg + "," + b + "," + (0.18 + 0.82 * level[ch]) + ")";
    g.beginPath(); g.roundRect(cx + 4, cy + 4, s - 8, s - 8, 6); g.fill();
  }
}

function tick() {
  if ((!clip || frame >= clip.frames.length) && !startClip()) {
    if (clip) $("n-time").textContent = latest && latest.age > 120 ? "Pas de nouvelles depuis " + ago(latest.age) + " : voir la page Erreurs" : "Chargement de l'extrait suivant…";
    return;
  }
  const f = clip.frames[frame++];
  drawPong(f); drawChip(f);
  const minute = Math.max(0, Math.floor(clip.sim_t / 60) + 1);
  $("n-score").textContent = clip.hits + " balles renvoyées, " + clip.misses + " ratées";
  $("n-time").textContent = clip.sim_t < 0 ? "échauffement" : "minute " + Math.min(minute, 15) + " sur 15";
}

poll(); setInterval(poll, 2000); setInterval(tick, 50);
</script>
</body></html>
"""

ERRORS = """<!doctype html>
<html lang="fr"><head>""" + STYLE + """
<meta http-equiv="refresh" content="120">
<title>Erreurs – Labo IA</title>
<style>
.err { border:1px solid var(--line); border-radius:10px; padding:12px 14px; margin:0 0 10px; }
.err.new { border-color:var(--bad); }
.big { font-size:16px; margin:2px 0; }
.lvl { font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; }
.lvl.erreur { color:var(--bad); } .lvl.avertissement { color:var(--warn); } .lvl.vue { color:var(--muted); }
pre { margin:8px 0 0; padding:10px; border-radius:8px; background:var(--bg); border:1px solid var(--line);
      font:12.5px/1.45 ui-monospace, Consolas, monospace; overflow:auto; max-height:420px; white-space:pre; }
code { font:13px ui-monospace, Consolas, monospace; padding:1px 6px; border:1px solid var(--line); border-radius:6px;
       user-select:all; overflow-wrap:anywhere; }
ol.steps { margin:6px 0 10px; padding-left:20px; }
</style>
</head><body>
<header>
  """ + nav("/erreurs") + """
  <h1>Erreurs et alertes</h1>
  <p class="sub">Le labo se surveille tout seul toutes les 5 minutes : plantages, services arrêtés, mission bloquée,
  publication en échec, disque plein. Page mise à jour le {{ now }}.</p>
</header>
<main style="display:block">
<section style="margin-bottom:16px">
  <h2>Voir le labo depuis ton téléphone</h2>
  <p class="note">Le labo passe par un VPN privé (Tailscale) : rien n'est ouvert sur Internet, seuls tes appareils
  le voient. Installe l'appli <b>Tailscale</b> sur ton téléphone, connecte-toi avec le même compte que le labo, puis
  ouvre cette adresse (de partout, même en 4G) :</p>
  {% if phone %}
  <p>{% if phone.nom %}<code>{{ phone.nom }}</code> ou {% endif %}<code>{{ phone.ip }}</code></p>
  {% else %}
  <p class="note">Le labo n'est pas encore relié au VPN.</p>
  {% endif %}
</section>
<section style="margin-bottom:16px">
  <h2>Recevoir les alertes sur ton téléphone</h2>
  <ol class="steps">
    <li>Installe l'application gratuite <b>ntfy</b> (Play Store, App Store ou F-Droid). Pas de compte à créer.</li>
    <li>Dans l'appli, appuie sur <b>+</b> et abonne-toi au sujet <code>{{ topic }}</code> (serveur par défaut, ntfy.sh).</li>
    <li>Appuie ici pour vérifier que ça marche :</li>
  </ol>
  <form method="post" action="/erreurs/test"><button>Envoyer une notification de test</button></form>
  {% if test == "ok" %}<p class="note" style="color:var(--ok)">Notification envoyée : elle doit arriver sur ton téléphone dans quelques secondes.</p>
  {% elif test %}<p class="alert">L'envoi a échoué (pas d'accès à Internet ?). Réessaie dans un moment.</p>{% endif %}
  <p class="note">Garde ce nom de sujet pour toi : toute personne qui le connaît peut lire les alertes. Elles ne contiennent
  que des messages d'erreur du labo, rien de personnel.</p>
</section>
<section>
  <div class="row" style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;align-items:center">
    <h2>{{ "Tout l'historique" if show_all else "Problèmes récents" }}</h2>
    <span>
    {% if unseen %}<form method="post" action="/erreurs/vu" style="display:inline"><button>Tout marquer comme vu</button></form>{% endif %}
    <a href="/erreurs{{ '' if show_all else '?tout=1' }}" class="note">{{ "Voir seulement les récents" if show_all else "Voir tout l'historique" }}</a>
    </span>
  </div>
  {% for e in errors %}
  <div class="err {{ 'new' if not e.vue and e.niveau == 'erreur' }}">
    <span class="lvl {{ 'vue' if e.vue else e.niveau }}">{{ e.niveau }}{{ " · vue" if e.vue }}</span>
    <div class="big"><strong>{{ e.source }}</strong> : {{ e.titre }}</div>
    <div class="note">{% if e.nombre > 1 %}{{ e.nombre }} fois, du {{ e.premiere|when }} au {{ e.derniere|when }}{% else %}le {{ e.premiere|when }}{% endif %}</div>
    {% if e.detail %}<details><summary class="note">Voir le détail technique</summary><pre>{{ e.detail }}</pre></details>{% endif %}
  </div>
  {% else %}
  <p class="note">Aucun problème : tout tourne normalement.</p>
  {% endfor %}
  <p class="note">Une <b>erreur</b> déclenche une notification (une seule fois tant que tu ne l'as pas marquée comme vue).
  Un <b>avertissement</b> est un petit souci passager, comme une photo qui n'a pas pu être téléchargée : il est
  seulement noté ici.</p>
</section>
</main>
</body></html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True)
