"""TP05 – PWM, maquette Excel Technologies ET-PWM (AF 1 kHz, horloge 8 kHz)."""
import numpy as np

from common import Resultat, CONFIRME, ECART, INDETERMINE, INFO, fmt, fr, nouvelle_figure, sauve
import pwm

TITRE = "PWM – Excel Technologies ET-PWM (1 kHz / 8 kHz)"


def run(outdir):
    r = Resultat(5, TITRE, "Modèle comportemental (Python) : modulateur à rampe synchronisée sur l'horloge 8 kHz.")
    fm, fs = 1e3, 8e3
    r.check("Impulsions par période du message", "AF 1 kHz, horloge 8 kHz", f"{fr(fs/fm)} impulsions de période {fmt(1/fs,'s')}", CONFIRME)
    res = []
    for fc in (1.5e3, 2.67e3, 3.4e3):
        for o in (2, 4):
            *_, sd = pwm.essai(fm, fs, 0.8, 1.0, fc, o)
            res.append([fmt(fc, "Hz"), str(o), f"{fr(sd)} dB"])
    r.tableaux.append(("Démodulateur : SINAD selon le filtre (message 0,8 × rampe)", ["Coupure", "Ordre", "SINAD"], res))
    *_, sd = pwm.essai(fm, fs, 0.8, 1.0, 2.67e3, 4)
    r.check("Démodulation PWM par filtre passe-bas", "message 1 kHz récupéré", f"SINAD {fr(sd)} dB", CONFIRME if sd > 20 else ECART,
            "avec seulement 8 impulsions par période, un filtre d'ordre 4 est nécessaire pour un sinus propre")
    t, msg, p, y, _ = pwm.essai(fm, fs, 0.8, 1.0, 2.67e3, 4)
    m0 = p[t > 10e-3].mean()
    r.check("Valeur moyenne de la PWM", "—", f"{fmt(m0,'V')} (moitié de 5 V : rapport cyclique moyen 50 %)", INFO,
            "la composante continue est enlevée par le condensateur de liaison de la maquette")
    r.hypotheses += ["Rampe synchronisée sur l'horloge 8 kHz ; amplitude du message = 80 % de la rampe."]
    fig, ax = nouvelle_figure(1, 3, "TP05 – PWM 1 kHz / 8 kHz et message récupéré")
    k = (t > 10e-3) & (t < 12e-3)
    ax[0].plot((t[k]-10e-3)*1e3, p[k], lw=0.6, c="0.6", label="PWM")
    ax[0].plot((t[k]-10e-3)*1e3, y[k], lw=1.4, label="après filtre d'ordre 4")
    ax[0].legend(fontsize=7, loc="upper right"); ax[0].set_xlabel("t (ms)")
    sauve(fig, r, outdir, "tp05_pwm.png", "PWM 1 kHz / 8 kHz et démodulation")
    return r
