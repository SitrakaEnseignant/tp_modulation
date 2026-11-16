"""TP03 – PAM naturel, flat-top et impulsionnel (maquette Scientech ST2110, DSO)."""
import numpy as np

from common import Resultat, CONFIRME, ECART, INDETERMINE, INFO, fmt, fr, nouvelle_figure, sauve
import pam

TITRE = "PAM naturel, sample & hold et flat-top – Scientech ST2110"
FS_KIT = [8e3, 16e3, 32e3, 64e3]
FM_KIT = [1e3, 2e3]
FC_FILTRE, ORDRE = 3.4e3, 4


def run(outdir):
    r = Resultat(3, TITRE, "Modèle comportemental (Python) : échantillonnage idéal + filtre de Butterworth.")
    lignes = []
    res = {}
    for fm in FM_KIT:
        for fs in FS_KIT:
            row = [fmt(fm, "Hz"), fmt(fs, "Hz")]
            for mode in ("naturel", "sh", "flat-top"):
                *_, sd = pam.essai(fm, fs, mode, 0.5, FC_FILTRE, ORDRE)
                res[(fm, fs, mode)] = sd
                row.append(f"{pam.txt_sinad(sd)} ({pam.qualite(sd)})")
            lignes.append(row)
    r.tableaux.append(("SINAD du message récupéré après le filtre (simulation)",
                       ["message", "fs", "naturel", "sample & hold", "flat-top (τ = Ts/2)"], lignes))

    for fs in FS_KIT:
        ok = fs >= 2 * max(FM_KIT)
        r.check(f"Critère de Nyquist à fs = {fmt(fs,'Hz')}", "fs ≥ 2·fm (message 1 ou 2 kHz)",
                f"fs/fmax = {fr(fs/max(FM_KIT))}", CONFIRME if ok else ECART)

    # effet d'ouverture
    for fs in (8e3, 16e3):
        a_sh = pam.attenuation_ouverture(2e3, 1 / fs)
        a_ft = pam.attenuation_ouverture(2e3, 0.5 / fs)
        r.check(f"Effet d'ouverture à 2 kHz, fs = {fmt(fs,'Hz')}", "non mesuré",
                f"S&H : {fr(20*np.log10(a_sh),2)} dB ; flat-top τ = Ts/2 : {fr(20*np.log10(a_ft),2)} dB", INFO,
                "le maintien atténue un peu les fréquences hautes du message (sinc)")

    # tableau à compléter de la vidéo
    pred = []
    for fs, mode, nom in [(16e3, "naturel", "naturel"), (16e3, "sh", "sample & hold"),
                          (32e3, "flat-top", "flat-top"), (64e3, "flat-top", "flat-top")]:
        sd = res[(1e3, fs, mode)]
        pred.append([fmt(fs, "Hz"), nom, f"sommets {'suivant le message' if mode=='naturel' else 'plats'} ; "
                     f"message récupéré {pam.qualite(sd)} ({pam.txt_sinad(sd)})"])
    r.tableaux.append(("Tableau de la vidéo rempli par la simulation (message 1 kHz)",
                       ["fs", "Type", "Observation prédite"], pred))
    r.check("Meilleure restitution quand fs augmente", "annoncé dans la vidéo",
            f"naturel 1 kHz : {fr(res[(1e3,8e3,'naturel')])} dB à 8 kHz → {fr(res[(1e3,64e3,'naturel')])} dB à 64 kHz",
            CONFIRME if res[(1e3, 64e3, 'naturel')] > res[(1e3, 8e3, 'naturel')] else ECART)
    r.hypotheses += [
        "Rapport cyclique des impulsions : 50 % (non indiqué dans la vidéo).",
        "Filtre de démodulation : Butterworth d'ordre 4, coupure 3,4 kHz (le filtre réel du ST2110 n'est pas documenté).",
        "SINAD : « correct » ≥ 30 dB, « limite » 20 à 30 dB, « dégradé » < 20 dB (seuils choisis pour la simulation).",
    ]

    fig, ax = nouvelle_figure(3, 2.4, "TP03 – PAM simulé, message 1 kHz, fs = 8 kHz")
    for a, mode, nom in zip(ax, ("naturel", "sh", "flat-top"), ("naturel", "sample & hold", "flat-top (τ = Ts/2)")):
        t, msg, p, y, sd = pam.essai(1e3, 8e3, mode, 0.5, FC_FILTRE, ORDRE)
        k = (t > 10e-3) & (t < 12e-3)
        a.plot((t[k]-10e-3)*1e3, msg[k], c="0.6", lw=0.8, label="message")
        a.plot((t[k]-10e-3)*1e3, p[k], lw=0.9, label=f"PAM {nom}")
        a.plot((t[k]-10e-3)*1e3, y[k], lw=1.3, label=f"après filtre ({fr(sd)} dB)")
        a.legend(fontsize=7, loc="upper right"); a.set_xlabel("t (ms)")
    sauve(fig, r, outdir, "tp03_pam.png", "Les trois formes de PAM et le message récupéré")
    return r
