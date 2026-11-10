import html
import io
import json
from pathlib import Path
import secrets
import time
from urllib.parse import urlsplit
import zipfile
from flask import Blueprint,abort,jsonify,redirect,render_template_string,request,send_file,Response
from . import explorations,experiments,direct

bp=Blueprint('explorations',__name__)
TOKEN=secrets.token_urlsafe(32)


def render(payload):
    template=Path(__file__).with_name('experiment.html').read_text(encoding='utf-8')
    data=json.dumps(payload,ensure_ascii=False,allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    return template.replace('__TITLE__',html.escape(payload['title'])).replace('__DATA__',data)


def context():
    state=direct.read('explorations') or {}
    return dict(missions=explorations.latest(),state=state,stale=time.time()-state.get('t',0)>90,
                paused=explorations.setting('paused')=='1')


@bp.get('/explorations')
def gallery():
    from .web import STYLE,nav
    return render_template_string(PAGE,style=STYLE,nav=render_template_string(nav('/explorations')),token=TOKEN,**context())


@bp.get('/api/explorations')
def api(): return jsonify(context())


@bp.post('/explorations/control')
def control():
    if not secrets.compare_digest(request.form.get('token','').encode(),TOKEN.encode()): abort(403)
    origin=request.headers.get('Origin')
    if origin and urlsplit(origin).netloc!=request.host: abort(403)
    action=request.form.get('action')
    if action in ('pause','resume'): explorations.set_setting('paused','1' if action=='pause' else '0')
    elif action=='run':
        kind=request.form.get('kind')
        if kind not in experiments.CATALOG: abort(400)
        explorations.enqueue(kind)
    else: abort(400)
    return redirect('/explorations',code=303)


@bp.get('/explorations/<kind>')
def detail(kind):
    from .web import STYLE,nav
    if kind not in experiments.CATALOG: abort(404)
    run=explorations.get_run(kind,request.args.get('run'))
    if not run: abort(404)
    return render_template_string(DETAIL,style=STYLE,nav=render_template_string(nav('/explorations')),run=run,
                                  history=explorations.history(kind),kind=kind)


@bp.get('/explorations/<kind>/<artifact>')
def download(kind,artifact):
    if kind not in experiments.CATALOG or artifact not in ('app','json','zip'): abort(404)
    run=explorations.get_run(kind,request.args.get('run'))
    if not run: abort(404)
    payload=run['payload']
    if artifact=='app':
        response=Response(render(payload),mimetype='text/html')
        response.headers['Content-Security-Policy']="sandbox allow-scripts allow-downloads; default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
    elif artifact=='json':
        response=send_file(io.BytesIO(json.dumps(run,ensure_ascii=False,indent=2).encode()),mimetype='application/json',as_attachment=True,download_name=kind+'-'+run['id']+'.json')
    else:
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('index.html',render(payload))
            archive.writestr('resultats.json',json.dumps(run,ensure_ascii=False,indent=2))
            archive.writestr('README.txt','Ouvrir index.html sans installation ni connexion.\n'+payload['origin']+'\nMethode : '+payload['method']+'\nLimites : '+payload['limits'])
        buffer.seek(0)
        response=send_file(buffer,mimetype='application/zip',as_attachment=True,download_name=kind+'-'+run['id']+'.zip')
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    return response


PAGE='''<!doctype html><html lang="fr"><head>{{ style|safe }}<title>Explorations · Labo IA</title><meta http-equiv="refresh" content="30">
<style>.hero{background:linear-gradient(120deg,#25365e,#263b42);padding:30px;border-radius:18px;color:#eef6ff;margin:12px 0 20px}.hero p{color:#c2d2e5;max-width:820px}.eyebrow{font-size:12px;text-transform:uppercase;letter-spacing:.14em;color:#9be5d1}.missions{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(340px,100%),1fr));gap:18px;grid-column:1/-1}.mission{display:flex;flex-direction:column;gap:12px}.mission h2{font-size:23px}.mission .links{margin-top:auto;display:flex;gap:15px;flex-wrap:wrap}.symbol{font-size:32px;color:var(--accent)}.smallmetrics{display:grid;grid-template-columns:1fr 1fr;gap:10px}.smallmetrics div{border:1px solid var(--line);padding:12px;border-radius:10px}.smallmetrics b{display:block;font-size:22px}.smallmetrics span{font-size:12px;color:var(--muted)}.statusrow{display:flex;justify-content:space-between;gap:16px;align-items:center;flex-wrap:wrap}</style></head><body><header>{{ nav|safe }}<div class="hero"><div class="eyebrow">Six terrains d’expérimentation</div><h1>Explorations autonomes</h1><p>Des robots qui se coordonnent, des pilotes qui évoluent, des signaux cachés et des mondes cellulaires. Le labo calcule, compare et conserve des expériences que tu peux rejouer.</p></div></header><main>
<section class="wide"><div class="statusrow"><div><h2>{{ 'Explorations en pause' if paused else state.message or 'Préparation des premières expériences…' }}</h2><p class="note">Une nouvelle expérience toutes les dix minutes, en alternant les six missions. Les résultats restent disponibles après fermeture du site.</p></div><form action="/explorations/control" method="post"><input type="hidden" name="token" value="{{ token }}"><button name="action" value="{{ 'resume' if paused else 'pause' }}">{{ 'Reprendre' if paused else 'Mettre en pause' }}</button></form></div>{% if stale %}<p class="alert">Le suivi n’a pas été actualisé depuis plus de 90 secondes.</p>{% endif %}{% if paused %}<p class="note">Le calcul déjà commencé peut se terminer. Reprendre pour traiter les expériences demandées.</p>{% endif %}</section>
<div class="missions">{% for m in missions %}<section class="mission"><div class="eyebrow" style="color:var(--accent)">Mission {{ loop.index }} / {{ 'résultat disponible' if m.run else 'en préparation' }}</div><h2>{{ m.title }}</h2><p class="sub">{{ m.summary }}</p>{% if m.run %}<div class="smallmetrics">{% for metric in m.metrics[:2] %}<div><span>{{ metric.label }}</span><b>{{ metric.value }} <small>{{ metric.unit }}</small></b></div>{% endfor %}</div><p class="note">Calcul du {{ m.run.created|when }} · graine {{ m.run.seed }} · {{ '%.1f'|format(m.run.duration) }} s</p>{% endif %}<div class="links">{% if m.run %}<a href="/explorations/{{ m.kind }}">Explorer →</a><a href="/explorations/{{ m.kind }}/zip?run={{ m.run.id }}">ZIP hors ligne</a>{% endif %}<form method="post" action="/explorations/control"><input type="hidden" name="token" value="{{ token }}"><input type="hidden" name="kind" value="{{ m.kind }}"><button name="action" value="run">Nouvelle expérience</button></form></div></section>{% endfor %}</div>
<section class="wide"><h2>Des expériences, pas des annonces de découverte</h2><p>Ces missions utilisent des algorithmes de recherche, d’évolution, de détection et d’optimisation sur des données simulées. Les méthodes sont indiquées dans chaque résultat. Qwen poursuit séparément la conception et l’autocritique dans <a href="/atelier">l’Atelier du futur</a>.</p><p class="note">Chaque résultat conserve sa graine aléatoire et ses mesures. Les visualisations ne sont pas des vidéos inventées : elles rejouent les états calculés.</p></section></main></body></html>'''

DETAIL='''<!doctype html><html lang="fr"><head>{{ style|safe }}<title>{{ run.payload.title }} · Explorations</title></head><body><header>{{ nav|safe }}<p><a href="/explorations">← Les six missions</a></p><h1>{{ run.payload.title }}</h1><p>Expérience du {{ run.created|when }} · <a href="/explorations/{{ kind }}/zip?run={{ run.id }}">Télécharger le ZIP</a> · <a href="/explorations/{{ kind }}/json?run={{ run.id }}">Données JSON</a> · <a href="/explorations/{{ kind }}/app?run={{ run.id }}">Plein écran</a></p></header><main><section class="wide" style="padding:0;overflow:hidden"><iframe src="/explorations/{{ kind }}/app?run={{ run.id }}" title="{{ run.payload.title }}" sandbox="allow-scripts allow-downloads" style="width:100%;height:1100px;border:0"></iframe></section><section class="wide"><h2>Expériences précédentes</h2><ol class="journal">{% for item in history %}<li><a href="/explorations/{{ kind }}?run={{ item.id }}">{{ item.created|when }}</a> · graine {{ item.seed }} · {{ '%.1f'|format(item.duration) }} s</li>{% endfor %}</ol></section></main></body></html>'''
