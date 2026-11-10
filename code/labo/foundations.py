"""Bilans de reference fournis par le developpement, pas des inventions de l'IA."""
import copy


def p(key, label, unit, low, high, default):
    return dict(id=key,label=label,unit=unit,min=low,max=high,default=default)


def m(label,unit,formula,explanation):
    return dict(label=label,unit=unit,formula=formula,explanation=explanation)


def seed(topic):
    if 'lunaire' in topic:
        params=[p('equipage','Équipage','personnes',2,20,6),p('usage','Usage par personne','L/jour',10,80,30),p('rendement','Récupération','%',0,98,90)]
        metrics=[m('Eau récupérée','L/jour','equipage * usage * rendement / 100','Le flux quotidien total est multiplié par la fraction récupérée.'),
                 m('Apport extérieur nécessaire','L/jour','equipage * usage * (1 - rendement / 100)','Le bilan stationnaire impose de remplacer la fraction non récupérée.')]
    elif 'microreseau' in topic:
        params=[p('production','Production quotidienne','kWh',1,1000,200),p('demande','Demande quotidienne','kWh',1,1000,100),p('capacite','Batterie initialement vide','kWh',0,500,100)]
        metrics=[m('Surplus stockable','kWh','min(capacite, max(0, production - demande))','Le surplus est borné par la capacité libre de la batterie, initialement vide.'),
                 m('Apport du réseau','kWh','max(0, demande - production)','Le réseau couvre le déficit de ce bilan journalier ; la batterie est initialement vide.')]
    elif 'serre' in topic or 'verticale' in topic:
        params=[p('surface','Surface cultivée','m²',10,1000,100),p('rendement','Rendement supposé','kg/m²/jour',0.001,0.1,0.02),p('irrigation','Irrigation supposée','L/m²/jour',0.1,10,2)]
        metrics=[m('Production estimée','kg/jour','surface * rendement','Surface multipliée par un rendement fourni par le scénario, non prédit biologiquement.'),
                 m('Besoin en eau','L/jour','surface * irrigation','Surface multipliée par le besoin en eau choisi ; pas de prédiction de photosynthèse.')]
    elif 'refroidissement' in topic:
        params=[p('surface','Surface de paroi','m²',10,500,100),p('coefficient','Coefficient thermique supposé','W/m²/K',0.1,5,1),p('ecart','Écart de température','K',1,40,10)]
        metrics=[m('Flux thermique stationnaire','W','surface * coefficient * ecart','Application du bilan simplifié Q = U A deltaT, paroi uniforme et régime stationnaire.'),
                 m('Énergie transférée en 24 heures','kWh','surface * coefficient * ecart * 24 / 1000','Puissance constante pendant 24 heures, conversion de Wh vers kWh.')]
    elif 'voile' in topic:
        params=[p('puissance','Puissance lumineuse incidente','kW',1,10000,100),p('masse','Masse totale','kg',100,10000,1000),p('duree','Durée d’éclairage','jours',1,365,30)]
        metrics=[m('Accélération idéale','m/s²','2 * puissance * 1000 / (299792458 * masse)','Réflexion parfaite : force = 2 P/c avec c = 299792458 m/s ; accélération = force/masse.'),
                 m('Gain de vitesse idéal','m/s','2 * puissance * 1000 * duree * 86400 / (299792458 * masse)','Accélération constante, 86400 secondes par jour ; gravité et trajectoire ignorées.')]
    elif 'chaleur' in topic:
        params=[p('puissance','Chaleur disponible','kW',1,1000,100),p('rendement','Récupération supposée','%',10,90,60),p('duree','Fonctionnement quotidien','h/jour',1,24,12)]
        metrics=[m('Puissance récupérée','kW','puissance * rendement / 100','La récupération est une fraction de la puissance thermique disponible.'),
                 m('Énergie récupérée','kWh/jour','puissance * rendement * duree / 100','Énergie = puissance récupérée multipliée par le temps de fonctionnement.')]
    else:
        params=[p('flux','Matière entrante','kg/jour',1,1000,100),p('rendement','Récupération matière','%',10,99,80),p('duree','Durée','jours',1,365,30)]
        metrics=[m('Matière récupérée','kg','flux * duree * rendement / 100','Masse entrante cumulée multipliée par la fraction récupérée.'),
                 m('Matière non récupérée','kg','flux * duree * (1 - rendement / 100)','Le complément ferme exactement le bilan de masse ; pertes regroupées dans cette quantité.')]
    return copy.deepcopy(dict(title='Exploration : '+topic,summary='Un bilan simplifié pour explorer différents scénarios de '+topic+'. Les paramètres sont des hypothèses explicites.',
        hypothesis='Comparer les besoins et les ressources en faisant varier les paramètres d’un bilan stationnaire vérifiable.',
        assumptions=['Les paramètres restent constants pendant la période étudiée.', 'Les rendements et besoins choisis sont des hypothèses illustratives, non des données mesurées.'],
        limitations=['Ce modèle ne prédit pas les transitoires ni les défaillances des équipements.', 'Aucune validation expérimentale ou faisabilité industrielle n’est revendiquée.'],
        parameters=params,metrics=metrics))
