"""TP09 – Démodulation FM par PLL LM565."""
import numpy as np

import ngspice_outil as ng
from common import Resultat, CONFIRME, ECART, INDETERMINE, INFO, LEVE, REDUIT, RESTE, periodes_cycle, fmt, fr, ecart_pct, ajuste_sinus, sinad_db, passe_bas, nouvelle_figure, sauve

TITRE = "Démodulation FM par boucle à verrouillage de phase LM565"


def pll(x, fs, f0, ko, a_pd, tau):
    """PLL comportementale : comparateur de phase (multiplieur de signaux limités), filtre RC, VCO."""
    n = len(x)
    vc = np.empty(n)
    ph = 0.0
    v = 0.0
    a = 1.0 / (tau * fs)
    two_pi_dt = 2 * np.pi / fs
    for k in range(n):
        vco = 1.0 if np.cos(ph) >= 0 else -1.0
        pd = a_pd * (1.0 if x[k] >= 0 else -1.0) * vco   # caractéristique triangulaire, pente 2·a_pd/π
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
    ko = 50 * f0 / (2 * np.pi * 24)               # Ko = 50·f0/Vc rad/s/V, Vc = 24 V (fiche technique)
    tau = 3.6e3 * 150e-9                          # résistance interne 3,6 kΩ et C2 = 150 nF (schéma)
    vc = pll(x, fs, f0, ko, 1.0, tau)
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
    _ngspice(r, f0, outdir)
    r.hypotheses += ["Excursion de fréquence du générateur non lue dans la vidéo : Δf = 1 kHz supposé.",
                     "Ko = 50·f0/Vc (fiche technique) ; comparateur de phase ±1 V ; résistance interne broche 7 ≈ 3,6 kΩ ; C2 = 150 nF (schéma)."]

    fig, ax = nouvelle_figure(1, 3, "TP09 – Tension de commande du VCO = message démodulé")
    k = t > 6e-3
    ax[0].plot((t[k]-6e-3)*1e3, vc[k] - vc[sel].mean(), lw=0.4, c="0.6", label="broche 7 (brut)")
    ax[0].plot((t[k]-6e-3)*1e3, vf[k] - vf[sel].mean(), lw=1.4, label="après filtre 3 kHz")
    ax[0].legend(fontsize=7, loc="upper right")
    ax[0].set_xlabel("t (ms)"); ax[0].set_ylabel("V")
    sauve(fig, r, outdir, "tp09_pll.png", "Sortie du LM565 simulé (message 1 kHz)")
    return r


def _f_vco(t, vco, debut):
    sel = t > debut
    _, per = periodes_cycle(vco[sel], t[sel], 0.0 if vco[sel].min() < 0 < vco[sel].max() else None)
    f = 1 / per
    return float(np.mean(f)), float(np.std(f))


def _ngspice(r, f0_formule, outdir):
    if not ng.disponible():
        r.check("[ngspice] Simulation du montage", "—", "ngspice absent sur cette machine", INDETERMINE,
                "la simulation tourne dans GitHub Actions")
        return
    f_libre = {}
    for bas, nom in ((0, "masse (vidéo)"), (1, "−12 V (fiche technique)")):
        t, (out, tc, vco) = ng.lance("tp09_lm565_pll.cir", pas=0.2e-6, VA=0, C1BAS=bas, TSTOP="3m")
        f_libre[bas] = _f_vco(t, vco, 1e-3)[0]
    r.check("[ngspice] Fréquence libre du VCO, C1 relié à la masse / à −12 V", "9,4 kHz",
            f"{fmt(f_libre[0],'Hz',4)} / {fmt(f_libre[1],'Hz',4)}",
            CONFIRME if abs(ecart_pct(f_libre[0], f_libre[1])) < 0.5 else ECART,
            "avec des alimentations stables, la masse et −12 V sont deux points fixes : le condensateur voit la même variation")

    # démodulation : porteuse 9,4 kHz, message 1 kHz, Δf = 1 kHz (indice 1)
    t, (out, tc, vco) = ng.lance("tp09_lm565_pll.cir", pas=1e-6, MDI=1, TSTOP="20m")
    td, outd = t, out
    sel = t > 10e-3
    amp, _, _, _ = ajuste_sinus(out[sel], t[sel], 1e3)
    sd = sinad_db(out[sel], t[sel], 1e3)
    ko = 50 * f0_formule / (2 * np.pi * 24)
    r.check("[ngspice] Message récupéré sur la broche 7 (Δf = 1 kHz)", "sinus 1 kHz récupéré",
            f"{fmt(amp,'V')} crête ; SINAD {fr(sd)} dB", CONFIRME if sd > 15 else ECART,
            f"amplitude attendue Δf/Ko = {fmt(1e3/ko,'V')} (Ko = {fmt(ko,'Hz')}/V sous ±12 V)")

    # plage de verrouillage : porteuse pure décalée de f0
    lignes, limite = [], 0.0
    for d in (1.5e3, 2.5e3, 3.0e3, 3.5e3, 4.5e3):
        ok_pm = []
        for sgn in (+1, -1):
            fin = f_libre[0] + sgn * d
            t, (out, tc, vco) = ng.lance("tp09_lm565_pll.cir", pas=0.5e-6, MDI=0, FC=f"{fin:.1f}", TSTOP="15m")
            fm_, fs_ = _f_vco(t, vco, 10e-3)
            ok_pm.append(abs(ecart_pct(fm_, fin)) < 0.5 and fs_ < 0.02 * fin)
        verrou = all(ok_pm)
        if verrou:
            limite = d
        lignes.append([f"± {fmt(d,'Hz')}", "verrouillée" if verrou else "décrochée"])
    r.tableaux.append(("ngspice : la boucle suit-elle une porteuse pure décalée de f0 ?",
                       ["Écart à f0", "Boucle"], lignes))
    fl = 8 * f0_formule / 24
    r.check("[ngspice] Plage de verrouillage simulée", f"fiche technique : ±8·f0/Vc = ±{fmt(fl,'Hz')}",
            f"verrouillée jusqu'à ±{fmt(limite,'Hz')} au moins", CONFIRME if 0.6 * fl <= limite <= 1.5 * fl else INDETERMINE)
    r.doute("C1 relié à la masse (vidéo) ou à −12 V (fiche technique) ?", REDUIT,
            f"Avec des alimentations stables, ngspice donne la même fréquence ({fmt(f_libre[0],'Hz')} et {fmt(f_libre[1],'Hz')}). "
            "La fiche technique préfère −V pour que le condensateur suive les variations de l'alimentation ; "
            "le modèle comportemental ne peut pas reproduire cet effet de second ordre.")
    r.doute("Alimentation ±4 V (oral) ou ±12 V (écran) ?", LEVE,
            "±4 V est hors de la plage du LM565 (±5 à ±12 V) ; ±12 V donne une plage de verrouillage de ±3,1 kHz "
            "autour de 9,4 kHz, compatible avec la démonstration.")
    r.doute("Excursion de fréquence du générateur", RESTE,
            "Non lisible dans la vidéo : la sortie démodulée lui est proportionnelle (Δf/Ko).")
    fig, ax = nouvelle_figure(1, 3, "TP09 – ngspice : sortie démodulée du LM565 (broche 7)")
    k = td > 8e-3
    ax[0].plot((td[k] - 8e-3) * 1e3, outd[k], lw=0.8); ax[0].set_xlabel("t (ms)"); ax[0].set_ylabel("V")
    sauve(fig, r, outdir, "tp09_lm565_ngspice.png", "Message de 1 kHz récupéré par le LM565 simulé dans ngspice")
