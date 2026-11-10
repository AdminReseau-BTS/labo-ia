"""Six experiences reproductibles : recherche, evolution, detection et optimisation."""
from collections import deque
import math
import random
import numpy as np

CATALOG = {
 'swarm': ('Essaim explorateur','Quatre robots cartographient un labyrinthe et se comparent à une marche aléatoire.'),
 'evolution': ('Pilote par évolution','Une population de séquences de commandes évolue pour atteindre une cible.'),
 'planets': ('Chasseur d’exoplanètes','Retrouver une période de transit cachée dans une courbe lumineuse synthétique.'),
 'signals': ('Écoute du cosmos','Retrouver une balise faible noyée dans un bruit radio simulé.'),
 'energy': ('Ville sobre','Chercher la capacité de batterie qui minimise le coût d’une journée simulée.'),
 'life': ('Vie artificielle','Explorer des mondes cellulaires et chercher ceux qui restent actifs longtemps.')}


def metric(label,value,unit=''):
    return dict(label=label,value=value,unit=unit)


def plot(title,xlabel,ylabel,series):
    return dict(title=title,xlabel=xlabel,ylabel=ylabel,series=[dict(name=n,points=[[float(x),float(y)] for x,y in pts]) for n,pts in series])


def neighbors(pos,n,walls):
    r,c=pos
    return [(a,b) for a,b in ((r+1,c),(r,c+1),(r-1,c),(r,c-1)) if 0<=a<n and 0<=b<n and (a,b) not in walls]


def distances(start,n,walls):
    out={start:0};queue=deque([start])
    while queue:
        p=queue.popleft()
        for q in neighbors(p,n,walls):
            if q not in out: out[q]=out[p]+1;queue.append(q)
    return out


def world(rng,n):
    walls={(r,c) for r in range(n) for c in range(n) if rng.random()<.18}
    # Une route praticable est garantie ; aucun resultat d'apprentissage ne depend d'un monde impossible.
    for i in range(n): walls.discard((i,0));walls.discard((n-1,i))
    reachable=distances((0,0),n,walls)
    walls={(r,c) for r in range(n) for c in range(n) if (r,c) not in reachable}
    return walls


def swarm(seed):
    rng=random.Random(seed);n=18;walls=world(rng,n);total=n*n-len(walls)
    bots=[(0,0)]*4;seen={(0,0)};random_bots=list(bots);random_seen=set(seen)
    frames=[];guided=[];baseline=[]
    for tick in range(161):
        guided.append((tick,100*len(seen)/total));baseline.append((tick,100*len(random_seen)/total))
        if tick%2==0: frames.append(dict(positions=bots.copy(),seen=list(seen)))
        if tick==160: break
        for i,start in enumerate(bots):
            queue=deque([(start,[])]);visited={start};path=[]
            while queue:
                p,route=queue.popleft()
                if p not in seen: path=route;break
                options=neighbors(p,n,walls);rng.shuffle(options)
                for q in options:
                    if q not in visited: visited.add(q);queue.append((q,route+[q]))
            if path: bots[i]=path[0];seen.add(bots[i])
            opts=neighbors(random_bots[i],n,walls)
            if opts: random_bots[i]=rng.choice(opts);random_seen.add(random_bots[i])
    return dict(method='Planification par plus court chemin vers une case inexplorée, carte partagée entre robots.',
        limits='Monde discret entièrement connu du planificateur pour les obstacles. Le témoin est une marche aléatoire sur le même monde ; ce n’est pas un test de robots physiques.',
        metrics=[metric('Couverture coordonnée',round(guided[-1][1],1),'%'),metric('Témoin aléatoire',round(baseline[-1][1],1),'%'),metric('Robots',4),metric('Cases accessibles',total)],
        visual=dict(type='grid',size=n,walls=list(walls),frames=frames),plots=[plot('Progression de la cartographie','pas','couverture (%)',[('Coordination',guided),('Aléatoire',baseline)])])


