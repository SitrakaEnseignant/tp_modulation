"""TP09 – Démodulation FM par PLL LM565."""
import numpy as np

from common import Resultat, CONFIRME, ECART, INDETERMINE, INFO, fmt, fr, ecart_pct, ajuste_sinus, sinad_db, passe_bas, nouvelle_figure, sauve

TITRE = "Démodulation FM par boucle à verrouillage de phase LM565"


def pll(x, fs, f0, ko, kd, tau):
    """PLL comportementale : comparateur de phase (multiplieur de signaux limités), filtre RC, VCO."""
    n = len(x)
    vc = np.empty(n)
    ph = 0.0
    v = 0.0
    a = 1.0 / (tau * fs)
    two_pi_dt = 2 * np.pi / fs
    for k in range(n):
        vco = 1.0 if np.cos(ph) >= 0 else -1.0
        pd = kd * (np.pi / 2) * (1.0 if x[k] >= 0 else -1.0) * vco   # caractéristique triangulaire, pente kd
        v += a * (pd - v)
        ph += two_pi_dt * (f0 + ko * v)
        vc[k] = v
    return vc


def run(outdir):
    r = Resultat(9, TITRE, "Formules de la fiche technique + PLL comportementale (Python).")
    R1, C1 = 6.8e3, 4.7e-9
    f0 = 1.2 / (4 * R1 * C1)
    r.check("Fréquence libre du VCO f0 = 1,2/(4·R1·C1)", "porteuse réglée à 9,4 kHz", fmt(f0, "Hz", 4),
            CONFIRME if abs(ecart_pct(f0, 9.4e3)) < 2 else ECART, f"écart {fr(ecart_pct(f0, 9.4e3),2)} %")
    r.check("Exemple de la fiche technique (R = 20 kΩ, C = 1,5 nF)", "—", fmt(1.2 / (4 * 20e3 * 1.5e-9), "Hz"), CONFIRME,
            "la fiche technique annonce 10 kHz : la formule est vérifiée")
    for vs, statut, com in [(12, CONFIRME, "valeur du schéma et de l'écran"),
                            (4, ECART, "±4 V est hors de la plage d'alimentation (±5 à ±12 V) : c'est une erreur de transcription")]:
        fl = 8 * f0 / (2 * vs)
        r.check(f"Plage de verrouillage à ±{vs} V : fL = ±8·f0/Vtot", "±12 V (écran) / « ±4 V » (oral)",
                f"±{fmt(fl,'Hz')} → de {fmt(f0-fl,'Hz')} à {fmt(f0+fl,'Hz')}", statut, com)

    # ---- simulation de la démodulation
    fs = 2e6
    fm, df = 1e3, 1e3
    t = np.arange(0, 20e-3, 1 / fs)
    x = np.cos(2 * np.pi * f0 * t + (df / fm) * np.sin(2 * np.pi * fm * t))
    ko = 2 * np.pi * 0.66 * f0 / (2 * np.pi)       # 6600 Hz/V à 10 kHz → 0,66·f0 par volt
    kd = 0.68
    tau = 3.6e3 * 10e-9
    vc = pll(x, fs, f0, ko, kd, tau)
    sel = t > 8e-3
    amp, _, _, _ = ajuste_sinus(vc[sel], t[sel], fm)
    sd_brut = sinad_db(vc[sel], t[sel], fm)
    vf = passe_bas(vc, fs, 3e3, 2)
    sd = sinad_db(vf[sel], t[sel], fm)
    r.check("Message récupéré à la sortie (broche 7)", "sinus 1 kHz récupéré à l'oscilloscope",
            f"{fmt(amp,'V')} crête ; SINAD {fr(sd_brut)} dB brut, {fr(sd)} dB après un filtre passe-bas de 3 kHz",
            CONFIRME if sd > 20 else ECART,
            f"amplitude attendue Δf/Ko = {fmt(df/ko,'V')}. La sortie brute porte une forte ondulation à 2·f0 ≈ 18,8 kHz "
            "qu'un petit filtre passe-bas après la broche 7 enlève.")
    r.check("Branchement de C1", "C1 relié à la masse dans la vidéo", "fiche technique : C1 entre broche 9 et −V (broche 1)",
            INDETERMINE, "le circuit fonctionne aussi avec C1 à la masse, mais f0 peut s'écarter un peu de la formule")
    r.hypotheses += ["Excursion de fréquence du générateur non lue dans la vidéo : Δf = 1 kHz supposé.",
                     "Kd = 0,68 V/rad et Ko = 6600 Hz/V à 10 kHz (fiche technique) ; résistance interne broche 7 ≈ 3,6 kΩ.",
                     "Condensateur de filtre de boucle C2 = 10 nF supposé."]

    fig, ax = nouvelle_figure(1, 3, "TP09 – Tension de commande du VCO = message démodulé")
    k = t > 6e-3
    ax[0].plot((t[k]-6e-3)*1e3, vc[k] - vc[sel].mean(), lw=0.4, c="0.6", label="broche 7 (brut)")
    ax[0].plot((t[k]-6e-3)*1e3, vf[k] - vf[sel].mean(), lw=1.4, label="après filtre 3 kHz")
    ax[0].legend(fontsize=7, loc="upper right")
    ax[0].set_xlabel("t (ms)"); ax[0].set_ylabel("V")
    sauve(fig, r, outdir, "tp09_pll.png", "Sortie du LM565 simulé (message 1 kHz)")
    return r
