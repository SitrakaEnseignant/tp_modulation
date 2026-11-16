"""TP07 – Modulation de fréquence avec l'ICL8038."""
import numpy as np

from common import Resultat, CONFIRME, ECART, INDETERMINE, INFO, fmt, fr, ecart_pct, periodes_cycle, nouvelle_figure, sauve

TITRE = "FM avec le générateur de fonctions ICL8038"


def f_8038(RA, RB, C):
    """Fiche technique ICL8038, figure 5A."""
    return 1.0 / ((5.0 / 3.0) * RA * C * (1 + RB / (2 * RA - RB)))


def run(outdir):
    r = Resultat(7, TITRE, "Formule de la fiche technique + VCO comportemental (Python) : courants de charge "
                           "proportionnels à V+ − V(broche 8).")
    R, C = 10e3, 1e-9
    f0 = f_8038(R, R, C)
    r.check("Fréquence libre (RA = RB = 10 kΩ, C = 1 nF)", "f ≈ 0,3/(R·C) ≈ 30 kHz (calculé dans le cours)",
            fmt(f0, "Hz", 4), CONFIRME if abs(ecart_pct(f0, 0.3 / (R * C))) < 0.5 else ECART,
            "formule complète f = 1/[(5/3)·RA·C·(1 + RB/(2RA − RB))]")
    t1 = 5 / 3 * R * C
    t2 = 5 / 3 * R * R * C / (2 * R - R)
    r.check("Rapport cyclique avec RA = RB", "signal carré / triangle symétrique",
            f"t1 = {fmt(t1,'s')}, t2 = {fmt(t2,'s')} → {fr(100*t1/(t1+t2))} %", CONFIRME,
            "t1 = (5/3)·RA·C et t2 = (5/3)·RA·RB·C/(2RA − RB) : symétrique si RA = RB")

    # ---- VCO : f ∝ (V+ − V8), pour V+ − V8 = 0,2·Vs au repos (broches 7 et 8 reliées)
    Vs = 12.0
    d0 = 0.2 * Vs
    lignes = []
    for dv in (-1.0, -0.5, 0.0, 0.5, 1.0):
        f = f0 * (d0 - dv) / d0
        lignes.append([fr(dv), fmt(f, "Hz")])
    r.tableaux.append(("Caractéristique du VCO prédite : f en fonction de la variation de V(broche 8) (V+ = 12 V)",
                       ["ΔV broche 8 (V)", "f"], lignes))
    k = f0 / d0
    r.check("Sensibilité du VCO", "tableau V / f à compléter", f"K = f0/(0,2·Vs) = {fmt(k,'Hz')}/V", INFO,
            "la fréquence baisse quand la tension de la broche 8 monte vers V+")

    # ---- simulation FM : message 1 kHz, 0,5 V crête sur la broche 8
    fm, am = 1e3, 0.5
    fs = 20e6
    t = np.arange(0, 3e-3, 1 / fs)
    finst = f0 * (d0 - am * np.sin(2 * np.pi * fm * t)) / d0
    ph = 2 * np.pi * np.cumsum(finst) / fs
    tri = 2 / np.pi * np.arcsin(np.sin(ph))        # sortie triangle
    tc, per = periodes_cycle(np.sin(ph), t, 0.0)
    fc_ = 1 / per
    fmax, fmin = fc_.max(), fc_.min()
    dfm = fmax - f0
    r.check("Exemple : m(t) = 0,5 V crête à 1 kHz sur la broche 8", "fmax, fmin, Δf, β à calculer",
            f"fmax = {fmt(fmax,'Hz')} ; fmin = {fmt(fmin,'Hz')} ; Δf = {fmt(dfm,'Hz')} ; β = {fr(dfm/fm)}", INFO,
            "valeurs prédites pour remplir le tableau ; Δf = K·Am")
    r.check("Valeur 6,6 kΩ entre les broches 7 et 8", "lue 6,6 kΩ (peut-être 6,8 kΩ)", "6,6 kΩ n'est pas une valeur normalisée",
            INDETERMINE, "la série E12 contient 6,8 kΩ ; cette résistance règle la polarisation FM, pas f0 (écart < 3 %)")
    r.hypotheses += ["RA, RB et C réels non lisibles dans la vidéo : RA = RB = 10 kΩ, C = 1 nF supposés.",
                     "Alimentation 12 V ; broches 7 et 8 au repos à 0,2·Vs sous V+ (fiche technique).",
                     "VCO idéal et linéaire ; la fiche technique annonce une linéarité de l'ordre de 0,5 % sur une large plage."]

    fig, ax = nouvelle_figure(2, 2.6, "TP07 – ICL8038 en VCO : FM simulée (f0 = 30 kHz, m(t) = 0,5 V à 1 kHz)")
    kk = t < 1e-3
    ax[0].plot(t[kk]*1e3, tri[kk], lw=0.5); ax[0].set_title("Sortie triangle modulée", fontsize=9); ax[0].set_xlabel("t (ms)")
    ax[1].plot(tc*1e3, fc_/1e3, ".", ms=2); ax[1].set_ylabel("kHz"); ax[1].set_xlabel("t (ms)")
    ax[1].set_title("Fréquence de chaque cycle", fontsize=9)
    sauve(fig, r, outdir, "tp07_fm.png", "ICL8038 utilisé comme VCO")
    return r
