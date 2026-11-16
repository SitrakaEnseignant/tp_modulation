"""TP08 – PAM, maquette Excel Technologies (source AF 1 kHz, horloge 8 kHz)."""
import numpy as np

from common import Resultat, CONFIRME, ECART, INDETERMINE, INFO, fmt, fr, nouvelle_figure, sauve
import pam

TITRE = "PAM – maquette Excel Technologies (1 kHz / 8 kHz)"


def run(outdir):
    r = Resultat(8, TITRE, "Modèle comportemental (Python) : interrupteur analogique commandé par une horloge 0/1.")
    fm, fs = 1e3, 8e3
    r.check("Nyquist", "message 1 kHz, horloge 8 kHz", f"fs/fm = {fr(fs/fm)} ≥ 2", CONFIRME)
    r.check("Impulsions par période du message", "—", f"{fr(fs/fm)} impulsions", INFO,
            "8 échantillons par période : l'enveloppe des impulsions dessine bien le sinus")

    t = np.arange(0, 14e-3, 1 / pam.FS_SIM)
    msg = np.sin(2 * np.pi * fm * t)
    clk = pam.horloge(t, fs, 0.5)
    # cas 1 : interrupteur analogique idéal (message bipolaire)
    p_ideal = msg * clk
    # cas 2 : message bipolaire mais étage alimenté en unipolaire (écrêtage à 0 V)
    p_uni = np.clip(msg, 0, None) * clk
    # cas 3 : message décalé d'une composante continue (cas fréquent des maquettes)
    p_off = (0.5 + 0.5 * msg) * clk
    neg_ideal = p_ideal.min() < -0.1
    r.check("« Seule l'alternance positive apparaît » (dit à l'oral)",
            "horloge unipolaire 0/1 → seulement l'alternance positive",
            "interrupteur idéal : impulsions positives ET négatives" if neg_ideal else "impulsions positives seulement",
            INDETERMINE,
            "Une horloge 0/1 commande l'interrupteur mais ne fixe pas le signe des impulsions : un interrupteur analogique "
            "laisse passer les deux alternances. L'observation de la vidéo s'explique si l'étage de la maquette est "
            "alimenté en unipolaire (écrêtage) ou si le message porte un décalage continu. À vérifier sur la maquette.")
    *_, sd = pam.essai(fm, fs, "naturel", 0.5, 3.4e3, 4)
    r.check("Message récupéré après filtre (cas idéal)", "démodulation non montrée", f"SINAD {pam.txt_sinad(sd)}", INFO)
    r.hypotheses += ["Rapport cyclique 50 % ; filtre Butterworth d'ordre 4 à 3,4 kHz pour la démodulation."]

    fig, ax = nouvelle_figure(3, 2.3, "TP08 – PAM 1 kHz / 8 kHz : rôle de l'horloge unipolaire")
    k = (t > 10e-3) & (t < 12e-3)
    tt = (t[k] - 10e-3) * 1e3
    for a, p, nom in zip(ax, (p_ideal, p_uni, p_off),
                         ("interrupteur idéal : deux alternances", "étage unipolaire : alternance positive seule",
                          "message décalé (0,5 + 0,5·sin) : tout positif")):
        a.plot(tt, msg[k], c="0.6", lw=0.8); a.plot(tt, p[k], lw=0.9); a.set_title(nom, fontsize=9); a.set_xlabel("t (ms)")
    sauve(fig, r, outdir, "tp08_pam.png", "Trois hypothèses pour expliquer l'alternance positive seule")
    return r
