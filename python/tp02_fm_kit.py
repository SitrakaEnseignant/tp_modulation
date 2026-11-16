"""TP02 – Modulation de fréquence, maquette « FM Modulation and Demodulation » (Dr. K.D. Gaikwad)."""
import numpy as np
from scipy import signal

from common import (Resultat, CONFIRME, ECART, INDETERMINE, INFO, fmt, fr,
                    periodes_cycle, sinad_db, passe_bas, spectre, nouvelle_figure, sauve)

TITRE = "FM – maquette FM Modulation & Demodulation (VCO + PLL)"


def run(outdir):
    r = Resultat(2, TITRE, "Modèle comportemental (Python) : VCO idéal, lecture aux curseurs simulée, "
                           "démodulation par discriminateur de phase.")
    tdiv = 10e-6
    fc = 1 / (2.2 * tdiv)
    fm = 1 / (4 * 50e-6)
    fmax_v = 1 / (1.8 * tdiv)
    fmin_v = 1 / (3.8 * tdiv)

    r.check("Porteuse (2,2 div × 10 µs)", "45,45 kHz", fmt(fc, "Hz", 4), CONFIRME)
    r.check("Message (4 div × 50 µs)", "5 kHz", fmt(fm, "Hz", 4), CONFIRME)
    r.check("fmax (1,8 div × 10 µs)", "≈ 55 kHz", fmt(fmax_v, "Hz", 4), CONFIRME)
    r.check("fmin (3,8 div × 10 µs)", "55 kHz écrit sur la feuille", fmt(fmin_v, "Hz", 4), ECART,
            "1/38 µs = 26,3 kHz : la valeur 55 kHz écrite pour fmin est une erreur de recopie (fmin doit être < fc).")

    dp, dm = fmax_v - fc, fc - fmin_v
    r.check("Symétrie de l'excursion", "non discutée",
            f"Δf+ = {fmt(dp,'Hz')} ; Δf− = {fmt(dm,'Hz')} ; milieu = {fmt((fmax_v+fmin_v)/2,'Hz')}", ECART,
            "Un VCO linéaire donne Δf+ = Δf−. Ici Δf− ≈ 2·Δf+ : la lecture de 3,8 div est douteuse "
            "(ou le VCO est très non linéaire).")

    # ---- simulation : FM symétrique avec Δf = Δf+ mesuré, lecture cycle par cycle
    fs = 20e6
    t = np.arange(0, 2e-3, 1 / fs)
    df = dp
    phase = 2 * np.pi * fc * t + (df / fm) * np.sin(2 * np.pi * fm * t)
    s = np.cos(phase)
    tc, per = periodes_cycle(s, t, 0.0)
    f_cyc = 1 / per
    fmax_s, fmin_s = f_cyc.max(), f_cyc.min()
    r.check("Lecture fmin attendue avec un VCO symétrique", "3,8 div (38 µs)",
            f"{fr(1/fmin_s/tdiv,2)} div ({fmt(1/fmin_s,'s')}) → fmin ≈ {fmt(fmin_s,'Hz')}", ECART,
            "Avec Δf = 10,1 kHz des deux côtés, la période la plus longue mesurée sur un cycle vaut ≈ 28 µs, pas 38 µs.")
    r.check("Lecture fmax simulée (un cycle)", "1,8 div", f"{fr(1/fmax_s/tdiv,2)} div → {fmt(fmax_s,'Hz')}", CONFIRME,
            "un cycle de porteuse dure environ 1/9 de la période du message : la lecture moyenne un peu l’excursion")

    beta = dp / fm
    carson = 2 * (dp + fm)
    r.check("Indice de modulation β = Δf/fm", "non calculé", f"β = {fr(beta)} (avec Δf+)", INFO)
    r.check("Bande de Carson B = 2(Δf + fm)", "non calculée", fmt(carson, "Hz"), INFO)

    # bande contenant 98 % de la puissance (contrôle de Carson)
    f, X = spectre(s, fs)
    P = X**2
    k0 = np.argmin(abs(f - fc))
    tot = P.sum()
    for w in range(1, len(f)):
        if P[max(k0-w,0):k0+w+1].sum() >= 0.98 * tot:
            break
    b98 = f[k0+w] - f[max(k0-w,0)]
    r.check("Bande à 98 % de puissance (simulée)", "—", fmt(b98, "Hz"), CONFIRME if abs(b98-carson)/carson < 0.25 else INDETERMINE,
            "comparaison avec la règle de Carson")

    # ---- démodulation (fréquence instantanée par la phase analytique)
    z = signal.hilbert(s)
    finst = np.diff(np.unwrap(np.angle(z))) * fs / (2 * np.pi)
    dem = passe_bas(finst, fs, 15e3, 4)
    sel = slice(int(0.5e-3 * fs), -int(0.1e-3 * fs))
    sd = sinad_db(dem[sel], t[1:][sel], fm)
    r.check("Démodulation : message récupéré à 5 kHz", "message récupéré montré (TP4)", f"SINAD {fr(sd)} dB", CONFIRME)
    r.hypotheses += [
        "VCO idéal et linéaire ; le circuit interne de la maquette n'est pas connu.",
        "Le démodulateur PLL de la maquette est remplacé par un discriminateur de phase idéal (même résultat pour un PLL verrouillé).",
    ]

    fig, ax = nouvelle_figure(3, 2.6, "TP02 – FM simulée (fc = 45,45 kHz, fm = 5 kHz, Δf = 10,1 kHz)")
    k = t < 0.4e-3
    ax[0].plot(t[k]*1e6, s[k], lw=0.7); ax[0].set_xlabel("t (µs)"); ax[0].set_title("Signal FM", fontsize=9)
    ax[1].plot(tc*1e6, f_cyc/1e3, ".", ms=3, label="lecture cycle par cycle")
    ax[1].axhline(fmax_v/1e3, c="r", ls="--", lw=0.8, label="fmax vidéo 55,6 kHz")
    ax[1].axhline(fmin_v/1e3, c="g", ls="--", lw=0.8, label="fmin vidéo 26,3 kHz")
    ax[1].set_xlim(0, 400); ax[1].set_xlabel("t (µs)"); ax[1].set_ylabel("kHz"); ax[1].legend(fontsize=7)
    ax[1].set_title("Fréquence lue sur chaque cycle : fmin vidéo hors de portée d'un VCO symétrique", fontsize=9)
    kf = (f > 0) & (f < 120e3)
    ax[2].plot(f[kf]/1e3, X[kf], lw=0.8); ax[2].axvspan((fc-carson/2)/1e3, (fc+carson/2)/1e3, alpha=0.15, label="bande de Carson")
    ax[2].set_xlabel("f (kHz)"); ax[2].legend(fontsize=7); ax[2].set_title("Spectre FM (raies espacées de fm)", fontsize=9)
    sauve(fig, r, outdir, "tp02_fm.png", "FM simulée : lecture des fréquences et spectre")
    return r
