# Labo de neurones : recettes d'entraÃ®nement

*Mis Ã  jour le 29/10/2026 Ã  03:12 UTC. ProgrÃ¨s = balles renvoyÃ©es pendant les 5 derniÃ¨res minutes de jeu, moins les 5 premiÃ¨res, en points, en moyenne sur 3 cultures.*

## La meilleure recette, minute par minute

![Courbe d'apprentissage](courbe-meilleure-recette.svg)

## Les 30 meilleures recettes

| nÂ° | Protocole | RÃ©glages | DÃ©but â†’ fin | ProgrÃ¨s | Contre-Ã©preuve |
|---:|---|---|---:|---:|---|
| 18 | retour prévisible / imprévisible (DishBrain)<br>*variante de la n°7* | stimulation 2,44 ÂµA de 7,5 Ã  47,85 Hz ; retour 0,93 ÂµA, 6 s Ã  13,79 Hz, salve de 8 ; raquette Ã—2,34 ; STDP 48,91 ms ; homÃ©ostasie 3 Hz | 20 % â†’ 32 % | **+12** | -3 avec plasticitÃ©, +3 sans : non reproduit |
| 55 | silence après une balle ratée<br>*variante de la n°31* | stimulation 1,54 ÂµA de 2,2 Ã  28,63 Hz ; retour 0,63 ÂµA, 4,87 s Ã  28,8 Hz, salve de 17 ; raquette Ã—1,5 ; STDP 71,99 ms ; homÃ©ostasie 1,37 Hz | 20 % â†’ 30 % | **+10** | +2 avec plasticitÃ©, +11 sans : non reproduit |
| 57 | silence après une balle ratée<br>*variante de la n°48* | stimulation 2,35 ÂµA de 5,54 Ã  46,88 Hz ; retour 1,21 ÂµA, 5,39 s Ã  13,79 Hz, salve de 9 ; raquette Ã—2,34 ; STDP 48,91 ms ; homÃ©ostasie 2,64 Hz | 19 % â†’ 29 % | **+10** | -6 avec plasticitÃ©, +1 sans : non reproduit |
| 69 | silence après une balle ratée<br>*variante de la n°57* | stimulation 2,35 ÂµA de 5,54 Ã  46,88 Hz ; retour 1,21 ÂµA, 5,39 s Ã  13,79 Hz, salve de 5 ; raquette Ã—2,34 ; STDP 48,91 ms ; homÃ©ostasie 2,64 Hz | 19 % â†’ 29 % | **+10** | â€“ |
| 48 | silence après une balle ratée<br>*variante de la n°21* | stimulation 2,35 ÂµA de 5,35 Ã  47,85 Hz ; retour 1,21 ÂµA, 5,39 s Ã  13,79 Hz, salve de 12 ; raquette Ã—2,34 ; STDP 48,91 ms ; homÃ©ostasie 2,46 Hz | 21 % â†’ 31 % | **+10** | -9 avec plasticitÃ©, -7 sans : non reproduit |
| 21 | silence après une balle ratée<br>*variante de la n°7* | stimulation 2,44 ÂµA de 5,26 Ã  47,85 Hz ; retour 0,93 ÂµA, 5,39 s Ã  13,79 Hz, salve de 12 ; raquette Ã—2,34 ; STDP 48,91 ms ; homÃ©ostasie 2,25 Hz | 19 % â†’ 28 % | **+10** | +2 avec plasticitÃ©, -3 sans : non reproduit |
| 63 | retour prévisible / imprévisible (DishBrain)<br>*variante de la n°18* | stimulation 2,44 ÂµA de 7,5 Ã  40,2 Hz ; retour 0,93 ÂµA, 6 s Ã  13,22 Hz, salve de 8 ; raquette Ã—2,34 ; STDP 48,09 ms ; homÃ©ostasie 3 Hz | 18 % â†’ 26 % | **+8** | â€“ |
| 60 | silence après une balle ratée<br>*variante de la n°57* | stimulation 2,35 ÂµA de 5,91 Ã  46,88 Hz ; retour 1,21 ÂµA, 4,1 s Ã  13,79 Hz, salve de 6 ; raquette Ã—1,9 ; STDP 48,91 ms ; homÃ©ostasie 2,64 Hz | 23 % â†’ 30 % | **+8** | â€“ |
| 31 | silence après une balle ratée<br>*tirée au hasard* | stimulation 1,73 ÂµA de 2,2 Ã  28,63 Hz ; retour 0,63 ÂµA, 4,87 s Ã  28,8 Hz, salve de 16 ; raquette Ã—1,5 ; STDP 75,55 ms ; homÃ©ostasie 1,37 Hz | 19 % â†’ 26 % | **+8** | +1 avec plasticitÃ©, -1 sans : non reproduit |
| 24 | retour prévisible / imprévisible (DishBrain)<br>*variante de la n°23* | stimulation 1,23 ÂµA de 2,86 Ã  37,32 Hz ; retour 0,71 ÂµA, 2,66 s Ã  12,47 Hz, salve de 9 ; raquette Ã—2 ; STDP 10 ms ; homÃ©ostasie 1,88 Hz | 25 % â†’ 32 % | **+8** | â€“ |
| 35 | silence après une balle ratée<br>*variante de la n°25* | stimulation 2,5 ÂµA de 9,79 Ã  39,72 Hz ; retour 0,3 ÂµA, 5,58 s Ã  6,25 Hz, salve de 1 ; raquette Ã—3,58 ; STDP 23,94 ms ; homÃ©ostasie 2,36 Hz | 23 % â†’ 30 % | **+7** | â€“ |
| 51 | silence après une balle ratée<br>*variante de la n°21* | stimulation 2,44 ÂµA de 5,26 Ã  47,85 Hz ; retour 0,93 ÂµA, 5,39 s Ã  13,79 Hz, salve de 12 ; raquette Ã—1,78 ; STDP 48,91 ms ; homÃ©ostasie 2,25 Hz | 21 % â†’ 28 % | **+7** | â€“ |
| 25 | silence après une balle ratée<br>*tirée au hasard* | stimulation 2,11 ÂµA de 8,52 Ã  39,72 Hz ; retour 0,71 ÂµA, 4,52 s Ã  6,25 Hz, salve de 1 ; raquette Ã—3,58 ; STDP 23,94 ms ; homÃ©ostasie 2,75 Hz | 21 % â†’ 28 % | **+7** | â€“ |
| 45 | silence après une balle ratée<br>*variante de la n°25* | stimulation 2,11 ÂµA de 8,52 Ã  39,72 Hz ; retour 0,71 ÂµA, 4,52 s Ã  8,22 Hz, salve de 1 ; raquette Ã—3,58 ; STDP 23,94 ms ; homÃ©ostasie 2,75 Hz | 21 % â†’ 28 % | **+7** | â€“ |
| 23 | retour prévisible / imprévisible (DishBrain)<br>*variante de la n°1* | stimulation 0,81 ÂµA de 2,86 Ã  40 Hz ; retour 0,71 ÂµA, 2,66 s Ã  12,47 Hz, salve de 9 ; raquette Ã—2 ; STDP 20 ms ; homÃ©ostasie 1,5 Hz | 22 % â†’ 29 % | **+7** | â€“ |
| 1 | retour prévisible / imprévisible (DishBrain)<br>*protocole DishBrain* | stimulation 1 ÂµA de 4 Ã  40 Hz ; retour 1 ÂµA, 4 s Ã  5 Hz, salve de 10 ; raquette Ã—2 ; STDP 20 ms ; homÃ©ostasie 1,5 Hz | 21 % â†’ 27 % | **+7** | +3 avec plasticitÃ©, -1 sans : non reproduit |
| 41 | silence après une balle ratée<br>*variante de la n°21* | stimulation 1,99 ÂµA de 5,26 Ã  47,85 Hz ; retour 0,93 ÂµA, 5,39 s Ã  19,08 Hz, salve de 5 ; raquette Ã—2,34 ; STDP 48,91 ms ; homÃ©ostasie 2,25 Hz | 19 % â†’ 26 % | **+6** | â€“ |
| 7 | silence après une balle ratée<br>*tirée au hasard* | stimulation 2,44 ÂµA de 7,5 Ã  47,85 Hz ; retour 0,93 ÂµA, 5,39 s Ã  13,79 Hz, salve de 8 ; raquette Ã—2,34 ; STDP 48,91 ms ; homÃ©ostasie 2,33 Hz | 22 % â†’ 28 % | **+6** | â€“ |
| 9 | retour prévisible / imprévisible (DishBrain)<br>*tirée au hasard* | stimulation 2,24 ÂµA de 3,05 Ã  48,76 Hz ; retour 1,71 ÂµA, 3,23 s Ã  18,99 Hz, salve de 11 ; raquette Ã—2,36 ; STDP 63,02 ms ; homÃ©ostasie 1,03 Hz | 20 % â†’ 26 % | **+6** | â€“ |
| 27 | silence après une balle ratée<br>*variante de la n°21* | stimulation 2,44 ÂµA de 5,26 Ã  34,23 Hz ; retour 0,6 ÂµA, 5,39 s Ã  13,79 Hz, salve de 12 ; raquette Ã—2,34 ; STDP 48,91 ms ; homÃ©ostasie 2,25 Hz | 21 % â†’ 26 % | **+6** | â€“ |
| 56 | silence après une balle ratée<br>*variante de la n°48* | stimulation 2,35 ÂµA de 7,32 Ã  47,85 Hz ; retour 1,4 ÂµA, 5,39 s Ã  14,23 Hz, salve de 13 ; raquette Ã—1,97 ; STDP 58,69 ms ; homÃ©ostasie 2,35 Hz | 24 % â†’ 30 % | **+6** | â€“ |
| 17 | silence après une balle ratée<br>*variante de la n°1* | stimulation 0,58 ÂµA de 4 Ã  40 Hz ; retour 1 ÂµA, 4 s Ã  12,44 Hz, salve de 10 ; raquette Ã—2 ; STDP 20 ms ; homÃ©ostasie 1,32 Hz | 22 % â†’ 28 % | **+6** | â€“ |
| 62 | retour prévisible / imprévisible (DishBrain)<br>*variante de la n°55* | stimulation 1,01 ÂµA de 4,33 Ã  28,63 Hz ; retour 0,64 ÂµA, 4,87 s Ã  28,8 Hz, salve de 17 ; raquette Ã—1,5 ; STDP 71,99 ms ; homÃ©ostasie 1,19 Hz | 26 % â†’ 31 % | **+6** | â€“ |
| 20 | retour prévisible / imprévisible (DishBrain)<br>*variante de la n°18* | stimulation 2,44 ÂµA de 7,5 Ã  47,85 Hz ; retour 0,92 ÂµA, 5,92 s Ã  11,07 Hz, salve de 8 ; raquette Ã—2,34 ; STDP 57,26 ms ; homÃ©ostasie 3 Hz | 24 % â†’ 29 % | **+5** | â€“ |
| 64 | retour prévisible / imprévisible (DishBrain)<br>*variante de la n°18* | stimulation 1,92 ÂµA de 7,5 Ã  47,85 Hz ; retour 1,22 ÂµA, 6 s Ã  13,79 Hz, salve de 8 ; raquette Ã—2,34 ; STDP 45,23 ms ; homÃ©ostasie 3 Hz | 23 % â†’ 28 % | **+5** | â€“ |
| 49 | silence après une balle ratée<br>*variante de la n°48* | stimulation 2,35 ÂµA de 5,35 Ã  47,85 Hz ; retour 1,19 ÂµA, 5,39 s Ã  13,79 Hz, salve de 12 ; raquette Ã—2,34 ; STDP 32,03 ms ; homÃ©ostasie 2,23 Hz | 29 % â†’ 33 % | **+4** | â€“ |
| 28 | silence après une balle ratée<br>*tirée au hasard* | stimulation 0,86 ÂµA de 3,41 Ã  31,89 Hz ; retour 2,49 ÂµA, 4,33 s Ã  16,55 Hz, salve de 4 ; raquette Ã—3,98 ; STDP 74,17 ms ; homÃ©ostasie 1,3 Hz | 26 % â†’ 31 % | **+4** | â€“ |
| 71 | retour prévisible / imprévisible (DishBrain)<br>*variante de la n°63* | stimulation 2,44 ÂµA de 6,76 Ã  40,2 Hz ; retour 0,93 ÂµA, 6 s Ã  13,22 Hz, salve de 8 ; raquette Ã—2,74 ; STDP 48,09 ms ; homÃ©ostasie 2,95 Hz | 20 % â†’ 24 % | **+4** | â€“ |
| 67 | silence après une balle ratée<br>*variante de la n°48* | stimulation 2,33 ÂµA de 4,67 Ã  47,85 Hz ; retour 1,21 ÂµA, 5,39 s Ã  13,79 Hz, salve de 8 ; raquette Ã—2,34 ; STDP 50,47 ms ; homÃ©ostasie 2,46 Hz | 27 % â†’ 30 % | **+4** | â€“ |
| 42 | silence après une balle ratée<br>*variante de la n°21* | stimulation 2,44 ÂµA de 5,26 Ã  50 Hz ; retour 0,93 ÂµA, 5,7 s Ã  13,79 Hz, salve de 12 ; raquette Ã—2,62 ; STDP 48,91 ms ; homÃ©ostasie 2,09 Hz | 24 % â†’ 27 % | **+3** | â€“ |

## Contre-Ã©preuves

Une contre-Ã©preuve rejoue une recette prometteuse sur 3 cultures neuves, avec et sans plasticitÃ©. Un vrai apprentissage doit apparaÃ®tre avec la plasticitÃ©, et pas sans.

| nÂ° | Protocole | RÃ©glages | DÃ©but â†’ fin | ProgrÃ¨s | Contre-Ã©preuve |
|---:|---|---|---:|---:|---|
| 1 | retour prévisible / imprévisible (DishBrain)<br>*protocole DishBrain* | stimulation 1 ÂµA de 4 Ã  40 Hz ; retour 1 ÂµA, 4 s Ã  5 Hz, salve de 10 ; raquette Ã—2 ; STDP 20 ms ; homÃ©ostasie 1,5 Hz | 21 % â†’ 27 % | **+7** | +3 avec plasticitÃ©, -1 sans : non reproduit |
| 18 | retour prévisible / imprévisible (DishBrain)<br>*variante de la n°7* | stimulation 2,44 ÂµA de 7,5 Ã  47,85 Hz ; retour 0,93 ÂµA, 6 s Ã  13,79 Hz, salve de 8 ; raquette Ã—2,34 ; STDP 48,91 ms ; homÃ©ostasie 3 Hz | 20 % â†’ 32 % | **+12** | -3 avec plasticitÃ©, +3 sans : non reproduit |
| 21 | silence après une balle ratée<br>*variante de la n°7* | stimulation 2,44 ÂµA de 5,26 Ã  47,85 Hz ; retour 0,93 ÂµA, 5,39 s Ã  13,79 Hz, salve de 12 ; raquette Ã—2,34 ; STDP 48,91 ms ; homÃ©ostasie 2,25 Hz | 19 % â†’ 28 % | **+10** | +2 avec plasticitÃ©, -3 sans : non reproduit |
| 31 | silence après une balle ratée<br>*tirée au hasard* | stimulation 1,73 ÂµA de 2,2 Ã  28,63 Hz ; retour 0,63 ÂµA, 4,87 s Ã  28,8 Hz, salve de 16 ; raquette Ã—1,5 ; STDP 75,55 ms ; homÃ©ostasie 1,37 Hz | 19 % â†’ 26 % | **+8** | +1 avec plasticitÃ©, -1 sans : non reproduit |
| 48 | silence après une balle ratée<br>*variante de la n°21* | stimulation 2,35 ÂµA de 5,35 Ã  47,85 Hz ; retour 1,21 ÂµA, 5,39 s Ã  13,79 Hz, salve de 12 ; raquette Ã—2,34 ; STDP 48,91 ms ; homÃ©ostasie 2,46 Hz | 21 % â†’ 31 % | **+10** | -9 avec plasticitÃ©, -7 sans : non reproduit |
| 55 | silence après une balle ratée<br>*variante de la n°31* | stimulation 1,54 ÂµA de 2,2 Ã  28,63 Hz ; retour 0,63 ÂµA, 4,87 s Ã  28,8 Hz, salve de 17 ; raquette Ã—1,5 ; STDP 71,99 ms ; homÃ©ostasie 1,37 Hz | 20 % â†’ 30 % | **+10** | +2 avec plasticitÃ©, +11 sans : non reproduit |
| 57 | silence après une balle ratée<br>*variante de la n°48* | stimulation 2,35 ÂµA de 5,54 Ã  46,88 Hz ; retour 1,21 ÂµA, 5,39 s Ã  13,79 Hz, salve de 9 ; raquette Ã—2,34 ; STDP 48,91 ms ; homÃ©ostasie 2,64 Hz | 19 % â†’ 29 % | **+10** | -6 avec plasticitÃ©, +1 sans : non reproduit |