def evolution(seed):
    rng=np.random.default_rng(seed);n=14;walls=world(random.Random(seed),n);goal=(n-1,n-1)
    dist=distances(goal,n,walls);moves=[(1,0),(0,1),(-1,0),(0,-1)];length=64;population=rng.integers(0,4,(64,length))
    def evaluate(genes):
        pos=(0,0);path=[pos];hits=0
        for g in genes:
            a,b=moves[int(g)];q=(pos[0]+a,pos[1]+b)
            if 0<=q[0]<n and 0<=q[1]<n and q not in walls: pos=q
            else: hits+=1
            path.append(pos)
            if pos==goal: break
        score=100-len(path)*.1 if pos==goal else -dist[pos]-hits*.02
        return score,path,dist[pos]
    history=[];first=None;best=None
    for generation in range(41):
        results=[evaluate(g) for g in population];order=np.argsort([r[0] for r in results])[::-1]
        best=results[int(order[0])]
        if first is None: first=best
        history.append((generation,best[0]))
        if generation==40: break
        elites=population[order[:8]].copy();children=[g.copy() for g in elites]
        while len(children)<64:
            a,b=elites[rng.integers(0,8,2)];split=int(rng.integers(1,length));child=np.concatenate([a[:split],b[split:]])
            mutation=rng.random(length)<.06;child[mutation]=rng.integers(0,4,mutation.sum());children.append(child)
        population=np.array(children)
    return dict(method='Algorithme génétique : 64 candidats, sélection des 8 meilleurs, croisement et mutation sur 40 générations.',
        limits='Apprentissage sur une seule carte, sans garantie de généralisation. La fonction objectif utilise la distance réelle au but ; ce pilote n’est pas le réseau de neurones Pong.',
        metrics=[metric('Distance initiale au but',first[2],'cases'),metric('Distance finale',best[2],'cases'),metric('Cible atteinte','Oui' if best[2]==0 else 'Non'),metric('Candidats évalués',64*41)],
        visual=dict(type='grid',size=n,walls=list(walls),goal=goal,frames=[dict(positions=[p],seen=best[1][:i+1]) for i,p in enumerate(best[1])]),
        plots=[plot('Meilleur score conservé à chaque génération','génération','score',[('Élite',history)])])


def planets(seed):
    rng=np.random.default_rng(seed);t=np.linspace(0,30,900);truth=float(rng.integers(170,330)/50);phase=.25;duty=.06
    transit=((t/truth-phase)%1)<duty;flux=1+rng.normal(0,.001,len(t))-.008*transit
    trials=[];best=(-1,None,None)
    for period in np.arange(3,7.001,.02):
        score=-1
        for offset in np.arange(0,1,1/16):
            inside=((t/period-offset)%1)<duty
            if inside.sum()<10: continue
            s=float((flux[~inside].mean()-flux[inside].mean())*np.sqrt(inside.sum())/.001)
            if s>best[0]: best=(s,float(period),float(offset))
            score=max(score,s)
        trials.append((float(period),score))
    return dict(method='Recherche exhaustive d’un creux périodique : 201 périodes et 16 phases, durée relative fixée à 6 %.',
        limits='Données entièrement synthétiques avec un transit injecté. Une détection réelle demanderait d’autres observations et le rejet des faux positifs astrophysiques.',
        metrics=[metric('Période retrouvée',round(best[1],3),'jours'),metric('Période injectée',truth,'jours'),metric('Erreur',round(abs(best[1]-truth),4),'jour'),metric('Échantillons',len(t))],
        visual=None,plots=[plot('Courbe lumineuse synthétique','temps (jours)','flux relatif',[('Observation simulée',zip(t,flux))]),plot('Recherche de période','période (jours)','score de détection',[('Recherche',trials)])])


def signals(seed):
    rng=np.random.default_rng(seed);fs=1024;n=2048;freq=int(rng.integers(40,220));t=np.arange(n)/fs
    signal=.35*np.sin(2*np.pi*freq*t)+rng.normal(0,1,n)
    spectrum=np.abs(np.fft.rfft(signal*np.hanning(n)))**2;axis=np.fft.rfftfreq(n,1/fs);spectrum[0]=0
    peak=int(np.argmax(spectrum));db=10*np.log10(np.maximum(spectrum,1e-12)/max(float(np.median(spectrum)),1e-12))
    return dict(method='Analyse spectrale FFT avec fenêtre de Hann ; recherche du pic dominant au-dessus du bruit médian.',
        limits='Balise et bruit sont simulés. Ce résultat n’est ni une observation du ciel ni une détection extraterrestre ; le score n’est pas une probabilité.',
        metrics=[metric('Fréquence détectée',float(axis[peak]),'Hz'),metric('Fréquence injectée',freq,'Hz'),metric('Pic / bruit médian',round(float(db[peak]),1),'dB'),metric('Durée du signal',2,'s')],
        visual=None,plots=[plot('Spectre du signal simulé','fréquence (Hz)','écart au bruit médian (dB)',[('FFT',zip(axis,db))]),plot('Signal temporel','temps (s)','amplitude',[('Signal bruité',zip(t[:300],signal[:300]))])])


