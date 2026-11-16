"""TP11 – Modulation d'amplitude à transistor BC107 (simulation SPICE avec ngspice)."""
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from common import (Resultat, CONFIRME, ECART, INDETERMINE, INFO, fmt, fr, ecart_pct, RACINE,
                    ngspice_disponible, cretes_par_cycle, ajuste_sinus, nouvelle_figure, sauve)

TITRE = "AM à transistor BC107BP + détecteur d'enveloppe (SPICE)"
FC, FM = 10e3, 500.0


def lance_spice(vcc, amsg, rl=50.0):
    gabarit = (RACINE / "spice" / "tp11_am_bc107.cir").read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "modeles.lib").write_text((RACINE / "spice" / "modeles.lib").read_text(encoding="utf-8"), encoding="utf-8")
        out = d / "out.txt"
        net = (gabarit.replace("{VCC}", str(vcc)).replace("{AMSG}", str(amsg))
                      .replace("{RL}", str(rl)).replace("{OUT}", str(out)))
        (d / "tp11.cir").write_text(net, encoding="utf-8")
        p = subprocess.run(["ngspice", "-b", "tp11.cir"], cwd=d, capture_output=True, text=True, timeout=600)
        if not out.exists():
            raise RuntimeError("ngspice n'a pas produit de résultat :\n" + p.stdout[-2000:] + p.stderr[-2000:])
        data = np.loadtxt(out)
    return data[:, 0], data[:, 1], data[:, 3]


def mesure(t, vc, vout):
    """Emax / Emin de l'enveloppe du collecteur sur les 10 dernières ms (comme aux curseurs)."""
    sel = t > 20e-3
    # rééchantillonnage régulier (ngspice utilise un pas variable)
    tt = np.arange(t[sel][0], t[sel][-1], 0.5e-6)
    v = np.interp(tt, t, vc)
    tp, pk = cretes_par_cycle(v, tt, FC)
    emax, emin = float(pk.max()), float(pk.min())
    vo = np.interp(tt, t, vout)
    amp_dem, *_ = ajuste_sinus(vo, tt, FM)
    return emax, emin, tt, v, vo, tp, pk, amp_dem


def run(outdir):
    r = Resultat(11, TITRE, "Simulation SPICE (ngspice) du schéma de la vidéo avec des modèles génériques BC107B et 1N4001.")
    L1, C1 = 50e-3, 10e-9
    f_tank = 1 / (2 * np.pi * np.sqrt(L1 * C1))
    r.check("Accord du circuit L1 // C1", "porteuse 10 kHz", f"f0 = 1/(2π√(LC)) = {fmt(f_tank,'Hz')}", ECART,
            f"le circuit accordé est réglé {fr(ecart_pct(f_tank, FC),2)} % sous la porteuse : le gain à 10 kHz est réduit. "
            "Il faudrait C1 ≈ 5,1 nF (ou L1 ≈ 25 mH) pour accorder sur 10 kHz.")
    mu_v = (11.8 - 11.0) / (11.8 + 11.0)
    r.check("Calcul de μ avec Emax = 11,8 V et Emin = 11 V", "μ = 0,029 annoncé", f"μ = {fr(mu_v)}", ECART,
            "0,029 venait d'une mesure précédente (Vmax = 12,3 V) ; avec les valeurs affichées μ ≈ 0,035")
    tau = 500 * 1e-6
    r.check("Détecteur : 1/fc ≪ R5·C2 ≪ 1/fm", "1/fc = 100 µs, 1/fm = 2 ms", f"R5·C2 = {fmt(tau,'s')}", CONFIRME,
            "condition respectée (5 périodes de porteuse, 1/4 de période du message)")

    if not ngspice_disponible():
        r.check("Simulation SPICE", "—", "ngspice absent sur cette machine", INDETERMINE,
                "la simulation SPICE tourne dans GitHub Actions (ngspice installé par le workflow)")
        return r

    res = {}
    for vcc in (8.3, 12.0):
        t, vc, vo = lance_spice(vcc, 4.5)
        res[vcc] = (t, vc, vo, *mesure(t, vc, vo))
    t, vc, vo, emax, emin, tt, v, vout, tp, pk, amp_dem = res[8.3]
    mu_s = (emax - emin) / (emax + emin)
    r.check("Emax / Emin au collecteur (Vcc = 8,3 V)", "≈ 11,8 V / ≈ 11 V", f"{fmt(emax,'V')} / {fmt(emin,'V')}",
            CONFIRME if abs(emax - 11.8) < 1.0 and abs(emin - 11.0) < 1.0 else INDETERMINE,
            "crêtes de chaque cycle de porteuse sur 10 ms")
    r.check("Taux de modulation μ (même formule que la vidéo)", "≈ 0,03", f"μ = {fr(mu_s)}",
            CONFIRME if mu_s < 0.1 else INDETERMINE,
            "un μ très faible confirme que ce montage module peu ; la vidéo l'attribue au transistor de remplacement, "
            "la simulation montre que le schéma lui-même donne déjà un μ faible avec un BC107" if mu_s < 0.1 else
            "avec un BC107 générique la modulation simulée est plus forte que dans la vidéo : le transistor de remplacement "
            "peut expliquer la différence")
    ac = (pk.max() - pk.min()) / 2
    r.check("Message récupéré après le détecteur", "sinus de 500 Hz observé", f"{fmt(amp_dem,'V')} crête à 500 Hz", INFO)
    e12 = res[12.0]
    r.check("Même montage sous 12 V (valeur du schéma)", "—",
            f"Emax = {fmt(e12[3],'V')} ; Emin = {fmt(e12[4],'V')} ; μ = {fr((e12[3]-e12[4])/(e12[3]+e12[4]))}", INFO)
    r.hypotheses += ["Modèles génériques BC107B et 1N4001 : le transistor réellement utilisé dans la vidéo n'est pas connu.",
                     "Résistance série de L1 : 50 Ω (non indiquée).",
                     "μ calculé comme dans la vidéo, avec les tensions absolues des crêtes : (Emax − Emin)/(Emax + Emin)."]

    fig, ax = nouvelle_figure(2, 2.6, "TP11 – Simulation SPICE du modulateur AM (Vcc = 8,3 V)")
    ax[0].plot((tt - tt[0]) * 1e3, v, lw=0.4); ax[0].plot((tp - tt[0]) * 1e3, pk, ".", ms=2)
    ax[0].set_title(f"Collecteur : Emax = {fmt(emax,'V')}, Emin = {fmt(emin,'V')}, μ = {fr(mu_s)}", fontsize=9)
    ax[0].set_xlabel("t (ms)")
    ax[1].plot((tt - tt[0]) * 1e3, vout, lw=1); ax[1].set_title("Sortie du détecteur (R5 // C2)", fontsize=9)
    ax[1].set_xlabel("t (ms)")
    sauve(fig, r, outdir, "tp11_am_spice.png", "Modulateur AM à BC107 simulé avec ngspice")
    return r
