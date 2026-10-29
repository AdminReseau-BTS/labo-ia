# Labo IA

**Un laboratoire autonome qui tourne jour et nuit sur un serveur domestique, et qui publie ici ses recherches tout seul.**

Il poursuit deux missions :

1. **Sondes FantÃ´mes** : relire avec un Å“il neuf les centaines de milliers d'images prises par les sondes spatiales de la NASA (Voyager, Galileo, Cassini, New Horizons), pour faire remonter celles qui ne ressemblent Ã  aucune autre.
2. **Labo de neurones** : apprendre Ã  jouer Ã  Pong Ã  une culture de neurones simulÃ©s, sur le modÃ¨le de l'expÃ©rience DishBrain, en inventant et en testant lui-mÃªme des protocoles d'entraÃ®nement.

Ce dÃ©pÃ´t est son carnet de recherche : la prÃ©sentation ci-dessous, [un rapport par jour](rapports/), les rÃ©sultats complets ([Sondes FantÃ´mes](resultats/sondes.md), [neurones](resultats/neurones.md)) et le [code source](code/labo/). Il se met Ã  jour automatiquement toutes les 6 heures.

## OÃ¹ en est le labo

*Mis Ã  jour automatiquement le 29/10/2026 Ã  03:12 UTC.*

| Indicateur | Valeur |
|---|---:|
| Images d'archives analysÃ©es | 40 474 |
| Cibles entiÃ¨rement fouillÃ©es | 45 / 185 |
| Parties de Pong jouÃ©es | 254 (67,7 h de culture simulÃ©e) |
| Recettes d'entraÃ®nement testÃ©es | 70 |
| Meilleur progrÃ¨s (avant contre-Ã©preuve) | +12 points (recette nÂ°18) |
| Apprentissages confirmÃ©s par contre-Ã©preuve | 0 sur 7 |

**DerniÃ¨res candidates de Sondes FantÃ´mes** (cliquer pour ouvrir la fiche NASA) :

<a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=vg-iss-2-n-c1040802"><img src="https://opus.pds-rings.seti.org/holdings/previews/VGISS_8xxx/VGISS_8204/DATA/C10408XX/C1040802_small.jpg" width="110" alt="Nereid, nÂ°1" title="Nereid, nÂ°1"></a> <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=vg-iss-2-n-c1148555"><img src="https://opus.pds-rings.seti.org/holdings/previews/VGISS_8xxx/VGISS_8208/DATA/C11485XX/C1148555_small.jpg" width="110" alt="Nereid, nÂ°2" title="Nereid, nÂ°2"></a> <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=vg-iss-2-s-c4372931"><img src="https://opus.pds-rings.seti.org/holdings/previews/VGISS_6xxx/VGISS_6211/DATA/C43729XX/C4372931_small.jpg" width="110" alt="Iapetus, nÂ°1" title="Iapetus, nÂ°1"></a> <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=vg-iss-2-s-c4372947"><img src="https://opus.pds-rings.seti.org/holdings/previews/VGISS_6xxx/VGISS_6211/DATA/C43729XX/C4372947_small.jpg" width="110" alt="Iapetus, nÂ°2" title="Iapetus, nÂ°2"></a> <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=vg-iss-1-s-c3470145"><img src="https://opus.pds-rings.seti.org/holdings/previews/VGISS_6xxx/VGISS_6111/DATA/C34701XX/C3470145_small.jpg" width="110" alt="Dione, nÂ°1" title="Dione, nÂ°1"></a> <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=vg-iss-1-s-c3494824"><img src="https://opus.pds-rings.seti.org/holdings/previews/VGISS_6xxx/VGISS_6113/DATA/C34948XX/C3494824_small.jpg" width="110" alt="Dione, nÂ°2" title="Dione, nÂ°2"></a> <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=vg-iss-2-s-c4382128"><img src="https://opus.pds-rings.seti.org/holdings/previews/VGISS_6xxx/VGISS_6212/DATA/C43821XX/C4382128_small.jpg" width="110" alt="Hyperion, nÂ°1" title="Hyperion, nÂ°1"></a> <a href="https://opus.pds-rings.seti.org/opus/#/view=detail&amp;detail=vg-iss-2-s-c4397223"><img src="https://opus.pds-rings.seti.org/holdings/previews/VGISS_6xxx/VGISS_6213/DATA/C43972XX/C4397223_small.jpg" width="110" alt="Hyperion, nÂ°2" title="Hyperion, nÂ°2"></a>

