"""TP04 – PWM, maquette Scientech ST2110."""
import numpy as np

from common import Resultat, CONFIRME, ECART, INDETERMINE, INFO, fmt, fr, nouvelle_figure, sauve
import pwm

TITRE = "PWM – Scientech ST2110 (comparateur message / rampe)"
FS, FM, AR = 8e3, 1e3, 2.5


def run(outdir):
    r = Resultat(4, TITRE, "Modèle comportemental (Python) : comparateur entre le message et une rampe, "
                           "démodulation par filtre passe-bas.")
    Ts = 1 / FS
    lignes = []
    ok_formule = True
    for A in (0.5, 1.0, 1.5, 2.0):
        t, msg, p, y, sd = pwm.essai(FM, FS, A, AR)
        tt, w = pwm.largeurs(p, t)
        w = w[tt > 2e-3]
        th_min, th_max = Ts * (0.5 - A / (2 * AR)), Ts * (0.5 + A / (2 * AR))
        ok_formule &= abs(w.min() - th_min) < 0.08 * Ts and abs(w.max() - th_max) < 0.08 * Ts
        lignes.append([fmt(A, "V"), fmt(w.min(), "s"), fmt(w.max(), "s"),
                       f"théorie {fmt(th_min,'s')} à {fmt(th_max,'s')} ; message récupéré {fr(sd)} dB"])
    r.tableaux.append((f"Tableau de la vidéo rempli par la simulation (fs = {fmt(FS,'Hz')}, message {fmt(FM,'Hz')}, rampe ± {fmt(AR,'V')})",
                       ["Amplitude du message", "Largeur min", "Largeur max", "Observation"], lignes))
    r.check("Largeur τ = Ts·(1/2 + m(t)/(2·Ar))", "principe expliqué dans la vidéo",
            "largeurs mesurées sur les impulsions simulées", CONFIRME if ok_formule else ECART,
            "la largeur varie linéairement avec l'amplitude instantanée du message")
    t, msg, p, y, sd = pwm.essai(FM, FS, 2.0, AR)
    r.check("Surmodulation", "—", f"si A > {fmt(AR,'V')} les impulsions disparaissent ou fusionnent", INFO,
            "l'amplitude du message doit rester inférieure à celle de la rampe")
    r.check("Démodulation par filtre passe-bas", "message récupéré sur la sortie audio", f"SINAD {fr(sd)} dB (A = 2 V)", CONFIRME)
    r.hypotheses += [f"Rampe ± {fmt(AR,'V')} et horloge {fmt(FS,'Hz')} supposées (non lues dans la vidéo) : "
                     "les largeurs du tableau changent avec ces valeurs, pas la loi linéaire.",
                     "Filtre : Butterworth d'ordre 4, coupure 2,67 kHz (fs/3)."]

    fig, ax = nouvelle_figure(2, 2.6, "TP04 – PWM simulée (1 kHz, fs = 8 kHz)")
    k = (t > 10e-3) & (t < 12e-3)
    tt = (t[k] - 10e-3) * 1e3
    ax[0].plot(tt, pwm.rampe(t[k], FS, AR), c="0.6", lw=0.7, label="rampe")
    ax[0].plot(tt, msg[k], lw=1, label="message 2 V")
    ax[0].plot(tt, p[k] / 2, lw=0.8, label="PWM (÷2)"); ax[0].legend(fontsize=7, loc="upper right")
    ax[1].plot(tt, y[k], lw=1.3, label="après filtre"); ax[1].set_xlabel("t (ms)"); ax[1].legend(fontsize=7)
    sauve(fig, r, outdir, "tp04_pwm.png", "Génération PWM par comparaison et démodulation")
    return r
