# Labo IA

**Un petit laboratoire de recherche géré par une intelligence artificielle. Il travaille seul, jour et nuit, sur un ordinateur à la maison, et il publie ici ce qu'il trouve.**

### En deux mots

1. **Sondes Fantômes : chercher l'image bizarre dans les archives de la NASA.** Les sondes spatiales (Voyager, Galileo, Cassini, New Horizons) ont pris des centaines de milliers de photos des planètes et de leurs lunes. Personne ne les a toutes regardées en détail. Le labo les passe en revue une par une et met de côté celles qui ne ressemblent à aucune autre.
2. **Labo de neurones : apprendre à des neurones à jouer à Pong.** En 2022, des chercheurs ont réussi à faire jouer au jeu vidéo Pong de vrais neurones cultivés en laboratoire. Personne ne sait vraiment pourquoi ça marche. Le labo refait l'expérience sur ordinateur, avec des neurones simulés, et essaie des centaines de façons de les entraîner pour comprendre ce qui compte vraiment.

Ce dépôt est son carnet de recherche. On y trouve où il en est et ce qu'il a trouvé (juste en dessous), [un rapport par jour](rapports/), tous les résultats ([images](resultats/sondes.md), [neurones](resultats/neurones.md)) et son [code source](code/labo/). Il se met à jour tout seul toutes les 6 heures.

## Où en est le labo

*Mis à jour automatiquement le 29/10/2026 à 03:53 UTC.*

| | |
|---|---:|
| Photos de la NASA passées en revue | 42 375 |
| Astres entièrement passés en revue | 50 sur 185 |
| Parties de Pong jouées par les neurones | 270 (72,0 h de jeu) |
| Façons d'entraîner essayées | 75 |
| Meilleur progrès observé, avant vérification | +12 points (recette n°18) |
| Progrès confirmés après vérification | 0 sur 7 |

**Les dernières photos bizarres repérées** (cliquer sur une photo ouvre sa fiche à la NASA) :

<a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=vg-iss-2-j-c2064928"><img src="https://opus.pds-rings.seti.org/holdings/previews/VGISS_5xxx/VGISS_5213/DATA/C20649XX/C2064928_small.jpg" width="110" alt="Europa, n°1" title="Europa, n°1"></a> <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=vg-iss-2-j-c2046905"><img src="https://opus.pds-rings.seti.org/holdings/previews/VGISS_5xxx/VGISS_5210/DATA/C20469XX/C2046905_small.jpg" width="110" alt="Europa, n°2" title="Europa, n°2"></a> <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=vg-iss-2-n-c1242957"><img src="https://opus.pds-rings.seti.org/holdings/previews/VGISS_8xxx/VGISS_8210/DATA/C12429XX/C1242957_small.jpg" width="110" alt="Star, n°1" title="Star, n°1"></a> <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=vg-iss-2-n-c1242706"><img src="https://opus.pds-rings.seti.org/holdings/previews/VGISS_8xxx/VGISS_8210/DATA/C12427XX/C1242706_small.jpg" width="110" alt="Star, n°2" title="Star, n°2"></a> <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=vg-iss-2-s-c4430317"><img src="https://opus.pds-rings.seti.org/holdings/previews/VGISS_6xxx/VGISS_6215/DATA/C44303XX/C4430317_small.jpg" width="110" alt="Phoebe, n°1" title="Phoebe, n°1"></a> <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=vg-iss-2-s-c4430137"><img src="https://opus.pds-rings.seti.org/holdings/previews/VGISS_6xxx/VGISS_6215/DATA/C44301XX/C4430137_small.jpg" width="110" alt="Phoebe, n°2" title="Phoebe, n°2"></a> <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=vg-iss-1-s-c3495037"><img src="https://opus.pds-rings.seti.org/holdings/previews/VGISS_6xxx/VGISS_6113/DATA/C34950XX/C3495037_small.jpg" width="110" alt="Rhea, n°1" title="Rhea, n°1"></a> <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=vg-iss-1-s-c3495057"><img src="https://opus.pds-rings.seti.org/holdings/previews/VGISS_6xxx/VGISS_6113/DATA/C34950XX/C3495057_small.jpg" width="110" alt="Rhea, n°2" title="Rhea, n°2"></a>

**La recette qui a le mieux marché (n°18)** : part des balles renvoyées, minute par minute, par des neurones qui apprennent (bleu) et par des neurones figés (gris) :

