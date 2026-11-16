"""TP13 – PAM avancé, maquette Vinytics CT-PAM ADV (filtres d'ordre 2 et 4)."""
import numpy as np

from common import Resultat, CONFIRME, ECART, INDETERMINE, INFO, fmt, fr, ecart_pct, nouvelle_figure, sauve
import pam

TITRE = "PAM avancé – Vinytics CT-PAM ADV (fs 2 à 64 kHz, filtres d'ordre 2 et 4)"
FS = [2e3, 4e3, 8e3, 16e3, 32e3, 64e3]
FC_TEST = [1.5e3, 2e3, 2.5e3, 3e3, 3.4e3, 4e3, 5e3]


def run(outdir):
    r = Resultat(13, TITRE, "Modèle comportemental (Python) : PAM naturel + filtres de Butterworth d'ordre 2 et 4 ; "
                            "balayage de la fréquence de coupure inconnue.")
    r.check("Fréquence du générateur", "réglé sur 1 kHz, mesuré 959 Hz", f"écart {fr(ecart_pct(959, 1000),2)} %", INFO,
            "écart du générateur de la maquette (réglage du potentiomètre), sans effet sur la conclusion")

    def sd(fs, o, fc):
        return pam.essai(1e3, fs, "naturel", 0.5, fc, o)[-1]

    compat, compat_strict = [], []
    for fc in FC_TEST:
        a = {(o, fs): sd(fs, o, fc) for o in (2, 4) for fs in (4e3, 16e3, 32e3, 64e3)}
        ok = (a[(2, 64e3)] >= 30 and a[(2, 32e3)] >= 30 and a[(4, 16e3)] >= 30
              and a[(2, 4e3)] < 20 and a[(4, 4e3)] < 20)
        if ok:
            compat.append(fc)
            if a[(2, 16e3)] < 30:
                compat_strict.append(fc)
    rng = lambda L: f"{fmt(min(L),'Hz')} à {fmt(max(L),'Hz')}" if L else "aucune"
    r.check("Résultats annoncés (ordre 2 correct à 64/32 kHz, ordre 4 correct à 16 kHz, dégradé à 4 kHz)",
            "annoncés dans la vidéo", f"reproduits pour une coupure de {rng(compat)}",
            CONFIRME if compat else ECART,
            f"si l'on exige aussi que l'ordre 2 ne suffise plus à 16 kHz (raison du passage à l'ordre 4) : {rng(compat_strict)}")
    fc_ref = compat_strict[len(compat_strict)//2] if compat_strict else 3e3

    lignes = []
    for fs in FS:
        s2, s4 = sd(fs, 2, fc_ref), sd(fs, 4, fc_ref)
        lignes.append([fmt(fs, "Hz"), f"{pam.txt_sinad(s2)} ({pam.qualite(s2)})", f"{pam.txt_sinad(s4)} ({pam.qualite(s4)})"])
    r.tableaux.append((f"Message 1 kHz récupéré, coupure {fmt(fc_ref,'Hz')} (simulation)",
                       ["fs", "Filtre d'ordre 2", "Filtre d'ordre 4"], lignes))
    r.check("fs = 2 kHz (limite de Nyquist pour 1 kHz)", "non commenté", "fs = 2·fm : échantillons à phase fixe, message non récupérable",
            INFO, "il faut fs > 2·fm, et en pratique fs ≥ 4 à 8·fm avec un filtre réel")
    r.check("fs = 4 kHz : image à fs − fm = 3 kHz", "signal dégradé", "image trop proche de 1 kHz pour être filtrée", CONFIRME)
    r.hypotheses += ["Fréquence de coupure des filtres de la maquette inconnue : balayée de 1,5 à 5 kHz.",
                     "Type de filtre : Butterworth ; rapport cyclique 50 % ; seuils SINAD 30 dB / 20 dB."]

    fig, ax = nouvelle_figure(3, 2.3, f"TP13 – Message 1 kHz récupéré (coupure {fmt(fc_ref,'Hz')})")
    for a, (fs, o) in zip(ax, [(32e3, 2), (16e3, 4), (4e3, 4)]):
        t, msg, p, y, s_ = pam.essai(1e3, fs, "naturel", 0.5, fc_ref, o)
        k = (t > 10e-3) & (t < 13e-3)
        a.plot((t[k]-10e-3)*1e3, p[k], lw=0.5, c="0.7"); a.plot((t[k]-10e-3)*1e3, y[k], lw=1.3)
        a.set_title(f"fs = {fmt(fs,'Hz')}, filtre d'ordre {o} : {pam.qualite(s_)} ({pam.txt_sinad(s_)})", fontsize=9)
        a.set_xlabel("t (ms)")
    sauve(fig, r, outdir, "tp13_pam.png", "Effet de fs et de l'ordre du filtre sur le message récupéré")
    return r
