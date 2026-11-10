"""Ordonnanceur persistant des experiences, independant des longues generations LLM."""
import fcntl
import json
import logging
import math
import shutil
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from . import direct, experiments
from .config import DATA, LOG_FORMAT

ROOT=DATA/'explorations'
INTERVAL=600
log=logging.getLogger('explorations')


@contextmanager
def database():
    ROOT.mkdir(exist_ok=True)
    con=sqlite3.connect(ROOT/'runs.db',timeout=15);con.row_factory=sqlite3.Row
    try:
        con.executescript('''CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,kind TEXT,created REAL,seed INTEGER,duration REAL,payload TEXT);
        CREATE INDEX IF NOT EXISTS latest_kind ON runs(kind,created DESC);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
        CREATE TABLE IF NOT EXISTS queue(kind TEXT PRIMARY KEY,requested REAL);''')
        yield con
        con.commit()
    finally: con.close()


def setting(key,default='0'):
    with database() as con:
        r=con.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
        return r[0] if r else default


def set_setting(key,value):
    with database() as con: con.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',(key,str(value)))


def enqueue(kind):
    if kind not in experiments.CATALOG: raise ValueError('Mission inconnue')
    with database() as con: con.execute('INSERT OR IGNORE INTO queue VALUES (?,?)',(kind,time.time()))


def get_run(kind,run_id=None):
    with database() as con:
        if run_id: row=con.execute('SELECT * FROM runs WHERE kind=? AND id=?',(kind,run_id)).fetchone()
        else: row=con.execute('SELECT * FROM runs WHERE kind=? ORDER BY created DESC LIMIT 1',(kind,)).fetchone()
        if not row: return None
        result=dict(row);result['payload']=json.loads(result['payload']);return result


def latest():
    out=[]
    for kind,(title,summary) in experiments.CATALOG.items():
        run=get_run(kind)
        out.append(dict(kind=kind,title=title,summary=summary,run={k:v for k,v in run.items() if k!='payload'} if run else None,
                        metrics=run['payload']['metrics'] if run else []))
    return out


def history(kind):
    with database() as con:
        return [dict(r) for r in con.execute('SELECT id,created,seed,duration FROM runs WHERE kind=? ORDER BY created DESC LIMIT 12',(kind,))]


def execute(kind,seed=None):
    started=time.monotonic()
    if seed is None: seed=int.from_bytes(uuid.uuid4().bytes[:4],'big')
    payload=experiments.run(kind,seed)
    encoded=json.dumps(payload,ensure_ascii=False,allow_nan=False)
    if len(encoded)>2_000_000: raise ValueError('Resultat trop volumineux')
    if not payload.get('metrics') or not payload.get('plots'): raise ValueError('Resultat incomplet')
    rid=uuid.uuid4().hex[:16]
    with database() as con:
        con.execute('INSERT INTO runs VALUES (?,?,?,?,?,?)',(rid,kind,time.time(),seed,time.monotonic()-started,encoded))
        con.execute('DELETE FROM queue WHERE kind=?',(kind,))
    return get_run(kind,rid)


def choose():
    with database() as con:
        queued=con.execute('SELECT kind FROM queue ORDER BY requested LIMIT 1').fetchone()
        if queued: return queued[0]
        times={r[0]:r[1] for r in con.execute('SELECT kind,MAX(created) FROM runs GROUP BY kind')}
    for kind in experiments.CATALOG:
        if kind not in times: return kind
    if time.time()-max(times.values())>=INTERVAL: return min(times,key=times.get)
    return None


def main():
    logging.basicConfig(level=logging.INFO,format=LOG_FORMAT);ROOT.mkdir(exist_ok=True)
    with (ROOT/'.worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        state={'status':'starting','message':'Initialisation des explorations'}
        def heartbeat():
            while True: direct.write('explorations',dict(state));time.sleep(15)
        threading.Thread(target=heartbeat,daemon=True).start()
        while True:
            try:
                if setting('paused')=='1':
                    state.update(status='paused',message='Explorations en pause');time.sleep(10);continue
                if shutil.disk_usage(ROOT).free<2*1024**3:
                    state.update(status='storage',message='Moins de 2 Gio libres : calculs suspendus');time.sleep(60);continue
                kind=choose()
                if kind:
                    state.update(status='running',kind=kind,message='Expérience : '+experiments.CATALOG[kind][0])
                    run=execute(kind)
                    state.update(status='idle',message='Résultat enregistré : '+run['payload']['title'],last_run=run['id'])
                    log.info('Experience %s terminee, seed=%s',kind,run['seed'])
                else: state.update(status='idle',message='Prochaine expérience dans les dix minutes suivant le dernier résultat.')
            except Exception:
                log.exception('Echec technique d’une exploration')
                state.update(status='error',message='Une expérience a échoué ; nouvelle tentative dans une minute.')
                time.sleep(50)
            time.sleep(10)


if __name__=='__main__': main()
