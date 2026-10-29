# Labo de neurones : recettes d'entraînement

*Mis à jour le 29/10/2026 à 01:32 UTC. Progrès = balles renvoyées pendant les 5 dernières minutes de jeu, moins les 5 premières, en points, en moyenne sur 3 cultures.*

## La meilleure recette, minute par minute

![Courbe d'apprentissage](courbe-meilleure-recette.svg)

## Les 30 meilleures recettes

| n° | Protocole | Réglages | Début → fin | Progrès | Contre-épreuve |
|---:|---|---|---:|---:|---|
| 18 | retour prévisible / imprévisible (DishBrain)<br>*variante de la n°7* | stimulation 2,44 µA de 7,5 à 47,85 Hz ; retour 0,93 µA, 6 s à 13,79 Hz, salve de 8 ; raquette ×2,34 ; STDP 48,91 ms ; homéostasie 3 Hz | 20 % → 32 % | **+12** | -3 avec plasticité, +3 sans : non reproduit |
| 55 | silence après une balle ratée<br>*variante de la n°31* | stimulation 1,54 µA de 2,2 à 28,63 Hz ; retour 0,63 µA, 4,87 s à 28,8 Hz, salve de 17 ; raquette ×1,5 ; STDP 71,99 ms ; homéostasie 1,37 Hz | 20 % → 30 % | **+10** | +2 avec plasticité, +11 sans : non reproduit |
| 57 | silence après une balle ratée<br>*variante de la n°48* | stimulation 2,35 µA de 5,54 à 46,88 Hz ; retour 1,21 µA, 5,39 s à 13,79 Hz, salve de 9 ; raquette ×2,34 ; STDP 48,91 ms ; homéostasie 2,64 Hz | 19 % → 29 % | **+10** | – |
| 48 | silence après une balle ratée<br>*variante de la n°21* | stimulation 2,35 µA de 5,35 à 47,85 Hz ; retour 1,21 µA, 5,39 s à 13,79 Hz, salve de 12 ; raquette ×2,34 ; STDP 48,91 ms ; homéostasie 2,46 Hz | 21 % → 31 % | **+10** | -9 avec plasticité, -7 sans : non reproduit |
| 21 | silence après une balle ratée<br>*variante de la n°7* | stimulation 2,44 µA de 5,26 à 47,85 Hz ; retour 0,93 µA, 5,39 s à 13,79 Hz, salve de 12 ; raquette ×2,34 ; STDP 48,91 ms ; homéostasie 2,25 Hz | 19 % → 28 % | **+10** | +2 avec plasticité, -3 sans : non reproduit |
| 60 | silence après une balle ratée<br>*variante de la n°57* | stimulation 2,35 µA de 5,91 à 46,88 Hz ; retour 1,21 µA, 4,1 s à 13,79 Hz, salve de 6 ; raquette ×1,9 ; STDP 48,91 ms ; homéostasie 2,64 Hz | 23 % → 30 % | **+8** | – |
| 31 | silence après une balle ratée<br>*tirée au hasard* | stimulation 1,73 µA de 2,2 à 28,63 Hz ; retour 0,63 µA, 4,87 s à 28,8 Hz, salve de 16 ; raquette ×1,5 ; STDP 75,55 ms ; homéostasie 1,37 Hz | 19 % → 26 % | **+8** | +1 avec plasticité, -1 sans : non reproduit |
| 24 | retour prévisible / imprévisible (DishBrain)<br>*variante de la n°23* | stimulation 1,23 µA de 2,86 à 37,32 Hz ; retour 0,71 µA, 2,66 s à 12,47 Hz, salve de 9 ; raquette ×2 ; STDP 10 ms ; homéostasie 1,88 Hz | 25 % → 32 % | **+8** | – |
| 35 | silence après une balle ratée<br>*variante de la n°25* | stimulation 2,5 µA de 9,79 à 39,72 Hz ; retour 0,3 µA, 5,58 s à 6,25 Hz, salve de 1 ; raquette ×3,58 ; STDP 23,94 ms ; homéostasie 2,36 Hz | 23 % → 30 % | **+7** | – |
| 51 | silence après une balle ratée<br>*variante de la n°21* | stimulation 2,44 µA de 5,26 à 47,85 Hz ; retour 0,93 µA, 5,39 s à 13,79 Hz, salve de 12 ; raquette ×1,78 ; STDP 48,91 ms ; homéostasie 2,25 Hz | 21 % → 28 % | **+7** | – |
| 25 | silence après une balle ratée<br>*tirée au hasard* | stimulation 2,11 µA de 8,52 à 39,72 Hz ; retour 0,71 µA, 4,52 s à 6,25 Hz, salve de 1 ; raquette ×3,58 ; STDP 23,94 ms ; homéostasie 2,75 Hz | 21 % → 28 % | **+7** | – |
| 45 | silence après une balle ratée<br>*variante de la n°25* | stimulation 2,11 µA de 8,52 à 39,72 Hz ; retour 0,71 µA, 4,52 s à 8,22 Hz, salve de 1 ; raquette ×3,58 ; STDP 23,94 ms ; homéostasie 2,75 Hz | 21 % → 28 % | **+7** | – |
| 23 | retour prévisible / imprévisible (DishBrain)<br>*variante de la n°1* | stimulation 0,81 µA de 2,86 à 40 Hz ; retour 0,71 µA, 2,66 s à 12,47 Hz, salve de 9 ; raquette ×2 ; STDP 20 ms ; homéostasie 1,5 Hz | 22 % → 29 % | **+7** | – |
| 1 | retour prévisible / imprévisible (DishBrain)<br>*protocole DishBrain* | stimulation 1 µA de 4 à 40 Hz ; retour 1 µA, 4 s à 5 Hz, salve de 10 ; raquette ×2 ; STDP 20 ms ; homéostasie 1,5 Hz | 21 % → 27 % | **+7** | +3 avec plasticité, -1 sans : non reproduit |
| 41 | silence après une balle ratée<br>*variante de la n°21* | stimulation 1,99 µA de 5,26 à 47,85 Hz ; retour 0,93 µA, 5,39 s à 19,08 Hz, salve de 5 ; raquette ×2,34 ; STDP 48,91 ms ; homéostasie 2,25 Hz | 19 % → 26 % | **+6** | – |
| 7 | silence après une balle ratée<br>*tirée au hasard* | stimulation 2,44 µA de 7,5 à 47,85 Hz ; retour 0,93 µA, 5,39 s à 13,79 Hz, salve de 8 ; raquette ×2,34 ; STDP 48,91 ms ; homéostasie 2,33 Hz | 22 % → 28 % | **+6** | – |
| 9 | retour prévisible / imprévisible (DishBrain)<br>*tirée au hasard* | stimulation 2,24 µA de 3,05 à 48,76 Hz ; retour 1,71 µA, 3,23 s à 18,99 Hz, salve de 11 ; raquette ×2,36 ; STDP 63,02 ms ; homéostasie 1,03 Hz | 20 % → 26 % | **+6** | – |
| 27 | silence après une balle ratée<br>*variante de la n°21* | stimulation 2,44 µA de 5,26 à 34,23 Hz ; retour 0,6 µA, 5,39 s à 13,79 Hz, salve de 12 ; raquette ×2,34 ; STDP 48,91 ms ; homéostasie 2,25 Hz | 21 % → 26 % | **+6** | – |
| 56 | silence après une balle ratée<br>*variante de la n°48* | stimulation 2,35 µA de 7,32 à 47,85 Hz ; retour 1,4 µA, 5,39 s à 14,23 Hz, salve de 13 ; raquette ×1,97 ; STDP 58,69 ms ; homéostasie 2,35 Hz | 24 % → 30 % | **+6** | – |
| 17 | silence après une balle ratée<br>*variante de la n°1* | stimulation 0,58 µA de 4 à 40 Hz ; retour 1 µA, 4 s à 12,44 Hz, salve de 10 ; raquette ×2 ; STDP 20 ms ; homéostasie 1,32 Hz | 22 % → 28 % | **+6** | – |
| 20 | retour prévisible / imprévisible (DishBrain)<br>*variante de la n°18* | stimulation 2,44 µA de 7,5 à 47,85 Hz ; retour 0,92 µA, 5,92 s à 11,07 Hz, salve de 8 ; raquette ×2,34 ; STDP 57,26 ms ; homéostasie 3 Hz | 24 % → 29 % | **+5** | – |
| 49 | silence après une balle ratée<br>*variante de la n°48* | stimulation 2,35 µA de 5,35 à 47,85 Hz ; retour 1,19 µA, 5,39 s à 13,79 Hz, salve de 12 ; raquette ×2,34 ; STDP 32,03 ms ; homéostasie 2,23 Hz | 29 % → 33 % | **+4** | – |
| 28 | silence après une balle ratée<br>*tirée au hasard* | stimulation 0,86 µA de 3,41 à 31,89 Hz ; retour 2,49 µA, 4,33 s à 16,55 Hz, salve de 4 ; raquette ×3,98 ; STDP 74,17 ms ; homéostasie 1,3 Hz | 26 % → 31 % | **+4** | – |
| 42 | silence après une balle ratée<br>*variante de la n°21* | stimulation 2,44 µA de 5,26 à 50 Hz ; retour 0,93 µA, 5,7 s à 13,79 Hz, salve de 12 ; raquette ×2,62 ; STDP 48,91 ms ; homéostasie 2,09 Hz | 24 % → 27 % | **+3** | – |
| 44 | silence après une balle ratée<br>*variante de la n°21* | stimulation 2,36 µA de 5,26 à 45,58 Hz ; retour 0,93 µA, 5,39 s à 13,92 Hz, salve de 12 ; raquette ×2,34 ; STDP 48,91 ms ; homéostasie 2,25 Hz | 25 % → 29 % | **+3** | – |
| 22 | silence après une balle ratée<br>*variante de la n°7* | stimulation 2,44 µA de 7,5 à 46,05 Hz ; retour 0,93 µA, 5,39 s à 13,79 Hz, salve de 8 ; raquette ×2,34 ; STDP 39,24 ms ; homéostasie 1,89 Hz | 27 % → 29 % | **+3** | – |
| 14 | retour prévisible / imprévisible (DishBrain)<br>*variante de la n°9* | stimulation 2,24 µA de 3,35 à 43,85 Hz ; retour 1,45 µA, 3,23 s à 19,33 Hz, salve de 9 ; raquette ×2,36 ; STDP 64,62 ms ; homéostasie 1,36 Hz | 24 % → 26 % | **+2** | – |
| 53 | silence après une balle ratée<br>*variante de la n°21* | stimulation 2,5 µA de 5,26 à 48,61 Hz ; retour 0,93 µA, 5,39 s à 15,43 Hz, salve de 12 ; raquette ×2,2 ; STDP 32,51 ms ; homéostasie 2,25 Hz | 26 % → 28 % | **+2** | – |
| 40 | retour prévisible / imprévisible (DishBrain)<br>*variante de la n°18* | stimulation 2,02 µA de 7,5 à 39,06 Hz ; retour 0,93 µA, 6 s à 13,79 Hz, salve de 8 ; raquette ×2,39 ; STDP 44,35 ms ; homéostasie 3 Hz | 22 % → 24 % | **+2** | – |
| 13 | aucun retour<br>*variante de la n°8* | stimulation 2,16 µA de 4,95 à 34,52 Hz ; retour 1,05 µA, 4,09 s à 8,47 Hz, salve de 1 ; raquette ×2,57 ; STDP 65,93 ms ; homéostasie 1,83 Hz | 26 % → 28 % | **+2** | – |

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
