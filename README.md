# Labo IA

**Un laboratoire autonome qui tourne jour et nuit sur un serveur domestique, et qui publie ici ses recherches tout seul.**

Il poursuit deux missions :

1. **Sondes Fantômes** : relire avec un œil neuf les centaines de milliers d'images prises par les sondes spatiales de la NASA (Voyager, Galileo, Cassini, New Horizons), pour faire remonter celles qui ne ressemblent à aucune autre.
2. **Labo de neurones** : apprendre à jouer à Pong à une culture de neurones simulés, sur le modèle de l'expérience DishBrain, en inventant et en testant lui-même des protocoles d'entraînement.

Ce dépôt est son carnet de recherche : la présentation ci-dessous, [un rapport par jour](rapports/), les résultats complets ([Sondes Fantômes](resultats/sondes.md), [neurones](resultats/neurones.md)) et le [code source](code/labo/). Il se met à jour automatiquement toutes les 6 heures.

## Où en est le labo

*Mis à jour automatiquement le 29/10/2026 à 03:50 UTC.*

| Indicateur | Valeur |
|---|---:|
| Images d'archives analysées | 42 175 |
| Cibles entièrement fouillées | 50 / 185 |
| Parties de Pong jouées | 269 (71,7 h de culture simulée) |
| Recettes d'entraînement testées | 75 |
| Meilleur progrès (avant contre-épreuve) | +12 points (recette n°18) |
| Apprentissages confirmés par contre-épreuve | 0 sur 7 |

**Dernières candidates de Sondes Fantômes** (cliquer pour ouvrir la fiche NASA) :

<a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=vg-iss-2-j-c2064928"><img src="https://opus.pds-rings.seti.org/holdings/previews/VGISS_5xxx/VGISS_5213/DATA/C20649XX/C2064928_small.jpg" width="110" alt="Europa, n°1" title="Europa, n°1"></a> <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=vg-iss-2-j-c2046905"><img src="https://opus.pds-rings.seti.org/holdings/previews/VGISS_5xxx/VGISS_5210/DATA/C20469XX/C2046905_small.jpg" width="110" alt="Europa, n°2" title="Europa, n°2"></a> <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=vg-iss-2-n-c1242957"><img src="https://opus.pds-rings.seti.org/holdings/previews/VGISS_8xxx/VGISS_8210/DATA/C12429XX/C1242957_small.jpg" width="110" alt="Star, n°1" title="Star, n°1"></a> <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=vg-iss-2-n-c1242706"><img src="https://opus.pds-rings.seti.org/holdings/previews/VGISS_8xxx/VGISS_8210/DATA/C12427XX/C1242706_small.jpg" width="110" alt="Star, n°2" title="Star, n°2"></a> <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=vg-iss-2-s-c4430317"><img src="https://opus.pds-rings.seti.org/holdings/previews/VGISS_6xxx/VGISS_6215/DATA/C44303XX/C4430317_small.jpg" width="110" alt="Phoebe, n°1" title="Phoebe, n°1"></a> <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=vg-iss-2-s-c4430137"><img src="https://opus.pds-rings.seti.org/holdings/previews/VGISS_6xxx/VGISS_6215/DATA/C44301XX/C4430137_small.jpg" width="110" alt="Phoebe, n°2" title="Phoebe, n°2"></a> <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=vg-iss-1-s-c3495037"><img src="https://opus.pds-rings.seti.org/holdings/previews/VGISS_6xxx/VGISS_6113/DATA/C34950XX/C3495037_small.jpg" width="110" alt="Rhea, n°1" title="Rhea, n°1"></a> <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=vg-iss-1-s-c3495057"><img src="https://opus.pds-rings.seti.org/holdings/previews/VGISS_6xxx/VGISS_6113/DATA/C34950XX/C3495057_small.jpg" width="110" alt="Rhea, n°2" title="Rhea, n°2"></a>

**Meilleure recette (n°18)**, balles renvoyées minute par minute :