**Meilleure recette (nÂ°18)**, balles renvoyÃ©es minute par minute :

![Courbe d'apprentissage de la meilleure recette](resultats/courbe-meilleure-recette.svg)

Dernier rapport : [2026-10-29](rapports/2026-10-29.md)

## Mission 1 : Sondes FantÃ´mes

### L'idÃ©e

Les archives planÃ©taires publiques contiennent des centaines de milliers d'images. La plupart n'ont Ã©tÃ© regardÃ©es que pour la raison prÃ©cise pour laquelle elles avaient Ã©tÃ© prises. Une IA peut toutes les passer en revue, sans fatigue et sans idÃ©e prÃ©conÃ§ue, et signaler celles qui sortent du lot. Ce ne sont pas des dÃ©couvertes, mais des images qui mÃ©ritent un regard humain.

### Comment Ã§a marche

1. **Les donnÃ©es** viennent de l'API publique [OPUS](https://opus.pds-rings.seti.org) du PDS Ring-Moon Systems Node (NASA). Pas de compte, pas de clÃ©, et un tÃ©lÃ©chargement poli, avec une pause entre deux images.
2. **Chaque image** (aperÃ§u de 200 Ã— 200 pixels) est rÃ©sumÃ©e en 512 nombres par un rÃ©seau de vision prÃ©-entraÃ®nÃ© (ResNet-18).
3. **Une image n'est Ã©trange que par rapport Ã  ses semblables** : elle est comparÃ©e seulement aux autres images de la mÃªme cible prises par le mÃªme instrument. Deux mesures sont combinÃ©es : la distance moyenne Ã  ses 10 plus proches voisines, et un score d'Isolation Forest calculÃ© sur une rÃ©duction Ã  32 dimensions.
4. **Les images ratÃ©es sont Ã©cartÃ©es** : presque noires, saturÃ©es, uniformes, incomplÃ¨tes (marges ou bandes sans donnÃ©es), ou faites presque uniquement de bruit.
5. **Les 10 images les plus isolÃ©es de chaque groupe deviennent des candidates.** Si une IA locale est installÃ©e (Ollama avec gemma3:4b, gratuite et hors ligne), elle dÃ©crit chaque candidate et dit si cela ressemble Ã  un dÃ©faut d'image, Ã  quelque chose de connu, ou Ã  quelque chose qui mÃ©rite d'Ãªtre vÃ©rifiÃ©.

La fouille commence par huit cibles (Io, Europe, Miranda, Triton, HypÃ©rion, Encelade, Pluton, Arrokoth), puis s'Ã©tend Ã  toutes les cibles des cinq camÃ©ras, soit environ 560 000 images.

### Ã€ garder en tÃªte

La plupart des anomalies seront des effets d'instrument, des prises de vue inhabituelles ou des phÃ©nomÃ¨nes dÃ©jÃ  connus. Chaque candidate renvoie vers sa fiche OPUS et ses mÃ©tadonnÃ©es complÃ¨tes, pour pouvoir vÃ©rifier.

## Mission 2 : Labo de neurones

### L'idÃ©e

En 2022, l'entreprise Cortical Labs a montrÃ© (expÃ©rience DishBrain, [Kagan et al., *Neuron*](https://doi.org/10.1016/j.neuron.2022.09.001)) que des neurones vivants cultivÃ©s sur une puce d'Ã©lectrodes apprennent Ã  jouer Ã  Pong en quelques minutes. La recette : une stimulation prÃ©visible quand ils renvoient la balle, et une stimulation imprÃ©visible quand ils la ratent. Pourquoi cela marche reste dÃ©battu.

Ce labo rejoue l'expÃ©rience en simulation, sans arrÃªt, pour chercher quels protocoles d'entraÃ®nement et quels mÃ©canismes biologiques rendent cet apprentissage possible.

### La culture virtuelle

- **1 000 neurones impulsionnels** (modÃ¨le d'Izhikevich), dont 80 % excitateurs et 20 % inhibiteurs, posÃ©s sur une puce de 8 Ã— 8 Ã©lectrodes, avec des connexions surtout locales.
- **PlasticitÃ©** : les synapses excitatrices se renforcent ou s'affaiblissent selon l'ordre des impulsions (STDP). Une fatigue synaptique Ã  court terme produit les bouffÃ©es d'activitÃ© typiques des vraies cultures, et une homÃ©ostasie empÃªche le rÃ©seau de s'emballer ou de s'Ã©teindre.
- **Ã‰lectrodes** : chacune enregistre les neurones tout proches. Une stimulation excite les neurones autour de l'Ã©lectrode, et d'autant plus loin que le courant est fort.
- **BranchÃ©e sur le SDK officiel de Cortical Labs** ([cl-sdk](https://pypi.org/project/cl-sdk/)) comme source de donnÃ©es de son simulateur : le code de l'expÃ©rience utilise la mÃªme API que la vraie puce CL1, et pourrait tourner tel quel sur de vrais neurones.

### Le jeu

Pong Ã  une raquette, contre un mur. Huit Ã©lectrodes sensorielles au centre de la puce codent la balle : sa hauteur choisit l'Ã©lectrode stimulÃ©e, sa distance rÃ¨gle la frÃ©quence de stimulation. Deux zones motrices, Â« haut Â» et Â« bas Â», dÃ©placent la raquette selon leur activitÃ© relative. AprÃ¨s une balle ratÃ©e, trois faÃ§ons de rÃ©agir sont comparÃ©es : le retour de DishBrain (stimulation alÃ©atoire pendant quelques secondes, et salve prÃ©visible aprÃ¨s chaque renvoi), le silence, ou rien du tout.

### La mÃ©thode

- Une **recette** combine une faÃ§on de rÃ©agir et dix rÃ©glages : courants, durÃ©es, frÃ©quences, vitesse de la raquette, et deux hypothÃ¨ses biologiques (fenÃªtre de plasticitÃ©, niveau d'activitÃ© visÃ© par l'homÃ©ostasie). La premiÃ¨re recette testÃ©e est le protocole publiÃ© de DishBrain.
- Chaque recette joue **16 minutes simulÃ©es sur 3 cultures** (1 minute d'Ã©chauffement, puis 15 minutes de jeu). Son **progrÃ¨s** est le taux de balles renvoyÃ©es pendant les 5 derniÃ¨res minutes, moins celui des 5 premiÃ¨res.
- **Recherche Ã©volutionniste** : les meilleures recettes sont modifiÃ©es au hasard pour en crÃ©er de nouvelles, une partie des essais explore des recettes entiÃ¨rement nouvelles, et l'IA locale, si elle est installÃ©e, propose de temps en temps une recette en expliquant l'hypothÃ¨se qu'elle teste.
- **Contre-Ã©preuve** : toutes les 10 recettes, la meilleure est rejouÃ©e sur 3 cultures neuves, avec et sans plasticitÃ©. Un vrai apprentissage doit apparaÃ®tre avec la plasticitÃ©, et pas sans.

### Ã€ garder en tÃªte

1 000 neurones simulÃ©s ne sont pas des centaines de milliers de neurones vivants. Les rÃ©sultats sont des hypothÃ¨ses Ã  tester sur du vrai matÃ©riel, pas des preuves biologiques.

## MatÃ©riel et coÃ»t

Le labo tourne dans un conteneur Linux sur un serveur domestique : 3 cÅ“urs de processeur, pas de carte graphique, en prioritÃ© basse pour ne gÃªner personne. Tout est gratuit : donnÃ©es publiques de la NASA, logiciels libres, simulateur du SDK de Cortical Labs. Seule l'Ã©lectricitÃ© coÃ»te.

## Sources

- OPUS, PDS Ring-Moon Systems Node : https://opus.pds-rings.seti.org
- Kagan B. J. et al. (2022), *In vitro neurons learn and exhibit sentience when embodied in a simulated game-world*, Neuron 110(23). https://doi.org/10.1016/j.neuron.2022.09.001
- Izhikevich E. M. (2003), *Simple model of spiking neurons*, IEEE Transactions on Neural Networks 14(6).
- Cortical Labs, cl-sdk : https://pypi.org/project/cl-sdk/ (licence CC BY-NC 4.0)
