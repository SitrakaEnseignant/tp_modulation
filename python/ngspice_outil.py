"""Lance un circuit du dossier ngspice/ et renvoie les courbes enregistrées.

Chaque circuit déclare ses valeurs modifiables par des lignes « .param NOM=valeur »
et enregistre ses courbes dans sortie.txt (commande wrdata). Les circuits restent
utilisables à la main : « cd ngspice && ngspice tp10_ne555_fm.cir ».
"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from common import RACINE, ngspice_disponible

DOSSIER = RACINE / "ngspice"


class NgspiceErreur(RuntimeError):
    pass


def lance(circuit, pas=None, **params):
    """Renvoie (t, [courbe1, courbe2, ...]) rééchantillonnées au pas `pas` (s) si demandé."""
    texte = (DOSSIER / circuit).read_text(encoding="utf-8")
    for nom, val in params.items():
        texte, n = re.subn(rf"^\.param\s+{nom}\s*=.*$", f".param {nom}={val}", texte, flags=re.M | re.I)
        if n == 0:
            raise NgspiceErreur(f"paramètre {nom} absent de {circuit}")
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        shutil.copytree(DOSSIER / "modeles", d / "modeles")
        (d / "circuit.cir").write_text(texte, encoding="utf-8")
        p = subprocess.run(["ngspice", "-b", "circuit.cir"], cwd=d, capture_output=True, text=True, timeout=900)
        f = d / "sortie.txt"
        if not f.exists():
            raise NgspiceErreur(f"{circuit} : pas de résultat\n{p.stdout[-3000:]}\n{p.stderr[-3000:]}")
        data = np.loadtxt(f)
    t = data[:, 0]
    courbes = [data[:, k] for k in range(1, data.shape[1], 2)]
    # ngspice peut répéter un instant : on garde des temps strictement croissants
    ok = np.concatenate([[True], np.diff(t) > 0])
    t = t[ok]
    courbes = [c[ok] for c in courbes]
    if pas:
        tt = np.arange(t[0], t[-1], pas)
        courbes = [np.interp(tt, t, c) for c in courbes]
        t = tt
    return t, courbes


disponible = ngspice_disponible
