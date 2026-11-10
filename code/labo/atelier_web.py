"""Galerie et controles de l'atelier ; seuls les artefacts valides sont servis."""
import secrets
import time
from urllib.parse import urlsplit

from flask import Blueprint, abort, jsonify, redirect, render_template_string, request, send_file

from . import atelier, direct
from .config import ATELIER_DIR, ATELIER_MODEL

bp = Blueprint('atelier', __name__)
# Jeton propre au processus, exige aussi sur le reseau local ; jamais dans une URL.
TOKEN = secrets.token_urlsafe(32)


def context():
    state = direct.read('atelier') or {}
    age = time.time()-state.get('t', 0)
    page = max(1, min(200, request.args.get('page', 1, type=int)))
    return dict(projects=atelier.list_projects(offset=(page-1)*30), page=page, state=state, stale=age>90,
                paused=atelier.setting('paused', '0') == '1', phases=atelier.PHASES,
                next_at=float(atelier.setting('next_at', '0')), model=ATELIER_MODEL, token=TOKEN)


@bp.get('/atelier')
def gallery():
    from .web import STYLE, nav
    return render_template_string(PAGE, style=STYLE, nav=render_template_string(nav('/atelier')), journal=atelier.events(), **context())


@bp.get('/api/atelier')
def api():
    data = context()
    data.pop('token')
    return jsonify(data)


@bp.post('/atelier/control')
def control():
    if not secrets.compare_digest(request.form.get('token', '').encode('utf-8'), TOKEN.encode('utf-8')): abort(403)
    origin = request.headers.get('Origin')
    if origin and urlsplit(origin).netloc != request.host: abort(403)
    action = request.form.get('action')
    if action == 'pause': atelier.set_setting('paused', '1')
    elif action == 'resume': atelier.set_setting('paused', '0')
    elif action == 'next':
        atelier.set_setting('request_next', '1')
        atelier.set_setting('next_at', '0')
        atelier.set_setting('paused', '0')
    else: abort(400)
    return redirect('/atelier', code=303)


@bp.get('/atelier/<pid>')
def detail(pid):
    from .web import STYLE, nav
    p = atelier.get_project(pid)
    if not p: abort(404)
    return render_template_string(DETAIL, style=STYLE, nav=render_template_string(nav('/atelier')), p=p,
                                  journal=atelier.events(pid), phases=atelier.PHASES)


@bp.get('/atelier/<pid>/<kind>')
def artifact(pid, kind):
    p = atelier.get_project(pid)
    if not p or p['phase'] != 'published': abort(404)
    names = {'app': 'index.html', 'download': 'prototype.zip', 'validation': 'validation.json'}
    if kind not in names: abort(404)
    path = ATELIER_DIR / 'releases' / p['id'] / names[kind]
    if not path.is_file(): abort(404)
    response = send_file(path, as_attachment=kind != 'app', download_name=names[kind])
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    if kind == 'app':
        response.headers['Content-Security-Policy'] = ("sandbox allow-scripts allow-downloads; default-src 'none'; "
            "script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; "
            "base-uri 'none'; form-action 'none'; frame-ancestors 'self'")
    return response


