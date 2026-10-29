"""Tableau de bord du labo, sur le port 8080 (reseau local uniquement, sans mot de passe)."""
import json
import time

from flask import Flask, abort, render_template_string

from .config import DEPLOY_KEY, FEEDBACK_MODES, NEURO_DB, OPUS_PREVIEWS, PUBLICATION_STATUS, SONDES_DB
from .db import rows, scalar

app = Flask(__name__)
OPUS_DETAIL = "https://opus.pds-rings.seti.org/opus/#/view=detail&detail="


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
        SELECT i.*, c.instrument, c.target, d.text FROM images i
        JOIN campaigns c ON c.id = i.campaign_id LEFT JOIN descriptions d ON d.opus_id = i.opus_id
        WHERE i.rank <= 3 ORDER BY c.scored_at DESC, c.id, i.rank LIMIT 24""")
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


STYLE = """
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root { --bg:#f5f6f8; --card:#fff; --ink:#1b1f24; --muted:#5d6876; --line:#e1e5ea;
        --accent:#2f6fde; --ok:#1d8048; --warn:#a85f00; --c2:#9aa4b1; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#0f1216; --card:#171b21; --ink:#e6e9ee; --muted:#95a1b0; --line:#272d36;
          --accent:#79a6ff; --ok:#52c48c; --warn:#e2a54b; --c2:#5d6876; } }
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

PAGE = """<!doctype html>
<html lang="fr"><head>""" + STYLE + """
<meta http-equiv="refresh" content="60">
<title>Labo IA</title>
</head><body>
<header>
  <h1>Labo IA</h1>
  <p class="sub">Deux missions qui tournent jour et nuit sur ton Proxmox · mis à jour le {{ now }}</p>
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
<footer class="note">Page visible seulement sur ton réseau local. Elle se recharge toute seule chaque minute.</footer>
</body></html>
"""

CAMPAIGN = """<!doctype html>
<html lang="fr"><head>""" + STYLE + """
<title>{{ c.target }} – Sondes Fantômes</title>
</head><body>
<header>
  <p><a href="/">← Labo IA</a></p>
  <h1>{{ c.target }} <span class="note">· {{ c.instrument }}</span></h1>
  <p class="sub">{{ total }} images analysées, dont {{ flagged }} écartées comme ratées (noires, saturées, uniformes).
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True)
