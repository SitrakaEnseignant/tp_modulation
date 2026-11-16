"""Outils communs aux simulations des 13 TP de modulation.

Chaque module tpNN_*.py expose une fonction run(outdir) qui renvoie un
dictionnaire « résultat » construit avec Resultat ci-dessous.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path

import numpy as np
from scipy import signal

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# Statuts possibles d'une vérification
CONFIRME = "CONFIRMÉ"          # la simulation retrouve la valeur de la vidéo
ECART = "ÉCART"                # la simulation contredit la valeur de la vidéo
INDETERMINE = "À VÉRIFIER"     # le résultat dépend d'une hypothèse non connue
INFO = "INFO"                  # valeur prédite (tableau vide dans la vidéo)

# Statuts d'un doute
LEVE = "levé"
REDUIT = "réduit"
RESTE = "reste"

LIENS = {
    1: "YkTwZO9ub90", 2: "D5Se6hQdWQA", 3: "vzdANFkMhSQ", 4: "MSSf-RjRAB4",
    5: "MGXgkWwaYSs", 6: "Q6VduGGqPRE", 7: "eaoYraDUfKk", 8: "eeunlmRM_LA",
    9: "3HIn2Pt3ySg", 10: "xSqwbJl5yzU", 11: "51hQ_KS0t9I", 12: "tbTM0nnaiV4",
    13: "OZSDbqnP3Wo",
}


@dataclass
class Check:
    nom: str
    video: str
    simulation: str
    statut: str
    commentaire: str = ""


@dataclass
class Resultat:
    tp: int
    titre: str
    methode: str
    checks: list = field(default_factory=list)
    hypotheses: list = field(default_factory=list)
    figures: list = field(default_factory=list)
    tableaux: list = field(default_factory=list)   # (titre, entêtes, lignes)
    doutes: list = field(default_factory=list)     # {doute, statut, explication}

    def check(self, nom, video, simulation, statut, commentaire=""):
        self.checks.append(Check(nom, str(video), str(simulation), statut, commentaire))

    def doute(self, doute, statut, explication):
        self.doutes.append({"doute": doute, "statut": statut, "explication": explication})

    def to_dict(self):
        d = asdict(self)
        d["lien"] = f"https://www.youtube.com/watch?v={LIENS[self.tp]}"
        return d


# ----------------------------------------------------------------- mesures

def ecart_pct(sim, ref):
    return 100.0 * (sim - ref) / ref


def statut_tol(sim, ref, tol_pct):
    return CONFIRME if abs(ecart_pct(sim, ref)) <= tol_pct else ECART


def zero_crossings(x, t, level=0.0):
    """Instants des passages montants par `level` (interpolation linéaire)."""
    y = x - level
    i = np.where((y[:-1] < 0) & (y[1:] >= 0))[0]
    frac = -y[i] / (y[i + 1] - y[i])
    return t[i] + frac * (t[i + 1] - t[i])


def freq_moyenne(x, t, level=None):
    if level is None:
        level = 0.5 * (np.max(x) + np.min(x))
    zc = zero_crossings(x, t, level)
    if len(zc) < 2:
        return float("nan")
    return (len(zc) - 1) / (zc[-1] - zc[0])


def periodes_cycle(x, t, level=None):
    """Période de chaque cycle (comme une lecture aux curseurs sur un oscilloscope)."""
    if level is None:
        level = 0.5 * (np.max(x) + np.min(x))
    zc = zero_crossings(x, t, level)
    return zc[1:], np.diff(zc)


def cretes_par_cycle(x, t, f_porteuse):
    """Valeur crête de chaque cycle de porteuse (enveloppe vue à l'oscilloscope)."""
    n = max(3, int(round(1.0 / (f_porteuse * (t[1] - t[0])) * 0.6)))
    pk, _ = signal.find_peaks(x, distance=n)
    return t[pk], x[pk]


def ajuste_sinus(y, t, f):
    """Ajustement moindres carrés y ≈ a·sin + b·cos + c ; renvoie amplitude, phase, résidu."""
    M = np.column_stack([np.sin(2 * np.pi * f * t), np.cos(2 * np.pi * f * t), np.ones_like(t)])
    coef, *_ = np.linalg.lstsq(M, y, rcond=None)
    fit = M @ coef
    amp = float(np.hypot(coef[0], coef[1]))
    phase = float(np.arctan2(coef[1], coef[0]))
    return amp, phase, y - fit, fit


def sinad_db(y, t, f):
    """SINAD (dB) du signal y par rapport à un sinus de fréquence f (gain, phase, continu libres)."""
    amp, _, res, _ = ajuste_sinus(y, t, f)
    p_sig = amp ** 2 / 2
    p_err = float(np.mean(res ** 2)) + 1e-30
    return 10 * np.log10(p_sig / p_err)


def passe_bas(x, fs, fc, ordre=4):
    sos = signal.butter(ordre, fc, btype="low", fs=fs, output="sos")
    return signal.sosfilt(sos, x)


def spectre(x, fs, fenetre=True):
    """Spectre d'amplitude (V crête). Sans fenêtre si x contient un nombre entier de périodes."""
    n = len(x)
    w = np.hanning(n) if fenetre else np.ones(n)
    X = np.fft.rfft(x * w) / (np.sum(w) / 2)
    f = np.fft.rfftfreq(n, 1 / fs)
    return f, np.abs(X)


# ----------------------------------------------------------------- figures

def nouvelle_figure(n=1, h=3.0, titre=None):
    fig, axes = plt.subplots(n, 1, figsize=(9, h * n), squeeze=False)
    if titre:
        fig.suptitle(titre, fontsize=11, fontweight="bold")
    for a in axes[:, 0]:
        a.grid(True, alpha=0.3)
    return fig, axes[:, 0]


def sauve(fig, res: Resultat, outdir: Path, nom: str, legende: str):
    outdir.mkdir(parents=True, exist_ok=True)
    p = outdir / nom
    fig.tight_layout()
    fig.savefig(p, dpi=110)
    plt.close(fig)
    res.figures.append({"fichier": f"figures/{nom}", "legende": legende})


def fmt(x, unite="", nd=3):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    a = abs(x)
    if a < 1e-12:
        return f"0 {unite}".strip()
    pref = [(1e6, "M"), (1e3, "k"), (1, ""), (1e-3, "m"), (1e-6, "µ"), (1e-9, "n")]
    if unite in ("Hz", "s", "V", "Ω", "F", "H"):
        for k, p in pref:
            if a >= k or k == 1e-9:
                v = x / k
                s = f"{v:.{nd}g}".replace(".", ",")
                return f"{s} {p}{unite}"
    s = f"{x:.{nd}g}".replace(".", ",")
    return f"{s} {unite}".strip()


def ngspice_disponible():
    from shutil import which
    return which("ngspice") is not None


def ecrire_json(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


RACINE = Path(os.environ.get("TP_RACINE", Path(__file__).resolve().parent.parent))


def detecteur_enveloppe(vin, dt, R, C, vd=0.2, rs=500.0):
    """Détecteur d'enveloppe diode + RC (diode à seuil vd et résistance série rs).

    Intégration d'Euler explicite ; dt doit être petit devant rs·C.
    """
    v = 0.0
    out = np.empty_like(vin)
    inv_c = dt / C
    inv_r = 1.0 / R
    inv_rs = 1.0 / rs
    for k, x in enumerate(vin):
        d = x - v - vd
        i = d * inv_rs if d > 0 else 0.0
        v += (i - v * inv_r) * inv_c
        out[k] = v
    return out


def fr(x, nd=3):
    """Nombre au format français (virgule décimale)."""
    return f"{x:.{nd}g}".replace(".", ",")