PAGE = '''<!doctype html><html lang="fr"><head>{{ style|safe }}
<title>Atelier du futur · Labo IA</title><meta http-equiv="refresh" content="45">
<style>.hero{background:linear-gradient(125deg,#142b43,#174a49);color:#eef9ff;border-radius:18px;padding:28px;margin:10px 0 20px}.hero p{color:#c9dce8;max-width:760px}.tag{font-size:12px;text-transform:uppercase;letter-spacing:.12em;color:#83e6ca}.flow{display:flex;gap:8px;flex-wrap:wrap;margin-top:18px}.flow span{border:1px solid #7894a2;border-radius:20px;padding:5px 12px;font-size:13px}.project-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(330px,100%),1fr));gap:16px}.project-card{display:flex;flex-direction:column;gap:12px}.project-card h2{font-size:20px}.project-card .links{margin-top:auto;display:flex;gap:16px;flex-wrap:wrap}.state{font-size:13px;font-weight:600;color:var(--accent)}.toolbar{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0}.toolbar form{display:inline}.mono{font-variant-numeric:tabular-nums}</style></head><body>
<header>{{ nav|safe }}<div class="hero"><div class="tag">Mission 03 / imagination appliquée</div><h1>Atelier du futur</h1><p>Une IA imagine des projets, construit des simulateurs interactifs et les soumet à des tests et à sa propre critique. Explore les prototypes retenus ou suis leur fabrication.</p><div class="flow"><span>1 · Concevoir</span><span>2 · Tester</span><span>3 · Critiquer</span><span>4 · Améliorer</span><span>5 · Publier</span></div></div></header>
<main><section class="wide"><div class="state">{{ 'PAUSE DEMANDÉE' if paused else 'ATELIER AUTONOME' }} · {{ model }}</div><h2>{{ state.message or 'Initialisation de la mission…' }}</h2>
{% if state.activity == 'waiting' %}<p class='note'>En file d’attente : une autre mission utilise le modèle.</p>{% elif state.activity == 'reasoning' %}<p class='note'>Examen raisonné des calculs en cours. Le verdict apparaîtra à la fin de la vérification.</p>{% elif state.activity == 'generating' %}<p class='note'>Génération en cours · {{ state.characters or 0 }} caractères reçus. Le calcul continue même si cette page est fermée.</p>{% endif %}
{% if stale %}<p class="alert">Le suivi n’a pas été actualisé depuis plus de 90 secondes. Consulter l’état des services.</p>{% endif %}
{% if paused %}<p class="note">La requête déjà en cours peut se terminer ; aucune publication ni nouvelle étape ne démarre pendant la pause.</p>{% elif next_at and state.status == 'idle' %}<p>Prochain cycle : <time class="localtime" data-epoch="{{ next_at }}">{{ next_at|when }} (serveur)</time></p>{% endif %}
<div class="toolbar"><form method="post" action="/atelier/control"><input type="hidden" name="token" value="{{ token }}"><button name="action" value="{{ 'resume' if paused else 'pause' }}">{{ 'Reprendre' if paused else 'Mettre en pause' }}</button></form><form method="post" action="/atelier/control"><input type="hidden" name="token" value="{{ token }}"><button name="action" value="next">Demander le prochain projet</button></form><a href="/direct">Santé du labo →</a></div>
<p class="note">Le travail en cours est conservé. Nouveau sujet une heure après chaque cycle terminé, avec jusqu’à trois révisions. Les autres missions gardent accès au modèle entre les étapes.</p></section>
<div class="wide project-grid" style="grid-column:1/-1">{% for p in projects %}<section class="project-card"><div class="state">{{ phases[p.phase] }} · révision {{ p.revision }}{% if p.review %} · autocritique {{ p.review.score }}/10{% endif %}</div><h2>{{ p.title }}</h2><p class="sub">{{ p.spec.summary if p.spec and p.spec.summary else p.topic }}</p>{% if p.tests and p.tests.passed %}<div class="note">{{ p.tests.cases }} scénarios de calcul testés</div>{% endif %}<div class="links"><a href="/atelier/{{ p.id }}">Journal et validation</a>{% if p.phase == 'published' %}<a href="/atelier/{{ p.id }}/app">Utiliser →</a><a href="/atelier/{{ p.id }}/download">Télécharger ZIP</a>{% endif %}</div></section>{% else %}<section><h2>La première idée se prépare</h2><p>Les propositions apparaîtront ici. Le premier calcul sur CPU peut prendre plusieurs dizaines de minutes.</p></section>{% endfor %}</div>
<div style="grid-column:1/-1;display:flex;gap:18px">{% if page > 1 %}<a href="/atelier?page={{ page-1 }}">Projets plus récents</a>{% endif %}{% if projects|length == 30 %}<a href="/atelier?page={{ page+1 }}">Projets plus anciens</a>{% endif %}</div><section><h2>Journal de l’atelier</h2><ol class="journal">{% for e in journal %}<li><time class="localtime" data-epoch="{{ e.t }}">{{ e.t|when }}</time>{{ e.message }}</li>{% else %}<li>En attente du premier cycle.</li>{% endfor %}</ol></section><section><h2>Ce que signifie « disponible »</h2><p>Les formules passent les tests numériques, les commandes ont un effet et l’autocritique atteint au moins 8/10 sans point bloquant.</p><p>Les projets sont des modèles exploratoires : aucune perfection, nouveauté scientifique ou faisabilité industrielle n’est garantie. Chaque téléchargement contient les hypothèses, les limites et le rapport de validation.</p><p class="note">Cette version explore huit familles de sujets (espace, énergie, habitat, eau…). Elle conçoit localement : elle n’effectue pas de veille scientifique sur Internet. Le modèle définit le projet et ses équations ; un moteur vérifié construit l’application.</p></section></main><script>document.querySelectorAll('.localtime').forEach(e=>e.textContent=new Date(Number(e.dataset.epoch)*1000).toLocaleString('fr-FR'));</script></body></html>'''


