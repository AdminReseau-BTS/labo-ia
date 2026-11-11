"""Comparaisons descriptives sur une fenêtre bornée, sans relancer les moteurs."""
import json
import math
import statistics
from . import explorations, experiments

RULES = {
    'swarm': (0, False), 'evolution': (1, True), 'planets': (2, True),
    'signals': (2, False), 'energy': (None, False), 'life': (1, False),
}


def score(kind, metrics):
    index, minimize = RULES[kind]
    if kind == 'energy':
        baseline, optimized = metrics[0]['value'], metrics[1]['value']
        if baseline <= 0: raise ValueError('Coût témoin non positif')
        return 100 * (baseline - optimized) / baseline, 'Réduction du coût simulé', '%'
    metric = metrics[index]
    value = float(metric['value'])
    if not math.isfinite(value): raise ValueError('Mesure non finie')
    return value, metric['label'], metric['unit']


def snapshot():
    cards = []
    with explorations.database() as con:
        for kind, (title, _) in experiments.CATALOG.items():
            total = con.execute('SELECT COUNT(*) FROM runs WHERE kind=?', (kind,)).fetchone()[0]
            rows = con.execute("SELECT id,created,seed,json_extract(payload,'$.metrics') AS metrics FROM runs WHERE kind=? ORDER BY created DESC LIMIT 500", (kind,)).fetchall()
            samples = []
            for row in rows:
                try:
                    value, label, unit = score(kind, json.loads(row['metrics']))
                    if not math.isfinite(value): continue
                except (ValueError, TypeError, KeyError, IndexError):
                    continue
                samples.append(dict(id=row['id'], created=row['created'], seed=row['seed'], value=value))
            card = dict(kind=kind, title=title, total=total, count=len(samples), skipped=len(rows)-len(samples))
            if samples:
                best = (min if RULES[kind][1] else max)(samples, key=lambda r: r['value'])
                card.update(best=best, latest=samples[0], label=label, unit=unit,
                            median=statistics.median(r['value'] for r in samples),
                            direction='Plus bas = meilleur' if RULES[kind][1] else 'Plus haut = meilleur')
            cards.append(card)
    return cards