def energy(seed):
    rng=np.random.default_rng(seed);hours=np.arange(24);solar=np.maximum(0,16*np.sin((hours-6)*np.pi/12))
    load=5+4*np.exp(-((hours-19)/3)**2)+rng.uniform(0,1,24);tariff=np.where((hours>=17)&(hours<=22),.42,.20)
    def dispatch(capacity):
        soc=0;grid=[];stored=[];charge=[];discharge=[];waste=[]
        for sun,demand in zip(solar,load):
            surplus=max(0,float(sun-demand));deficit=max(0,float(demand-sun))
            incoming=min(surplus,(capacity-soc)/.9);soc+=incoming*.9
            outgoing=min(deficit,soc*.9);soc-=outgoing/.9
            grid.append(deficit-outgoing);stored.append(soc);charge.append(incoming);discharge.append(outgoing);waste.append(surplus-incoming)
        cost=float(np.dot(grid,tariff)+capacity*.03)
        residual=max(abs(float(solar[i])+grid[i]+discharge[i]-float(load[i])-charge[i]-waste[i]) for i in range(24))
        return dict(cost=cost,grid=grid,stored=stored,residual=residual)
    trials=[(cap,dispatch(cap)) for cap in range(0,81,2)];capacity,best=min(trials,key=lambda item:item[1]['cost']);base=trials[0][1]
    return dict(method='Énumération de 41 capacités. Dispatch solaire prioritaire, charge/décharge à 90 %, coût journalier de capacité de 0,03 €/kWh.',
        limits='Scénario synthétique sur 24 heures, batterie initialement vide et valeur finale du stock ignorée. Pas de puissance maximale, vieillissement ou recommandation d’investissement.',
        metrics=[metric('Coût sans batterie',round(base['cost'],2),'€/jour'),metric('Coût optimisé',round(best['cost'],2),'€/jour'),metric('Capacité choisie',capacity,'kWh'),metric('Erreur du bilan',round(best['residual'],10),'kWh')],
        visual=None,plots=[plot('Bilan d’une journée simulée','heure','énergie horaire (kWh)',[('Solaire',zip(hours,solar)),('Demande',zip(hours,load)),('Réseau',zip(hours,best['grid']))]),plot('Recherche de capacité','capacité (kWh)','coût total (€/jour)',[('Recherche',[(c,r['cost']) for c,r in trials])])])


def life_step(grid):
    count=sum(np.roll(np.roll(grid,dx,axis=0),dy,axis=1) for dx in (-1,0,1) for dy in (-1,0,1) if dx or dy)
    return ((count==3)|((grid==1)&(count==2))).astype(np.uint8)


def life(seed):
    rng=np.random.default_rng(seed);n=24
    def simulate(grid):
        frames=[];counts=[];seen={};period=None
        for step in range(81):
            key=grid.tobytes()
            if period is None and key in seen: period=step-seen[key]
            seen.setdefault(key,step);frames.append(dict(cells=grid.astype(int).ravel().tolist()));counts.append((step,int(grid.sum())))
            grid=life_step(grid)
        return len(seen),frames,counts,period
    runs=[simulate((rng.random((n,n))<rng.uniform(.15,.4)).astype(np.uint8)) for _ in range(16)]
    best=max(runs,key=lambda r:r[0]);unique,frames,counts,period=best
    return dict(method='Jeu de la vie de Conway sur grille torique. Recherche parmi 16 mondes aléatoires du plus grand nombre d’états distincts sur 80 pas.',
        limits='Automate cellulaire déterministe : ce n’est pas de la vie biologique ni une conscience. La durée d’observation est finie ; une période peut apparaître plus tard.',
        metrics=[metric('Mondes explorés',16),metric('États distincts',unique),metric('Période observée',period if period else 'Non observée'),metric('Cellules finales',counts[-1][1])],
        visual=dict(type='life',size=n,frames=frames),plots=[plot('Population du monde retenu','pas','cellules vivantes',[('Population',counts)])])


def run(kind,seed):
    if kind not in CATALOG: raise ValueError('Mission inconnue')
    result=globals()[kind](seed)
    result.update(kind=kind,title=CATALOG[kind][0],summary=CATALOG[kind][1],seed=seed,
                  origin='Expérience algorithmique reproductible, moteur fourni par le labo ; données simulées.')
    return result