DETAIL = '''<!doctype html><html lang="fr"><head>{{ style|safe }}<title>{{ p.title }} · Atelier</title></head><body><header>{{ nav|safe }}<p><a href="/atelier">← Tous les projets</a></p><h1>{{ p.title }}</h1><p class="sub">{{ phases[p.phase] }} · révision {{ p.revision }}</p></header><main>
{% if p.phase == 'published' %}<section class="wide"><h2>Prototype disponible</h2><p><a href="/atelier/{{ p.id }}/app">Ouvrir l’application</a> · <a href="/atelier/{{ p.id }}/download">Télécharger le ZIP autonome</a> · <a href="/atelier/{{ p.id }}/validation">Rapport JSON</a></p><iframe src="/atelier/{{ p.id }}/app" title="{{ p.title }}" sandbox="allow-scripts allow-downloads" style="width:100%;height:720px;border:1px solid var(--line);border-radius:12px"></iframe></section>{% endif %}
{% if p.spec %}<section><h2>Intention du projet</h2><p>{{ p.spec.summary }}</p><p>{{ p.spec.hypothesis }}</p><h3>Hypothèses</h3><ul>{% for a in p.spec.assumptions or [] %}<li>{{ a }}</li>{% endfor %}</ul><h3>Limites</h3><ul>{% for a in p.spec.limitations or [] %}<li>{{ a }}</li>{% endfor %}</ul></section>{% endif %}
<section><h2>Validation</h2>{% if p.tests %}<p>{{ p.tests.cases }} scénarios de calcul vérifiés.</p><ul>{% for t in p.tests.checks %}<li>{{ t }}</li>{% endfor %}</ul><p class="note">{{ p.tests.scope }}</p>{% else %}<p>Tests non terminés.</p>{% endif %}{% if p.error %}<p class="alert">{{ p.error }}</p>{% endif %}
{% if p.review %}<h3>Autocritique · {{ p.review.score }}/10</h3><p>{{ p.review.reason }}</p><h3>Points bloquants</h3><ul>{% for b in p.review.blockers %}<li>{{ b }}</li>{% else %}<li>Aucun point bloquant signalé par le modèle.</li>{% endfor %}</ul><h3>Améliorations proposées</h3><ul>{% for b in p.review.improvements %}<li>{{ b }}</li>{% else %}<li>Aucune.</li>{% endfor %}</ul>{% endif %}</section>
<section class="wide"><h2>Journal de conception</h2><ol class="journal">{% for e in journal %}<li><time>{{ e.t|when }}</time>{{ e.message }}</li>{% endfor %}</ol></section></main></body></html>'''