![Courbe d'apprentissage de la meilleure recette](resultats/courbe-meilleure-recette.svg)

Dernier rapport : [2026-10-29](rapports/2026-10-29.md)

## Ce que le labo a trouvé

### Sondes Fantômes : les photos les plus bizarres

Pour chaque astre, voici la photo qui ressemble le moins à toutes les autres. Ce sont des **pistes**, pas encore des découvertes : il faut un œil humain pour dire si c'est un simple défaut ou quelque chose d'intéressant. Cliquer sur une photo ouvre sa fiche à la NASA. Les 10 pistes de chaque astre sont dans [les résultats complets](resultats/sondes.md).

| Astre (appareil photo) | Photo la plus bizarre | Comparée à | Prise le |
|---|---|---:|---|
| Enceladus (Cassini ISS) | <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=co-iss-w1745432624"><img src="https://opus.pds-rings.seti.org/holdings/previews/COISS_2xxx/COISS_2082/data/1745365751_1745606282/W1745432624_1_small.jpg" width="90" alt="Enceladus, n°1" title="Enceladus, n°1"></a> | 9 762 autres photos | 2013-04-23 |
| Earth (Galileo SSI) | <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=go-ssi-c0166212400"><img src="https://opus.pds-rings.seti.org/holdings/previews/GO_0xxx/GO_0015/GOPEX/C0166212400R_small.jpg" width="90" alt="Earth, n°1" title="Earth, n°1"></a> | 5 677 autres photos | 1992-12-16 |
| Pluto (New Horizons LORRI) | <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=nh-lorri-lor_0299179751"><img src="https://opus.pds-rings.seti.org/holdings/previews/NHxxLO_xxxx/NHPELO_1001/data/20150714_029917/lor_0299179751_0x636_eng_small.jpg" width="90" alt="Pluto, n°1" title="Pluto, n°1"></a> | 5 366 autres photos | 2015-07-14 |
| Arrokoth (New Horizons LORRI) | <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=nh-lorri-lor_0408624843"><img src="https://opus.pds-rings.seti.org/holdings/previews/NHxxLO_xxxx/NHKELO_1001/data/20190101_040862/lor_0408624843_0x630_eng_small.jpg" width="90" alt="Arrokoth, n°1" title="Arrokoth, n°1"></a> | 4 342 autres photos | 2019-01-01 |
| Moon (Galileo SSI) | <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=go-ssi-c0060959300"><img src="https://opus.pds-rings.seti.org/holdings/previews/GO_0xxx/GO_0003/MOON/C0060959300R_small.jpg" width="90" alt="Moon, n°1" title="Moon, n°1"></a> | 1 986 autres photos | 1990-12-08 |
| Hyperion (Cassini ISS) | <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=co-iss-w1692998324"><img src="https://opus.pds-rings.seti.org/holdings/previews/COISS_2xxx/COISS_2069/data/1692994130_1693342058/W1692998324_1_small.jpg" width="90" alt="Hyperion, n°1" title="Hyperion, n°1"></a> | 1 705 autres photos | 2011-08-25 |
| Jupiter (Galileo SSI) | <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=go-ssi-c0164408700"><img src="https://opus.pds-rings.seti.org/holdings/previews/GO_0xxx/GO_0008/RAW_CAL/C0164408700R_small.jpg" width="90" alt="Jupiter, n°1" title="Jupiter, n°1"></a> | 1 450 autres photos | 1992-12-03 |
| Black Sky (Galileo SSI) | <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=go-ssi-c0062302800"><img src="https://opus.pds-rings.seti.org/holdings/previews/GO_0xxx/GO_0006/RAW_CAL/C0062302800R_small.jpg" width="90" alt="Black Sky, n°1" title="Black Sky, n°1"></a> | 1 185 autres photos | 1990-12-17 |
| Io (Galileo SSI) | <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=go-ssi-c0450101100"><img src="https://opus.pds-rings.seti.org/holdings/previews/GO_0xxx/GO_0020/E15/IO/C0450101100R_small.jpg" width="90" alt="Io, n°1" title="Io, n°1"></a> | 840 autres photos | 1998-06-01 |
| Europa (Galileo SSI) | <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=go-ssi-c0389773000"><img src="https://opus.pds-rings.seti.org/holdings/previews/GO_0xxx/GO_0018/G7/EUROPA/C0389773000R_small.jpg" width="90" alt="Europa, n°1" title="Europa, n°1"></a> | 699 autres photos | 1997-04-04 |

### Labo de neurones : ce qui marche vraiment

**Pour l'instant, aucune façon d'entraîner les neurones n'a passé la vérification.** Le labo a rejoué ses 7 meilleures recettes sur des neurones neufs. 7 fois, le progrès a disparu. 0 fois, des neurones figés, incapables d'apprendre, ont progressé tout autant.

Autrement dit : les beaux scores du début venaient surtout de la chance, pas d'un vrai apprentissage. Ce n'est pas un échec : c'est un vrai résultat, qui montre qu'il ne faut pas croire un bon score sans le vérifier. Le labo continue de chercher.

## Mission 1 : Sondes Fantômes

### L'idée

Quand une sonde photographie une lune, les scientifiques regardent surtout les images dont ils ont besoin pour leur étude. Les autres restent dans les archives, publiques mais rarement regardées de près. Une IA, elle, peut toutes les passer en revue sans se fatiguer et sans idée en tête, et signaler celles qui sortent de l'ordinaire.

### Comment ça marche, simplement

1. Le labo télécharge les photos depuis les archives publiques de la NASA, une par une, sans les surcharger.
2. Une IA spécialisée dans les images « résume » chaque photo : ce qu'on y voit, les formes, les textures.
3. Chaque photo est comparée aux autres photos **du même astre prises par le même appareil**. Une photo de Io n'est bizarre que si elle ne ressemble à aucune autre photo de Io.
4. Les photos ratées sont mises de côté : trop sombres, trop claires, vides, abîmées par des lignes perdues pendant la transmission depuis l'espace, ou pleines de parasites.
5. Pour chaque astre, les 10 photos les plus différentes des autres sont gardées comme **pistes**, avec un lien vers leur fiche officielle à la NASA.

### Ce qu'il faut savoir

Une photo bizarre n'est pas forcément une découverte. Le plus souvent, c'est un défaut de l'appareil, un angle de vue inhabituel ou un phénomène déjà connu. Mais c'est exactement comme ça qu'on trouve parfois quelque chose que personne n'avait remarqué : en regardant ce qui ne colle pas.

<details>
<summary><b>Détails techniques</b></summary>

1. **Les données** viennent de l'API publique [OPUS](https://opus.pds-rings.seti.org) du PDS Ring-Moon Systems Node (NASA). Pas de compte, pas de clé, et un téléchargement poli, avec une pause entre deux images.
2. **Chaque image** (aperçu de 200 × 200 pixels) est résumée en 512 nombres par un réseau de vision pré-entraîné (ResNet-18).
3. **Une image n'est étrange que par rapport à ses semblables** : elle est comparée seulement aux autres images de la même cible prises par le même instrument. Deux mesures sont combinées : la distance moyenne à ses 10 plus proches voisines, et un score d'Isolation Forest calculé sur une réduction à 32 dimensions.
4. **Les images ratées sont écartées** : presque noires, saturées, uniformes, incomplètes (marges ou bandes sans données), striées de lignes brouillées, ou faites presque uniquement de bruit.
5. **Les 10 images les plus isolées de chaque groupe deviennent des candidates.** Si une IA locale est installée (Ollama avec gemma3:4b, gratuite et hors ligne), elle décrit chaque candidate et dit si cela ressemble à un défaut d'image, à quelque chose de connu, ou à quelque chose qui mérite d'être vérifié.

La fouille commence par huit cibles (Io, Europe, Miranda, Triton, Hypérion, Encelade, Pluton, Arrokoth), puis s'étend à toutes les cibles des cinq caméras, soit environ 560 000 images.

</details>

## Mission 2 : Labo de neurones

### L'idée

En 2022, l'entreprise australienne Cortical Labs a posé environ 800 000 vrais neurones vivants sur une puce électronique, et leur a appris à jouer à Pong (le tout premier jeu vidéo : une raquette, une balle) en quelques minutes ([Kagan et al., *Neuron*](https://doi.org/10.1016/j.neuron.2022.09.001)). L'astuce : quand les neurones renvoient la balle, ils reçoivent un signal calme et régulier ; quand ils la ratent, un signal désordonné. Les neurones semblent préférer le calme, et finissent par mieux jouer. Mais pourquoi exactement, les chercheurs en débattent encore.

Le labo refait cette expérience **sur ordinateur**, avec 1 000 neurones simulés, et sans jamais s'arrêter.

### Comment ça marche, simplement

- Une **recette** est une façon d'entraîner les neurones : quel signal envoyer, à quelle force, pendant combien de temps, etc.
- Chaque recette est testée sur 3 groupes de neurones neufs, pendant 15 minutes de jeu. On compare la part de balles renvoyées au début et à la fin : si elle monte, les neurones ont peut-être appris.
- Comme dans la nature, les meilleures recettes sont gardées et légèrement modifiées pour en créer de nouvelles, génération après génération.
- **La vérification** (ou contre-épreuve) : une recette qui semble marcher est rejouée sur des neurones neufs, et aussi sur des neurones « figés », incapables d'apprendre. Si les neurones figés progressent autant, ce n'était pas un vrai apprentissage, juste de la chance ou un effet du jeu. Seules les recettes qui passent ce test comptent.

### Ce qu'il faut savoir

1 000 neurones simulés, ce n'est pas un vrai cerveau ni une vraie culture de neurones. Ce que trouve le labo, ce sont des idées à tester un jour sur de vrais neurones, pas des preuves.

<details>
<summary><b>Détails techniques</b></summary>

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

</details>

## Matériel et coût

Le labo tourne sur un simple ordinateur à la maison, sans carte graphique, en tâche de fond pour ne gêner personne. Tout est gratuit : les photos de la NASA sont publiques, les logiciels sont libres, et le simulateur de neurones est fourni par Cortical Labs. Seule l'électricité coûte.

## Sources

- OPUS, PDS Ring-Moon Systems Node : https://opus.pds-rings.seti.org
- Kagan B. J. et al. (2022), *In vitro neurons learn and exhibit sentience when embodied in a simulated game-world*, Neuron 110(23). https://doi.org/10.1016/j.neuron.2022.09.001
- Izhikevich E. M. (2003), *Simple model of spiking neurons*, IEEE Transactions on Neural Networks 14(6).
- Cortical Labs, cl-sdk : https://pypi.org/project/cl-sdk/ (licence CC BY-NC 4.0)
