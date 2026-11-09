"""Compile des specifications declaratives en simulateurs autonomes, sans executer du code IA."""
import ast
import html
import itertools
import json
import math
import operator
import random
import re
from pathlib import Path

OPS = {ast.Add: ('+', operator.add), ast.Sub: ('-', operator.sub),
       ast.Mult: ('*', operator.mul), ast.Div: ('/', operator.truediv)}
FUNCS = {'min': min, 'max': max, 'abs': abs, 'sqrt': math.sqrt}


def formula(source, names):
    """Petit arbre mathematique portable. Aucun eval, attribut ou appel arbitraire."""
    if not isinstance(source, str) or len(source) > 240:
        raise ValueError('Formule trop longue')
    tree = ast.parse(source, mode='eval')
    if sum(1 for _ in ast.walk(tree)) > 90:
        raise ValueError('Formule trop complexe')

    def walk(n):
        if isinstance(n, ast.Constant) and type(n.value) in (int, float) and math.isfinite(n.value) and abs(n.value) <= 1e9:
            return ['n', n.value]
        if isinstance(n, ast.Name) and n.id in names:
            return ['v', n.id]
        if isinstance(n, ast.BinOp) and type(n.op) in OPS:
            return [OPS[type(n.op)][0], walk(n.left), walk(n.right)]
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
            return ['neg', walk(n.operand)]
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in FUNCS and not n.keywords:
            count = len(n.args)
            if (n.func.id in ('abs', 'sqrt') and count == 1) or (n.func.id in ('min', 'max') and 2 <= count <= 5):
                return [n.func.id, *map(walk, n.args)]
        raise ValueError('Formule non autorisee : ' + source)
    return walk(tree.body)


def evaluate(tree, values):
    op = tree[0]
    if op == 'n': return tree[1]
    if op == 'v': return values[tree[1]]
    args = [evaluate(t, values) for t in tree[1:]]
    if op == 'neg': return -args[0]
    if op in FUNCS: return FUNCS[op](*args)
    return {'+': operator.add, '-': operator.sub, '*': operator.mul, '/': operator.truediv}[op](*args)


def text(value, name, minimum=1, maximum=1500):
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise ValueError('Texte invalide : ' + name)
    return value.strip()


def compile_spec(spec):
    if not isinstance(spec, dict): raise ValueError('Specification objet attendue')
    result = {k: text(spec.get(k), k, lo, hi) for k, lo, hi in
              [('title', 5, 100), ('summary', 30, 600), ('hypothesis', 30, 1000)]}
    for key in ('assumptions', 'limitations'):
        items = spec.get(key)
        if not isinstance(items, list) or not 2 <= len(items) <= 6:
            raise ValueError('Deux a six ' + key + ' requis')
        result[key] = [text(s, key, 10, 500) for s in items]
    params = spec.get('parameters')
    metrics = spec.get('metrics')
    if not isinstance(params, list) or not 2 <= len(params) <= 5: raise ValueError('2 a 5 parametres requis')
    if not isinstance(metrics, list) or not 2 <= len(metrics) <= 4: raise ValueError('2 a 4 mesures requises')
    result['parameters'] = []
    names = set()
    for p in params:
        key = p.get('id', '')
        if not re.fullmatch('[a-z][a-z0-9_]{0,19}', key) or key in names or key in FUNCS:
            raise ValueError('Identifiant parametre invalide ou duplique')
        names.add(key)
        vals = [p.get(k) for k in ('min', 'max', 'default')]
        if any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 1e8 for v in vals):
            raise ValueError('Bornes numeriques invalides')
        if not vals[0] < vals[1] or not vals[0] <= vals[2] <= vals[1]:
            raise ValueError('Bornes incoherentes')
        result['parameters'].append(dict(id=key, label=text(p.get('label'), 'label', 2, 100),
            unit=text(p.get('unit'), 'unit', 1, 40), min=vals[0], max=vals[1], default=vals[2]))
    result['metrics'] = []
    for m in metrics:
        result['metrics'].append(dict(label=text(m.get('label'), 'mesure', 2, 100),
            unit=text(m.get('unit'), 'unit', 1, 40), formula=m.get('formula'),
            explanation=text(m.get('explanation'), 'explication', 20, 600), tree=formula(m.get('formula'), names)))
    return result


def validate(spec):
    """Combinaisons des bornes, points aleatoires reproductibles et sensibilite."""
    model = compile_spec(spec)
    ps = model['parameters']
    rng = random.Random(20261109)
    cases = list(itertools.product(*[(p['min'], p['default'], p['max']) for p in ps]))
    cases += [tuple(rng.uniform(p['min'], p['max']) for p in ps) for _ in range(64)]
    outputs = []
    for case in cases:
        values = dict(zip((p['id'] for p in ps), case))
        try:
            y = [evaluate(m['tree'], values) for m in model['metrics']]
            if any(not math.isfinite(v) or abs(v) > 1e14 for v in y): raise ValueError('Resultat non fini ou excessif')
            outputs.append(y)
        except (ArithmeticError, ValueError) as exc:
            raise ValueError(f'Calcul invalide pour {values}: {exc}') from exc
    for p in ps:
        vals = {q['id']: q['default'] for q in ps}
        ys = []
        for x in (p['min'], p['default'], p['max']):
            vals[p['id']] = x
            ys.append([evaluate(m['tree'], vals) for m in model['metrics']])
        if all(max(col) - min(col) < 1e-9 for col in zip(*ys)):
            raise ValueError('Parametre sans effet : ' + p['id'])
    return model, {'passed': True, 'cases': len(cases), 'checks': ['schema', 'formules bornees',
        'combinaisons des bornes', '64 points aleatoires', 'sensibilite des commandes'],
        'scope': 'Validite numerique du prototype ; aucune validation scientifique ou industrielle.',
        'ranges': [{'label': m['label'], 'min': min(c[i] for c in outputs), 'max': max(c[i] for c in outputs)}
                   for i, m in enumerate(model['metrics'])]}


def render(model):
    template = Path(__file__).with_name('prototype.html').read_text(encoding='utf-8')
    data = json.dumps(model, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    return template.replace('__TITLE__', html.escape(model['title'])).replace('__MODEL__', data)
