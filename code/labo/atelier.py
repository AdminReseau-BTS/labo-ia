"""Atelier autonome : concevoir, tester, critiquer, reviser, publier des prototypes."""
import fcntl
import hashlib
import json
import logging
import os
import shutil
import sqlite3
import threading
import time
import uuid
import zipfile
from contextlib import contextmanager

from . import direct, llm, prototype, foundations
from .config import ATELIER_DIR, ATELIER_MODEL, LOG_FORMAT

log = logging.getLogger('atelier')
TOPICS = ['habitat lunaire et recyclage de l’eau', 'microreseau solaire et stockage pour une ville autonome',
          'serre martienne et autonomie alimentaire', 'refroidissement passif de villes futures',
          'voile solaire et exploration spatiale', 'recuperation de chaleur dans un habitat sous-marin',
          'recyclage de materiaux pour une station orbitale', 'ferme verticale et sobriete energetique']
PHASES = {'design': 'Conception', 'review': 'Autocritique', 'revise': 'Amélioration',
          'published': 'Disponible', 'rejected': 'À reprendre'}
INTERVAL = 3600
_progress = None
SPEC_SCHEMA = {'type': 'object', 'properties': {
    'title': {'type': 'string'}, 'summary': {'type': 'string'}, 'hypothesis': {'type': 'string'},
    'assumptions': {'type': 'array', 'items': {'type': 'string'}},
    'limitations': {'type': 'array', 'items': {'type': 'string'}},
    'parameters': {'type': 'array', 'items': {'type': 'object', 'properties': {
        'id': {'type': 'string'}, 'label': {'type': 'string'}, 'unit': {'type': 'string'},
        'min': {'type': 'number'}, 'max': {'type': 'number'}, 'default': {'type': 'number'}},
        'required': ['id', 'label', 'unit', 'min', 'max', 'default'], 'additionalProperties': False}},
    'metrics': {'type': 'array', 'items': {'type': 'object', 'properties': {
        'label': {'type': 'string'}, 'unit': {'type': 'string'}, 'formula': {'type': 'string'},
        'explanation': {'type': 'string'}}, 'required': ['label', 'unit', 'formula', 'explanation'], 'additionalProperties': False}}
}, 'required': ['title', 'summary', 'hypothesis', 'assumptions', 'limitations', 'parameters', 'metrics'], 'additionalProperties': False}
REVIEW_SCHEMA = {'type': 'object', 'properties': {
    'score': {'type': 'integer'}, 'verdict': {'type': 'string', 'enum': ['publish', 'revise']},
    'strengths': {'type': 'array', 'items': {'type': 'string'}},
    'blockers': {'type': 'array', 'items': {'type': 'string'}},
    'improvements': {'type': 'array', 'items': {'type': 'string'}},
    'reason': {'type': 'string'}}, 'required': ['score', 'verdict', 'strengths', 'blockers', 'improvements', 'reason'],
    'additionalProperties': False}

# Les contraintes envoyees au modele doivent correspondre au validateur reel.
for key in ('assumptions', 'limitations'):
    SPEC_SCHEMA['properties'][key].update(minItems=2,maxItems=4)
SPEC_SCHEMA['properties']['parameters'].update(minItems=2,maxItems=3)
SPEC_SCHEMA['properties']['metrics'].update(minItems=2,maxItems=2)
SPEC_SCHEMA['properties']['parameters']['items']['properties']['id'].update(pattern='^[a-z][a-z0-9_]{0,63}$',maxLength=64)


@contextmanager
def database():
    ATELIER_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ATELIER_DIR / 'atelier.db', timeout=15)
    con.row_factory = sqlite3.Row
    try:
        con.executescript('''CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY, topic TEXT NOT NULL, title TEXT NOT NULL, phase TEXT NOT NULL,
            created REAL NOT NULL, updated REAL NOT NULL, revision INTEGER DEFAULT 0,
            attempts INTEGER DEFAULT 0, spec TEXT, review TEXT, tests TEXT, error TEXT);
            CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, project TEXT, t REAL, message TEXT);
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS versions (id INTEGER PRIMARY KEY, project TEXT, t REAL, snapshot TEXT);
            CREATE INDEX IF NOT EXISTS events_project ON events(project,id);''')
        yield con
        con.commit()
    finally:
        con.close()


def unpack(row):
    if row is None: return None
    item = dict(row)
    for key in ('spec', 'review', 'tests'):
        if item.get(key): item[key] = json.loads(item[key])
    return item


def list_projects(limit=30, offset=0):
    with database() as con:
        return [unpack(r) for r in con.execute('SELECT * FROM projects ORDER BY created DESC LIMIT ? OFFSET ?', (limit, offset))]


