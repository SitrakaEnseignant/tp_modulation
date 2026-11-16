"""TP06 – PWM, maquette Akademika DCL-08 (largeur en fonction d'une tension continue)."""
import numpy as np
from scipy import signal, optimize

from common import Resultat, CONFIRME, ECART, INDETERMINE, INFO, fmt, fr, nouvelle_figure, sauve

TITRE = "PWM – Akademika DCL-08 (caractéristique largeur / tension, déphasage)"
V = np.array([0.6, 1.4, 2.4, 3.3, 4.2])
W = np.array([0.18, 0.20, 0.21, 0.24, 0.26])   # unité notée « secs » (probablement ms)


def run(outdir):
    r = Resultat(6, TITRE, "Analyse des relevés (régression linéaire) + modèle de filtre de démodulation.")
    a, b = np.polyfit(V, W, 1)
    fit = a * V + b
    r2 = 1 - np.sum((W - fit) ** 2) / np.sum((W - W.mean()) ** 2)
    res_max = np.max(abs(W - fit))
    r.check("Largeur proportionnelle à la tension (droite croissante)", "courbe demandée : droite croissante",
            f"w = {fr(a,3)}·V + {fr(b,3)} ; R² = {fr(r2,3)}", CONFIRME if r2 > 0.95 else INDETERMINE,
            f"écart maximal à la droite : {fr(res_max,2)} (unité de la feuille). La relation est bien linéaire.")
    r.tableaux.append(("Relevés de la vidéo et droite ajustée",
                       ["V (V)", "largeur notée", "droite", "écart"],
                       [[fr(v), fr(w), fr(f, 3), fr(w - f, 2)] for v, w, f in zip(V, W, fit)]))
    r.check("Unité « secs »", "0,18 à 0,26 « secs »", "0,18 à 0,26 ms", INDETERMINE,
            "des largeurs de 0,2 s seraient impossibles avec une horloge de l'ordre du kHz : l'unité est très probablement la ms")

    # déphasage 150 µs : quel filtre de démodulation le produit ?
    dt = 0.6 * 250e-6
    lignes = []
    for fm in (500.0, 1000.0):
        phi = 360 * fm * dt
        row = [fmt(fm, "Hz"), f"{fr(phi)}°"]
        for o in (1, 2, 4):
            def err(fc):
                b_, a_ = signal.butter(o, 2 * np.pi * fc, analog=True)
                w = 2 * np.pi * np.linspace(1, fm, 400)
                _, h = signal.freqs(b_, a_, worN=w)
                return -np.degrees(np.unwrap(np.angle(h)))[-1] - phi
            try:
                fc = optimize.brentq(err, fm * 0.05, 200e3)
                row.append(fmt(fc, "Hz"))
            except ValueError:
                row.append("—")
        lignes.append(row)
    r.tableaux.append(("Déphasage mesuré 0,6 div × 250 µs = 150 µs : coupure du filtre qui le produit",
                       ["message", "déphasage", "filtre ordre 1", "Butterworth ordre 2", "Butterworth ordre 4"], lignes))
    r.check("Déphasage du signal démodulé", "0,6 × 250 µs = 150 µs", f"{fmt(dt,'s')} = {fr(360*1000*dt)}° à 1 kHz",
            CONFIRME, "valeur cohérente avec un filtre de démodulation de quelques kHz (voir tableau)")
    r.hypotheses += ["La fréquence du message pendant la mesure de déphasage (500 Hz ou 1 kHz) n'est pas certaine : les deux cas sont donnés."]

    fig, ax = nouvelle_figure(1, 3.2, "TP06 – Largeur d'impulsion en fonction de la tension continue")
    ax[0].plot(V, W, "o", label="relevés de la vidéo")
    vv = np.linspace(0, 5, 50)
    ax[0].plot(vv, a * vv + b, label=f"droite (R² = {fr(r2,3)})")
    ax[0].set_xlabel("tension d'entrée (V)"); ax[0].set_ylabel("largeur (ms ?)"); ax[0].legend(fontsize=8)
    sauve(fig, r, outdir, "tp06_pwm.png", "Caractéristique largeur / tension relevée dans la vidéo")
    return r