![Courbe d'apprentissage de la meilleure recette](resultats/courbe-meilleure-recette.svg)

Dernier rapport : [2026-10-29](rapports/2026-10-29.md)

## Mission 1 : Sondes Fantômes

### L'idée

Les archives planétaires publiques contiennent des centaines de milliers d'images. La plupart n'ont été regardées que pour la raison précise pour laquelle elles avaient été prises. Une IA peut toutes les passer en revue, sans fatigue et sans idée préconçue, et signaler celles qui sortent du lot. Ce ne sont pas des découvertes, mais des images qui méritent un regard humain.

### Comment ça marche

1. **Les données** viennent de l'API publique [OPUS](https://opus.pds-rings.seti.org) du PDS Ring-Moon Systems Node (NASA). Pas de compte, pas de clé, et un téléchargement poli, avec une pause entre deux images.
2. **Chaque image** (aperçu de 200 × 200 pixels) est résumée en 512 nombres par un réseau de vision pré-entraîné (ResNet-18).
3. **Une image n'est étrange que par rapport à ses semblables** : elle est comparée seulement aux autres images de la même cible prises par le même instrument. Deux mesures sont combinées : la distance moyenne à ses 10 plus proches voisines, et un score d'Isolation Forest calculé sur une réduction à 32 dimensions.
4. **Les images ratées sont écartées** : presque noires, saturées, uniformes, incomplètes (marges ou bandes sans données), striées de lignes brouillées, ou faites presque uniquement de bruit.
5. **Les 10 images les plus isolées de chaque groupe deviennent des candidates.** Si une IA locale est installée (Ollama avec gemma3:4b, gratuite et hors ligne), elle décrit chaque candidate et dit si cela ressemble à un défaut d'image, à quelque chose de connu, ou à quelque chose qui mérite d'être vérifié.

La fouille commence par huit cibles (Io, Europe, Miranda, Triton, Hypérion, Encelade, Pluton, Arrokoth), puis s'étend à toutes les cibles des cinq caméras, soit environ 560 000 images.

### À garder en tête

La plupart des anomalies seront des effets d'instrument, des prises de vue inhabituelles ou des phénomènes déjà connus. Chaque candidate renvoie vers sa fiche OPUS et ses métadonnées complètes, pour pouvoir vérifier.

## Mission 2 : Labo de neurones

### L'idée

En 2022, l'entreprise Cortical Labs a montré (expérience DishBrain, [Kagan et al., *Neuron*](https://doi.org/10.1016/j.neuron.2022.09.001)) que des neurones vivants cultivés sur une puce d'électrodes apprennent à jouer à Pong en quelques minutes. La recette : une stimulation prévisible quand ils renvoient la balle, et une stimulation imprévisible quand ils la ratent. Pourquoi cela marche reste débattu.

Ce labo rejoue l'expérience en simulation, sans arrêt, pour chercher quels protocoles d'entraînement et quels mécanismes biologiques rendent cet apprentissage possible.

### La culture virtuelle

- **1 000 neurones impulsionnels** (modèle d'Izhikevich), dont 80 % excitateurs et 20 % inhibiteurs, posés sur une puce de 8 × 8 électrodes, avec des connexions surtout locales.
- **Plasticité** : les synapses excitatrices se renforcent ou s'affaiblissent selon l'ordre des impulsions (STDP). Une fatigue synaptique à court terme produit les bouffées d'activité typiques des vraies cultures, et une homéostasie empêche le réseau de s'emballer ou de s'éteindre.
- **Électrodes** : chacune enregistre les neurones tout proches. Une stimulation excite les neurones autour de l'électrode, et d'autant plus loin que le courant est fort.
- **Branchée sur le SDK officiel de Cortical Labs** ([cl-sdk](https://pypi.org/project/cl-sdk/)) comme source de données de son simulateur : le code de l'expérience utilise la même API que la vraie puce CL1, et pourrait tourner tel quel sur de vrais neurones.

### Le jeu

Pong à une raquette, contre un mur. Huit électrodes sensorielles au centre de la puce codent la balle : sa hauteur choisit l'électrode stimulée, sa distance règle la fréquence de stimulation. Deux zones motrices, « haut » et « bas », déplacent la raquette selon leur activité relative. Après une balle ratée, trois façons de réagir sont comparées : le retour de DishBrain (stimulation aléatoire pendant quelques secondes, et salve prévisible après chaque renvoi), le silence, ou rien du tout.

### La méthode

- Une **recette** combine une façon de réagir et dix réglages : courants, durées, fréquences, vitesse de la raquette, et deux hypothèses biologiques (fenêtre de plasticité, niveau d'activité visé par l'homéostasie). La première recette testée est le protocole publié de DishBrain.
- Chaque recette joue **16 minutes simulées sur 3 cultures** (1 minute d'échauffement, puis 15 minutes de jeu). Son **progrès** est le taux de balles renvoyées pendant les 5 dernières minutes, moins celui des 5 premières.
- **Recherche évolutionniste** : les meilleures recettes sont modifiées au hasard pour en créer de nouvelles, une partie des essais explore des recettes entièrement nouvelles, et l'IA locale, si elle est installée, propose de temps en temps une recette en expliquant l'hypothèse qu'elle teste.
- **Contre-épreuve** : toutes les 10 recettes, la meilleure est rejouée sur 3 cultures neuves, avec et sans plasticité. Un vrai apprentissage doit apparaître avec la plasticité, et pas sans.

### À garder en tête

1 000 neurones simulés ne sont pas des centaines de milliers de neurones vivants. Les résultats sont des hypothèses à tester sur du vrai matériel, pas des preuves biologiques.

## Matériel et coût

Le labo tourne dans un conteneur Linux sur un serveur domestique : 3 cœurs de processeur, pas de carte graphique, en priorité basse pour ne gêner personne. Tout est gratuit : données publiques de la NASA, logiciels libres, simulateur du SDK de Cortical Labs. Seule l'électricité coûte.

## Sources

- OPUS, PDS Ring-Moon Systems Node : https://opus.pds-rings.seti.org
- Kagan B. J. et al. (2022), *In vitro neurons learn and exhibit sentience when embodied in a simulated game-world*, Neuron 110(23). https://doi.org/10.1016/j.neuron.2022.09.001
- Izhikevich E. M. (2003), *Simple model of spiking neurons*, IEEE Transactions on Neural Networks 14(6).
- Cortical Labs, cl-sdk : https://pypi.org/project/cl-sdk/ (licence CC BY-NC 4.0)
