"""TP12 – PAM et démodulation, maquette Scientech ST2110 (impulsions 8 et 16 kHz)."""
import numpy as np

from common import Resultat, CONFIRME, ECART, INDETERMINE, INFO, fmt, fr, nouvelle_figure, sauve
import pam

TITRE = "PAM et démodulation – Scientech ST2110 (8 / 16 / 32 / 64 kHz)"


def run(outdir):
    r = Resultat(12, TITRE, "Modèle comportemental (Python) : sorties Sample, Sample & Hold, Flat-Top + filtre.")
    lignes = []
    for fs in (8e3, 16e3, 32e3, 64e3):
        row = [fmt(fs, "Hz")]
        for mode in ("naturel", "sh", "flat-top"):
            *_, sd = pam.essai(1e3, fs, mode, 0.5, 3.4e3, 4)
            row.append(f"{pam.txt_sinad(sd)} ({pam.qualite(sd)})")
        lignes.append(row)
    r.tableaux.append(("Tableau de la vidéo rempli par la simulation (message 1 kHz)",
                       ["Fréquence d'impulsion", "Sample", "Sample & Hold", "Flat-Top"], lignes))
    *_, s8 = pam.essai(1e3, 8e3, "naturel", 0.5, 3.4e3, 4)
    *_, s16 = pam.essai(1e3, 16e3, "naturel", 0.5, 3.4e3, 4)
    r.check("Démodulation à 8 kHz et 16 kHz (affichées)", "message récupéré dans les deux cas",
            f"8 kHz : {pam.txt_sinad(s8)} ; 16 kHz : {pam.txt_sinad(s16)}", CONFIRME,
            "à 8 kHz, une petite ondulation résiduelle reste visible ; à 16 kHz le sinus est propre")
    r.check("Câblage : message broche 2, impulsions broche 1", "dit à l'oral", "PAM = m(t) × p(t)", CONFIRME,
            "le modulateur multiplie le message par le train d'impulsions ; l'ordre des broches est propre à la maquette")
    # retard du filtre (effet « RC delay » cité dans la vidéo)
    t, msg, p, y, _ = pam.essai(1e3, 16e3, "naturel", 0.5, 3.4e3, 4)
    sel = t > 10e-3
    xc = np.correlate(y[sel], msg[sel], "full")
    n = len(msg[sel])
    lags = np.arange(-n + 1, n)
    ok = (lags >= 0) & (lags < pam.FS_SIM / 1e3)
    lag = lags[ok][np.argmax(xc[ok])]
    retard = lag / pam.FS_SIM
    r.check("Retard du message récupéré (« RC delay »)", "retard visible, non chiffré",
            f"{fmt(retard,'s')} soit {fr(360*retard*1e3)}° à 1 kHz", INFO, "retard de groupe du filtre de démodulation")
    r.hypotheses += ["Rapport cyclique 50 %, filtre Butterworth d'ordre 4 à 3,4 kHz (non documenté pour le ST2110)."]

    fig, ax = nouvelle_figure(2, 2.6, "TP12 – Message récupéré à 8 kHz et 16 kHz")
    for a, fs in zip(ax, (8e3, 16e3)):
        t, msg, p, y, sd = pam.essai(1e3, fs, "naturel", 0.5, 3.4e3, 4)
        k = (t > 10e-3) & (t < 13e-3)
        a.plot((t[k]-10e-3)*1e3, p[k], lw=0.5, c="0.7", label="PAM")
        a.plot((t[k]-10e-3)*1e3, msg[k]*0.5, lw=0.8, ls="--", label="message × 0,5")
        a.plot((t[k]-10e-3)*1e3, y[k], lw=1.3, label=f"sortie filtre ({pam.txt_sinad(sd)})")
        a.set_title(f"fs = {fmt(fs,'Hz')}", fontsize=9); a.legend(fontsize=7, loc="upper right"); a.set_xlabel("t (ms)")
    sauve(fig, r, outdir, "tp12_pam.png", "Démodulation PAM : retard du filtre et ondulation résiduelle")
    return r
