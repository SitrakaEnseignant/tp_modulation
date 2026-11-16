# Simulations des TP de modulation (AM, FM, PAM, PWM)

Ce dépôt vérifie par simulation les 13 TP de modulation tirés de vidéos YouTube.
Chaque simulation compare les valeurs relevées dans la vidéo avec ce que donne le calcul.

**Le rapport complet est dans [`results/RAPPORT.md`](results/RAPPORT.md).** GitHub Actions le met à jour à chaque modification.

## Ce que fait chaque simulation

| TP | Sujet | Méthode |
|---|---|---|
| 01 | AM, maquette Omega ETB-96 | signal AM, spectre, détecteur d'enveloppe diode/RC |
| 02 | FM, maquette VCO + PLL | lecture des fréquences cycle par cycle, Carson, démodulation |
| 03 | PAM naturel / S&H / flat-top, ST2110 | échantillonnage 8 à 64 kHz + filtre |
| 04 | PWM, ST2110 | comparateur message / rampe, largeurs, démodulation |
| 05 | PWM, Excel ET-PWM | 1 kHz / 8 kHz, choix du filtre |
| 06 | PWM, Akademika DCL-08 | régression sur les relevés, déphasage |
| 07 | FM avec ICL8038 | formule de la fiche technique, VCO |
| 08 | PAM, Excel | rôle de l'horloge unipolaire |
| 09 | Démodulation FM, LM565 | formules de la fiche technique, PLL |
| 10 | FM avec NE555 | simulation pas à pas du 555 avec diode |
| 11 | AM à transistor BC107 | **SPICE (ngspice)** du schéma complet |
| 12 | PAM et démodulation, ST2110 | 8 / 16 / 32 / 64 kHz, retard du filtre |
| 13 | PAM avancé, Vinytics | filtres d'ordre 2 et 4, coupure balayée |

Les statuts du rapport :

- ✅ **confirmé** : la simulation retrouve la valeur de la vidéo ;
- ❌ **écart** : la simulation contredit la vidéo (erreur de lecture, de calcul ou de composant) ;
- ⚠️ **à vérifier** : le résultat dépend d'une valeur que la vidéo ne montre pas ;
- ℹ️ **valeur prédite** : la vidéo laisse le tableau vide, la simulation le remplit.

Chaque TP liste ses hypothèses (valeurs supposées) à la fin de sa section.

## Lancer les simulations

Sur GitHub : onglet **Actions** → « Simulations des TP de modulation » → **Run workflow**.
On peut indiquer les numéros de TP (par exemple `1 10 11`) ou laisser vide pour les 13.

Sur un ordinateur :

```bash
pip install -r requirements.txt
sudo apt-get install ngspice      # seulement pour le TP11
python sim/run_all.py             # les 13 TP
python sim/run_all.py 10 11       # quelques TP
```

## Organisation

```
sim/common.py         outils de mesure (fréquence, crêtes, SINAD, filtres)
sim/pam.py, pwm.py    moteurs PAM et PWM partagés
sim/tpNN_*.py         une simulation par TP
sim/run_all.py        lance tout et écrit results/RAPPORT.md et results/resultats.json
spice/                netlist ngspice du TP11 et modèles BC107B / 1N4001
results/              rapport, figures et résultats JSON (écrits par GitHub Actions)
```
