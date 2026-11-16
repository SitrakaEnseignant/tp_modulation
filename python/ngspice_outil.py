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
        m = re.search(r"^\.param\s+TSTOP\s*=\s*(\S+)", texte, flags=re.M | re.I)
        if m:
            tstop = _valeur(m.group(1))
            if data[-1, 0] < 0.98 * tstop:
                raise NgspiceErreur(f"{circuit} {params} : simulation arrêtée à {data[-1,0]:.4g} s sur {tstop:.4g} s\n"
                                    + p.stdout[-3000:] + "\n" + p.stderr[-3000:])
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


def _valeur(txt):
    """Convertit une valeur SPICE (3m, 0.1u, 10k...) en nombre."""
    suf = {"t": 1e12, "g": 1e9, "meg": 1e6, "k": 1e3, "m": 1e-3, "u": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15}
    m = re.match(r"([-+0-9.eE]+)([a-zA-Z]*)", txt)
    v = float(m.group(1))
    u = m.group(2).lower()
    for k in ("meg", "t", "g", "k", "m", "u", "n", "p", "f"):
        if u.startswith(k):
            return v * suf[k]
    return v


disponible = ngspice_disponible
