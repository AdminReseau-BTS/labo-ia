# Labo de neurones : recettes d'entraînement

*Mis à jour le 29/10/2026 à 09:15 UTC. Progrès = balles renvoyées pendant les 5 dernières minutes de jeu, moins les 5 premières, en points, en moyenne sur 3 cultures.*

## La meilleure recette, minute par minute

![Courbe d'apprentissage](courbe-meilleure-recette.svg)

## Les 30 meilleures recettes

| n° | Protocole | Réglages | Début → fin | Progrès | Contre-épreuve |
|---:|---|---|---:|---:|---|
| 18 | retour prévisible / imprévisible (DishBrain)<br>*variante de la n°7* | stimulation 2,44 µA de 7,5 à 47,85 Hz ; retour 0,93 µA, 6 s à 13,79 Hz, salve de 8 ; raquette ×2,34 ; STDP 48,91 ms ; homéostasie 3 Hz | 20 % → 32 % | **+12** | -3 avec plasticité, +3 sans : non reproduit |
| 86 | silence après une balle ratée<br>*variante de la n°57* | stimulation 2,34 µA de 5,54 à 50 Hz ; retour 1,41 µA, 6 s à 13,79 Hz, salve de 9 ; raquette ×2,34 ; STDP 49,67 ms ; homéostasie 2,64 Hz | 23 % → 34 % | **+11** | -7 avec plasticité, +1 sans : non reproduit |
| 88 | silence après une balle ratée<br>*variante de la n°86* | stimulation 2,05 µA de 5,54 à 41,67 Hz ; retour 1,41 µA, 6 s à 13,79 Hz, salve de 9 ; raquette ×1,76 ; STDP 49,67 ms ; homéostasie 2,64 Hz | 21 % → 32 % | **+11** | +1 avec plasticité, -6 sans : non reproduit |
| 55 | silence après une balle ratée<br>*variante de la n°31* | stimulation 1,54 µA de 2,2 à 28,63 Hz ; retour 0,63 µA, 4,87 s à 28,8 Hz, salve de 17 ; raquette ×1,5 ; STDP 71,99 ms ; homéostasie 1,37 Hz | 20 % → 30 % | **+10** | +2 avec plasticité, +11 sans : non reproduit |
| 57 | silence après une balle ratée<br>*variante de la n°48* | stimulation 2,35 µA de 5,54 à 46,88 Hz ; retour 1,21 µA, 5,39 s à 13,79 Hz, salve de 9 ; raquette ×2,34 ; STDP 48,91 ms ; homéostasie 2,64 Hz | 19 % → 29 % | **+10** | -6 avec plasticité, +1 sans : non reproduit |
| 69 | silence après une balle ratée<br>*variante de la n°57* | stimulation 2,35 µA de 5,54 à 46,88 Hz ; retour 1,21 µA, 5,39 s à 13,79 Hz, salve de 5 ; raquette ×2,34 ; STDP 48,91 ms ; homéostasie 2,64 Hz | 19 % → 29 % | **+10** | -3 avec plasticité, -1 sans : non reproduit |
| 92 | silence après une balle ratée<br>*variante de la n°48* | stimulation 2,35 µA de 5,35 à 50 Hz ; retour 1,21 µA, 5,66 s à 13,79 Hz, salve de 12 ; raquette ×2,34 ; STDP 47,27 ms ; homéostasie 2,81 Hz | 22 % → 32 % | **+10** | – |
| 48 | silence après une balle ratée<br>*variante de la n°21* | stimulation 2,35 µA de 5,35 à 47,85 Hz ; retour 1,21 µA, 5,39 s à 13,79 Hz, salve de 12 ; raquette ×2,34 ; STDP 48,91 ms ; homéostasie 2,46 Hz | 21 % → 31 % | **+10** | -9 avec plasticité, -7 sans : non reproduit |
| 101 | silence après une balle ratée<br>*variante de la n°88* | stimulation 2,02 µA de 7,44 à 41,67 Hz ; retour 1,41 µA, 6 s à 13,79 Hz, salve de 9 ; raquette ×2,13 ; STDP 49,67 ms ; homéostasie 2,64 Hz | 19 % → 29 % | **+10** | – |
| 21 | silence après une balle ratée<br>*variante de la n°7* | stimulation 2,44 µA de 5,26 à 47,85 Hz ; retour 0,93 µA, 5,39 s à 13,79 Hz, salve de 12 ; raquette ×2,34 ; STDP 48,91 ms ; homéostasie 2,25 Hz | 19 % → 28 % | **+10** | +2 avec plasticité, -3 sans : non reproduit |
| 90 | silence après une balle ratée<br>*variante de la n°55* | stimulation 1,56 µA de 2 à 21,62 Hz ; retour 1,17 µA, 4,87 s à 28,8 Hz, salve de 17 ; raquette ×0,72 ; STDP 71,99 ms ; homéostasie 1,37 Hz | 23 % → 31 % | **+9** | – |
| 106 | silence après une balle ratée<br>*variante de la n°86* | stimulation 1,83 µA de 5,54 à 50 Hz ; retour 1,41 µA, 6 s à 13,79 Hz, salve de 9 ; raquette ×2,58 ; STDP 33,79 ms ; homéostasie 2,84 Hz | 22 % → 31 % | **+8** | – |
| 63 | retour prévisible / imprévisible (DishBrain)<br>*variante de la n°18* | stimulation 2,44 µA de 7,5 à 40,2 Hz ; retour 0,93 µA, 6 s à 13,22 Hz, salve de 8 ; raquette ×2,34 ; STDP 48,09 ms ; homéostasie 3 Hz | 18 % → 26 % | **+8** | – |
| 60 | silence après une balle ratée<br>*variante de la n°57* | stimulation 2,35 µA de 5,91 à 46,88 Hz ; retour 1,21 µA, 4,1 s à 13,79 Hz, salve de 6 ; raquette ×1,9 ; STDP 48,91 ms ; homéostasie 2,64 Hz | 23 % → 30 % | **+8** | – |
| 31 | silence après une balle ratée<br>*tirée au hasard* | stimulation 1,73 µA de 2,2 à 28,63 Hz ; retour 0,63 µA, 4,87 s à 28,8 Hz, salve de 16 ; raquette ×1,5 ; STDP 75,55 ms ; homéostasie 1,37 Hz | 19 % → 26 % | **+8** | +1 avec plasticité, -1 sans : non reproduit |
| 24 | retour prévisible / imprévisible (DishBrain)<br>*variante de la n°23* | stimulation 1,23 µA de 2,86 à 37,32 Hz ; retour 0,71 µA, 2,66 s à 12,47 Hz, salve de 9 ; raquette ×2 ; STDP 10 ms ; homéostasie 1,88 Hz | 25 % → 32 % | **+8** | – |
| 96 | silence après une balle ratée<br>*variante de la n°92* | stimulation 2,35 µA de 5,35 à 50 Hz ; retour 0,97 µA, 6 s à 13,5 Hz, salve de 14 ; raquette ×2,26 ; STDP 50,08 ms ; homéostasie 3 Hz | 22 % → 29 % | **+7** | – |
| 35 | silence après une balle ratée<br>*variante de la n°25* | stimulation 2,5 µA de 9,79 à 39,72 Hz ; retour 0,3 µA, 5,58 s à 6,25 Hz, salve de 1 ; raquette ×3,58 ; STDP 23,94 ms ; homéostasie 2,36 Hz | 23 % → 30 % | **+7** | – |
| 94 | silence après une balle ratée<br>*variante de la n°69* | stimulation 2,35 µA de 7,67 à 40,65 Hz ; retour 1,15 µA, 5,39 s à 19,55 Hz, salve de 1 ; raquette ×2,49 ; STDP 48,91 ms ; homéostasie 2,64 Hz | 25 % → 32 % | **+7** | – |
| 51 | silence après une balle ratée<br>*variante de la n°21* | stimulation 2,44 µA de 5,26 à 47,85 Hz ; retour 0,93 µA, 5,39 s à 13,79 Hz, salve de 12 ; raquette ×1,78 ; STDP 48,91 ms ; homéostasie 2,25 Hz | 21 % → 28 % | **+7** | – |
| 25 | silence après une balle ratée<br>*tirée au hasard* | stimulation 2,11 µA de 8,52 à 39,72 Hz ; retour 0,71 µA, 4,52 s à 6,25 Hz, salve de 1 ; raquette ×3,58 ; STDP 23,94 ms ; homéostasie 2,75 Hz | 21 % → 28 % | **+7** | – |
| 45 | silence après une balle ratée<br>*variante de la n°25* | stimulation 2,11 µA de 8,52 à 39,72 Hz ; retour 0,71 µA, 4,52 s à 8,22 Hz, salve de 1 ; raquette ×3,58 ; STDP 23,94 ms ; homéostasie 2,75 Hz | 21 % → 28 % | **+7** | – |
| 23 | retour prévisible / imprévisible (DishBrain)<br>*variante de la n°1* | stimulation 0,81 µA de 2,86 à 40 Hz ; retour 0,71 µA, 2,66 s à 12,47 Hz, salve de 9 ; raquette ×2 ; STDP 20 ms ; homéostasie 1,5 Hz | 22 % → 29 % | **+7** | – |
| 1 | retour prévisible / imprévisible (DishBrain)<br>*protocole DishBrain* | stimulation 1 µA de 4 à 40 Hz ; retour 1 µA, 4 s à 5 Hz, salve de 10 ; raquette ×2 ; STDP 20 ms ; homéostasie 1,5 Hz | 21 % → 27 % | **+7** | +3 avec plasticité, -1 sans : non reproduit |
| 76 | silence après une balle ratée<br>*variante de la n°55* | stimulation 1,54 µA de 2,2 à 33,8 Hz ; retour 0,61 µA, 6 s à 28,8 Hz, salve de 16 ; raquette ×1,5 ; STDP 56,43 ms ; homéostasie 1,37 Hz | 23 % → 29 % | **+7** | – |
| 102 | silence après une balle ratée<br>*variante de la n°88* | stimulation 2,15 µA de 5,54 à 41,67 Hz ; retour 1,41 µA, 6 s à 10,43 Hz, salve de 9 ; raquette ×1,33 ; STDP 53,43 ms ; homéostasie 2,64 Hz | 24 % → 30 % | **+6** | – |
| 41 | silence après une balle ratée<br>*variante de la n°21* | stimulation 1,99 µA de 5,26 à 47,85 Hz ; retour 0,93 µA, 5,39 s à 19,08 Hz, salve de 5 ; raquette ×2,34 ; STDP 48,91 ms ; homéostasie 2,25 Hz | 19 % → 26 % | **+6** | – |
| 7 | silence après une balle ratée<br>*tirée au hasard* | stimulation 2,44 µA de 7,5 à 47,85 Hz ; retour 0,93 µA, 5,39 s à 13,79 Hz, salve de 8 ; raquette ×2,34 ; STDP 48,91 ms ; homéostasie 2,33 Hz | 22 % → 28 % | **+6** | – |
| 75 | silence après une balle ratée<br>*variante de la n°48* | stimulation 2,5 µA de 6,65 à 47,85 Hz ; retour 1,21 µA, 5,5 s à 13,79 Hz, salve de 12 ; raquette ×2,4 ; STDP 48,91 ms ; homéostasie 2,44 Hz | 19 % → 25 % | **+6** | – |
| 9 | retour prévisible / imprévisible (DishBrain)<br>*tirée au hasard* | stimulation 2,24 µA de 3,05 à 48,76 Hz ; retour 1,71 µA, 3,23 s à 18,99 Hz, salve de 11 ; raquette ×2,36 ; STDP 63,02 ms ; homéostasie 1,03 Hz | 20 % → 26 % | **+6** | – |

## Contre-épreuves

Une contre-épreuve rejoue une recette prometteuse sur 3 cultures neuves, avec et sans plasticité. Un vrai apprentissage doit apparaître avec la plasticité, et pas sans.

| n° | Protocole | Réglages | Début → fin | Progrès | Contre-épreuve |
|---:|---|---|---:|---:|---|
| 1 | retour prévisible / imprévisible (DishBrain)<br>*protocole DishBrain* | stimulation 1 µA de 4 à 40 Hz ; retour 1 µA, 4 s à 5 Hz, salve de 10 ; raquette ×2 ; STDP 20 ms ; homéostasie 1,5 Hz | 21 % → 27 % | **+7** | +3 avec plasticité, -1 sans : non reproduit |
| 18 | retour prévisible / imprévisible (DishBrain)<br>*variante de la n°7* | stimulation 2,44 µA de 7,5 à 47,85 Hz ; retour 0,93 µA, 6 s à 13,79 Hz, salve de 8 ; raquette ×2,34 ; STDP 48,91 ms ; homéostasie 3 Hz | 20 % → 32 % | **+12** | -3 avec plasticité, +3 sans : non reproduit |
| 21 | silence après une balle ratée<br>*variante de la n°7* | stimulation 2,44 µA de 5,26 à 47,85 Hz ; retour 0,93 µA, 5,39 s à 13,79 Hz, salve de 12 ; raquette ×2,34 ; STDP 48,91 ms ; homéostasie 2,25 Hz | 19 % → 28 % | **+10** | +2 avec plasticité, -3 sans : non reproduit |
| 31 | silence après une balle ratée<br>*tirée au hasard* | stimulation 1,73 µA de 2,2 à 28,63 Hz ; retour 0,63 µA, 4,87 s à 28,8 Hz, salve de 16 ; raquette ×1,5 ; STDP 75,55 ms ; homéostasie 1,37 Hz | 19 % → 26 % | **+8** | +1 avec plasticité, -1 sans : non reproduit |
| 48 | silence après une balle ratée<br>*variante de la n°21* | stimulation 2,35 µA de 5,35 à 47,85 Hz ; retour 1,21 µA, 5,39 s à 13,79 Hz, salve de 12 ; raquette ×2,34 ; STDP 48,91 ms ; homéostasie 2,46 Hz | 21 % → 31 % | **+10** | -9 avec plasticité, -7 sans : non reproduit |
| 55 | silence après une balle ratée<br>*variante de la n°31* | stimulation 1,54 µA de 2,2 à 28,63 Hz ; retour 0,63 µA, 4,87 s à 28,8 Hz, salve de 17 ; raquette ×1,5 ; STDP 71,99 ms ; homéostasie 1,37 Hz | 20 % → 30 % | **+10** | +2 avec plasticité, +11 sans : non reproduit |
| 57 | silence après une balle ratée<br>*variante de la n°48* | stimulation 2,35 µA de 5,54 à 46,88 Hz ; retour 1,21 µA, 5,39 s à 13,79 Hz, salve de 9 ; raquette ×2,34 ; STDP 48,91 ms ; homéostasie 2,64 Hz | 19 % → 29 % | **+10** | -6 avec plasticité, +1 sans : non reproduit |
| 69 | silence après une balle ratée<br>*variante de la n°57* | stimulation 2,35 µA de 5,54 à 46,88 Hz ; retour 1,21 µA, 5,39 s à 13,79 Hz, salve de 5 ; raquette ×2,34 ; STDP 48,91 ms ; homéostasie 2,64 Hz | 19 % → 29 % | **+10** | -3 avec plasticité, -1 sans : non reproduit |
| 86 | silence après une balle ratée<br>*variante de la n°57* | stimulation 2,34 µA de 5,54 à 50 Hz ; retour 1,41 µA, 6 s à 13,79 Hz, salve de 9 ; raquette ×2,34 ; STDP 49,67 ms ; homéostasie 2,64 Hz | 23 % → 34 % | **+11** | -7 avec plasticité, +1 sans : non reproduit |
| 88 | silence après une balle ratée<br>*variante de la n°86* | stimulation 2,05 µA de 5,54 à 41,67 Hz ; retour 1,41 µA, 6 s à 13,79 Hz, salve de 9 ; raquette ×1,76 ; STDP 49,67 ms ; homéostasie 2,64 Hz | 21 % → 32 % | **+11** | +1 avec plasticité, -6 sans : non reproduit |