def get_project(pid):
    with database() as con:
        return unpack(con.execute('SELECT * FROM projects WHERE id=?', (pid,)).fetchone())


def events(pid=None):
    with database() as con:
        if pid:
            return [dict(r) for r in con.execute('SELECT * FROM events WHERE project=? ORDER BY id DESC LIMIT 40', (pid,))]
        return [dict(r) for r in con.execute('SELECT * FROM events ORDER BY id DESC LIMIT 20')]


def setting(key, default=''):
    with database() as con:
        row = con.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
        return row[0] if row else default


def set_setting(key, value):
    with database() as con:
        con.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (key, str(value)))


def update(pid, message, **changes):
    allowed = {'title', 'phase', 'revision', 'attempts', 'spec', 'review', 'tests', 'error'}
    if not changes.keys() <= allowed: raise ValueError('Champ inconnu')
    fields = {k: json.dumps(v, ensure_ascii=False) if k in ('spec', 'review', 'tests') and v is not None else v for k, v in changes.items()}
    fields['updated'] = time.time()
    with database() as con:
        con.execute('UPDATE projects SET ' + ','.join(k+'=?' for k in fields) + ' WHERE id=?', (*fields.values(), pid))
        con.execute('INSERT INTO events(project,t,message) VALUES (?,?,?)', (pid, time.time(), message))
        if {'spec', 'review', 'tests'} & changes.keys():
            snapshot = dict(con.execute('SELECT * FROM projects WHERE id=?', (pid,)).fetchone())
            con.execute('INSERT INTO versions(project,t,snapshot) VALUES (?,?,?)',
                        (pid, time.time(), json.dumps(snapshot, ensure_ascii=False)))
    log.info('%s : %s', pid, message)


def new_project():
    with database() as con:
        count = con.execute('SELECT COUNT(*) FROM projects').fetchone()[0]
        pid = uuid.uuid4().hex[:16]
        topic = TOPICS[count % len(TOPICS)]
        con.execute('INSERT INTO projects(id,topic,title,phase,created,updated) VALUES (?,?,?,?,?,?)',
                    (pid, topic, 'Recherche : '+topic, 'design', time.time(), time.time()))
        con.execute('INSERT INTO events(project,t,message) VALUES (?,?,?)', (pid, time.time(), 'Nouveau sujet : '+topic))
        con.execute("INSERT OR REPLACE INTO settings VALUES ('request_next','0')")
    return get_project(pid)


def valid_review(review):
    if not isinstance(review, dict) or type(review.get('score')) is not int or not 0 <= review['score'] <= 10:
        raise ValueError('Note de critique invalide')
    if review.get('verdict') not in ('publish', 'revise'): raise ValueError('Verdict invalide')
    prototype.text(review.get('reason'), 'motif', 20, 2000)
    for key in ('strengths', 'blockers', 'improvements'):
        if not isinstance(review.get(key), list) or len(review[key]) > 12: raise ValueError('Critique incomplete')
        for item in review[key]: prototype.text(item, key, 3, 1200)
    return review


def publish(project):
    """Artefacts atomiques ; route publique reservee aux projets approuves."""
    review = valid_review(project['review'])
    if review['verdict'] != 'publish' or review['score'] < 8 or review['blockers']:
        raise ValueError('Critique insuffisante pour publication')
    model, tests = prototype.validate(project['spec'])
    root = ATELIER_DIR / 'releases'
    root.mkdir(exist_ok=True)
    stage = root / ('.'+project['id'])
    stage.mkdir(exist_ok=True)
    content = prototype.render(model)
    (stage / 'index.html').write_text(content, encoding='utf-8')
    digest = hashlib.sha256(content.encode()).hexdigest()
    report = dict(model=ATELIER_MODEL, created=time.time(), revision=project['revision'],
                  tests=tests, review=review, sha256=digest,
                  status='Prototype exploratoire ; tests techniques et autocritique, sans certification scientifique.')
    (stage / 'project.json').write_text(json.dumps(project['spec'], ensure_ascii=False, indent=2), encoding='utf-8')
    (stage / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    with database() as con:
        history = [json.loads(r[0]) for r in con.execute('SELECT snapshot FROM versions WHERE project=? ORDER BY id', (project['id'],))]
    (stage / 'history.json').write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding='utf-8')
    (stage / 'README.txt').write_text(model['title']+'\n\nOuvrir index.html dans un navigateur, sans installation ni connexion.\n'
        +'Le modele local a concu les hypotheses et les formules ; le moteur du labo construit l’interface.\n'
        +'Voir project.json pour les hypotheses et validation.json pour les tests et la critique.\n'
        +'Prototype exploratoire : pas une preuve scientifique, pas une invention certifiee.\n', encoding='utf-8')
    with zipfile.ZipFile(stage / 'prototype.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in ('index.html', 'project.json', 'validation.json', 'history.json', 'README.txt'):
            archive.write(stage / name, name)
    target = root / project['id']
    # Apres interruption entre rename et UPDATE, la meme publication est reproductible.
    if not target.exists(): os.replace(stage, target)
    else:
        for source in stage.iterdir(): os.replace(source, target / source.name)
        stage.rmdir()
    update(project['id'], 'Prototype publie : tests reussis et critique sans point bloquant.', phase='published', tests=tests, error=None)
    set_setting('next_at', time.time()+INTERVAL)


def step(p):
    pid = p['id']
    if p['phase'] in ('design', 'revise'):
        base = foundations.seed(p['topic'])
        previous = '\nDerniere version : '+json.dumps(p['spec'], ensure_ascii=False) if p['spec'] else ''
        feedback = '\nA corriger : '+json.dumps(p['review'], ensure_ascii=False) if p['review'] else ''
        if p['error']: feedback += '\nErreur des tests : '+p['error']
        existing = [x['title'] for x in list_projects(12) if x['id'] != pid]
        prompt = '''Tu es concepteur de prototypes futuristes. Adapte en francais le bilan de reference fourni en un simulateur utile.
Sujet : '''+p['topic']+'''. Le produit final est une application interactive telechargeable, calculable hors ligne.
Le moteur construit automatiquement les curseurs, les mesures, un graphe de sensibilite et un export CSV.
Conserve les equations, unites et identifiants du bilan fourni sauf erreur mathematique demontree.
Personnalise le titre, les explications, les scenarios et les valeurs par defaut dans les bornes.
Fournis exactement 2 mesures et 2 ou 3 parametres. Identifiants ASCII courts, au maximum 64 caracteres.
Formules : uniquement les identifiants des parametres, nombres, parentheses, + - * / et min,max,abs,sqrt.
Pas de puissance, pas de reference aux autres mesures. Evite toute division par zero sur l'ensemble des bornes.
Chaque parametre doit influencer au moins une mesure. Verifie les unites, les conversions et les ordres de grandeur.
Explique chaque formule et ses coefficients. Les constantes non sourcees doivent etre declarees comme hypotheses illustratives.
Minimum 2 hypotheses et 2 limites explicites. Ne revendique aucune nouveaute scientifique ou preuve experimentale.
N'invente pas de formule d'humidite, biologie ou rendement hors du bilan fourni. Un rapport de flux n'est pas une humidite relative.
Textes brefs : 30 mots maximum par champ, 2 hypotheses et 2 limites. Ne recopie pas les consignes techniques dans les textes du produit.
Bilan de reference : '''+json.dumps(base,ensure_ascii=False)+'''\nTitres deja proposes a ne pas reproduire : '''+json.dumps(existing, ensure_ascii=False)+previous+feedback
        spec = llm.ask(prompt, schema=SPEC_SCHEMA, model=ATELIER_MODEL, num_predict=2300, num_ctx=8192,
                       timeout=2400, wait=True, progress=_progress)
        # Sauver aussi une proposition invalide pour permettre au modele de la corriger.
        update(pid, 'Proposition recue ; verification des formules et des commandes.', spec=spec, tests=None, review=None)
        model, tests = prototype.validate(spec)
        with database() as con:
            previous_titles = {r[0].casefold() for r in con.execute('SELECT title FROM projects WHERE id<>?', (pid,))}
        if model['title'].casefold() in previous_titles:
            raise ValueError('Titre deja utilise : proposer un projet different, pas une copie.')
        update(pid, f'Tests numeriques reussis sur {tests["cases"]} scenarios ; autocritique a suivre.',
               title=model['title'], phase='review', tests=tests, attempts=0, error=None)
    elif p['phase'] == 'review':
        prompt = '''Tu es un evaluateur rigoureux, distinct du role de conception. Critique ce simulateur pedagogique.
Il s'agit d'un prototype pedagogique, pas d'une innovation prouvee. Verifie les formules, dimensions/unites,
conversions, coefficients, bornes, valeurs par defaut, utilite, honnetete des hypotheses et limites.
Les tests numeriques ne prouvent PAS la validite physique. Mets chaque erreur substantielle dans blockers.
Score entier de 0 a 10. Verdict publish seulement si score >=8 et aucun blocker, sinon revise.
Ne recompense pas seulement une belle presentation. N'invente pas d'objection : chaque blocker doit montrer une contradiction concrete,
une operation dimensionnelle fausse ou un cas numerique qui echoue. Un parametre choisi par l'utilisateur est une hypothese,
pas une prediction. Un rendement declare illustratif ne pretend pas modeliser la biologie ou les conditions de Mars.
Une surface en m2 multipliee par kg/m2/j donne kg/j ; une surface multipliee par L/m2/j donne L/j.
Ces deux sorties independantes n'ont aucune conversion kg/L a faire entre elles. Ne demande pas de donnees externes
pour valider un bilan explicitement illustratif. La rigueur comprend aussi l'absence de faux positifs.
Reponse en francais, concise (200 mots maximum), au maximum 3 elements par liste.
Specification : '''+json.dumps(p['spec'], ensure_ascii=False)+'\nTests : '+json.dumps(p['tests'], ensure_ascii=False)
        review = valid_review(llm.ask(prompt, schema=REVIEW_SCHEMA, model=ATELIER_MODEL, num_predict=4096,
                                     num_ctx=8192, timeout=3600, wait=True, progress=_progress, thinking=True))
        update(pid, 'Autocritique : '+str(review['score'])+'/10 — '+review['reason'], review=review, attempts=0)
        if review['verdict'] == 'publish' and review['score'] >= 8 and not review['blockers']:
            if setting('paused', '0') != '1': publish(get_project(pid))
        elif p['revision'] < 3:
            update(pid, 'Les points de critique sont transmis au concepteur.', phase='revise', revision=p['revision']+1)
        else:
            update(pid, 'Trois revisions effectuees ; prototype conserve sans publication.', phase='rejected')
            set_setting('next_at', time.time()+INTERVAL)


def run():
    global _progress
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    ATELIER_DIR.mkdir(parents=True, exist_ok=True)
    with (ATELIER_DIR / '.worker.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = {'status': 'starting', 'message': 'Demarrage de l’atelier', 'model': ATELIER_MODEL}
        def progress(activity, characters):
            state.update(activity=activity, characters=characters)
        _progress = progress
        def heartbeat():
            while True:
                direct.write('atelier', dict(state))
                time.sleep(15)
        threading.Thread(target=heartbeat, daemon=True).start()
        while True:
            p = None
            try:
                if setting('paused', '0') == '1':
                    state.update(status='paused', message='Atelier en pause ; projets publies toujours disponibles.')
                    time.sleep(15)
                    continue
                if shutil.disk_usage(ATELIER_DIR).free < 2*1024**3:
                    state.update(status='storage', message='Espace insuffisant : 2 Gio libres requis.')
                    time.sleep(60)
                    continue
                if not llm.available(ATELIER_MODEL):
                    state.update(status='model_missing', message='Modele de conception indisponible : '+ATELIER_MODEL)
                    time.sleep(60)
                    continue
                with database() as con:
                    p = unpack(con.execute("SELECT * FROM projects WHERE phase IN ('design','review','revise') ORDER BY created LIMIT 1").fetchone())
                    count = con.execute('SELECT COUNT(*) FROM projects').fetchone()[0]
                if p is None:
                    due = 0 if setting('request_next', '0') == '1' else float(setting('next_at', '0'))
                    if count >= 5000:
                        state.update(status='quota', message='Archive de 5000 projets atteinte ; pause de creation.')
                        time.sleep(60)
                        continue
                    if time.time() < due:
                        state.update(status='idle', message='Cycle termine. Prochaine recherche programmee.', next_at=due)
                        time.sleep(30)
                        continue
                    p = new_project()
                state.update(status=p['phase'], message=PHASES[p['phase']]+' : '+p['title'], project=p['id'], next_at=None)
                step(p)
                state.update(activity=None, characters=None)
            except llm.Busy:
                state.update(status='waiting', message='En attente du modele, utilise par une autre mission.')
            except Exception as exc:
                if isinstance(exc, (ValueError, SyntaxError, TypeError, KeyError)):
                    log.info('Proposition a corriger (pas une panne du service) : %s', exc)
                else:
                    log.exception('Echec technique d’une etape de l’atelier')
                state.update(status='retry', message='Etape en echec ; nouvelle tentative apres temporisation.', activity=None, characters=None)
                if p:
                    attempts = p['attempts']+1
                    update(p['id'], 'Etape interrompue : '+str(exc)[:500], attempts=attempts, error=str(exc)[:1500],
                           phase='rejected' if attempts >= 3 else p['phase'])
                    if attempts >= 3: set_setting('next_at', time.time()+INTERVAL)
            # Laisse passer les autres missions entre deux etapes ; pas de boucle de generation continue.
            time.sleep(60)


if __name__ == '__main__': run()
