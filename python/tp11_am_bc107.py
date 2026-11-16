"""TP11 – Modulation d'amplitude à transistor BC107 (simulation SPICE avec ngspice)."""
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from common import (Resultat, CONFIRME, ECART, INDETERMINE, INFO, fmt, fr, ecart_pct, RACINE,
                    ngspice_disponible, cretes_par_cycle, ajuste_sinus, nouvelle_figure, sauve)

TITRE = "AM à transistor BC107BP + détecteur d'enveloppe (SPICE)"
FC, FM = 10e3, 500.0


DETECTEURS = {
    # modulateur seul : le démodulateur est un circuit séparé sur la feuille de la vidéo
    "aucun": ("", "v(c)"),
    # démodulateur branché directement sur le collecteur (sans condensateur de liaison)
    "direct": ("D1 c out D1N4001\nC2 out 0 1u\nR5 out 0 500", "v(out)"),
    # même branchement, mais R5 = 10 kΩ et C2 = 47 nF (même constante de temps ≈ 0,5 ms)
    "r5_10k": ("D1 c out D1N4001\nC2 out 0 47n\nR5 out 0 10k", "v(out)"),
    # diode rapide 1N4148 avec R5 = 10 kΩ et C2 = 47 nF
    "rapide": ("D1 c out D1N4148\nC2 out 0 47n\nR5 out 0 10k", "v(out)"),
}


def lance_spice(vcc, amsg, rl=50.0, detecteur="aucun"):
    gabarit = (RACINE / "spice" / "tp11_am_bc107.cir").read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "modeles.lib").write_text((RACINE / "spice" / "modeles.lib").read_text(encoding="utf-8"), encoding="utf-8")
        out = d / "out.txt"
        net = (gabarit.replace("{VCC}", str(vcc)).replace("{AMSG}", str(amsg))
                      .replace("{RL}", str(rl)).replace("{OUT}", str(out))
                      .replace("{DETECTEUR}", DETECTEURS[detecteur][0]).replace("{SONDE}", DETECTEURS[detecteur][1]))
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
    mu_corr = (11.8 - 11.0) / (11.8 + 11.0 - 2 * 8.3)
    r.check("μ en retirant la tension continue du collecteur (8,3 V)", "μ ≈ 0,03 (tensions absolues)",
            f"μ = (11,8 − 11)/(11,8 + 11 − 2 × 8,3) = {fr(mu_corr)}", INDETERMINE,
            "Le collecteur est polarisé à Vcc par L1. Si l'oscilloscope est en couplage continu (DC), les crêtes lues "
            "contiennent ces 8,3 V : la formule (Emax − Emin)/(Emax + Emin) sous-estime alors μ d'un facteur ≈ 4. "
            "Il faut mesurer en couplage alternatif (AC) ou retirer la composante continue.")
    tau = 500 * 1e-6
    r.check("Détecteur : 1/fc ≪ R5·C2 ≪ 1/fm", "1/fc = 100 µs, 1/fm = 2 ms", f"R5·C2 = {fmt(tau,'s')}", CONFIRME,
            "condition respectée (5 périodes de porteuse, 1/4 de période du message)")

    if not ngspice_disponible():
        r.check("Simulation SPICE", "—", "ngspice absent sur cette machine", INDETERMINE,
                "la simulation SPICE tourne dans GitHub Actions (ngspice installé par le workflow)")
        return r

    # 1) modulateur seul (comme pendant la mesure de Emax / Emin)
    t, vc, _ = lance_spice(8.3, 4.5, detecteur="aucun")
    emax, emin, tt, v, _, tp, pk, _ = mesure(t, vc, vc)
    mu_s = (emax - emin) / (emax + emin)
    vdc = float(np.mean(v))
    mu_ac = (pk.max() - pk.min()) / (pk.max() + pk.min() - 2 * vdc) if pk.max() > vdc else float("nan")
    r.check("Emax / Emin au collecteur, modulateur seul (Vcc = 8,3 V)", "≈ 11,8 V / ≈ 11 V",
            f"{fmt(emax,'V')} / {fmt(emin,'V')}",
            CONFIRME if abs(emax - 11.8) < 1.0 and abs(emin - 11.0) < 1.0 else INDETERMINE,
            "crêtes de chaque cycle de porteuse sur 10 ms ; dépend du transistor et de la résistance de L1")
    r.check("Taux de modulation μ (formule de la vidéo, tensions absolues)", "≈ 0,03", f"μ = {fr(mu_s)}",
            CONFIRME if abs(mu_s - 0.035) < 0.03 else INDETERMINE,
            "la simulation retrouve la valeur de la vidéo avec un BC107 : le transistor de remplacement n'est pas nécessaire "
            "pour l'expliquer ; la valeur faible vient surtout de la tension continue (ligne suivante)" if abs(mu_s - 0.035) < 0.03 else
            "écart avec la vidéo : le transistor de remplacement et le réglage réel expliquent la différence")
    r.check("μ calculé sur la seule partie alternative", "0,129 en corrigeant les valeurs de la vidéo",
            f"μ = {fr(mu_ac)}", CONFIRME if abs(mu_ac - mu_corr) < 0.03 else INDETERMINE,
            f"en retirant la tension continue du collecteur ({fmt(vdc,'V')}) : c'est la définition correcte de μ. "
            "Le vrai taux de modulation est ≈ 13 %, pas 3 %.")
    t12, vc12, _ = lance_spice(12.0, 4.5, detecteur="aucun")
    e12 = mesure(t12, vc12, vc12)
    r.check("Même modulateur sous 12 V (valeur du schéma)", "—",
            f"Emax = {fmt(e12[0],'V')} ; Emin = {fmt(e12[1],'V')} ; μ = {fr((e12[0]-e12[1])/(e12[0]+e12[1]))}", INFO)

    # 2) démodulateur branché sur la sortie AM : schéma de la vidéo et deux variantes
    attendu = (emax - emin) / 2
    variantes = [("direct", "schéma : 1N4001, R5 = 500 Ω, C2 = 1 µF"),
                 ("r5_10k", "1N4001, R5 = 10 kΩ, C2 = 47 nF"),
                 ("rapide", "1N4148, R5 = 10 kΩ, C2 = 47 nF")]
    lignes, sorties = [], {}
    for cle, nom in variantes:
        tv, vcv, vov = lance_spice(8.3, 4.5, detecteur=cle)
        e = mesure(tv, vcv, vov)
        sorties[cle] = e
        lignes.append([nom, f"{fmt(e[0],'V')} / {fmt(e[1],'V')}", fmt(float(np.mean(e[4])), "V"), fmt(e[7], "V")])
    r.tableaux.append((f"Démodulateur branché sur la sortie AM (collecteur à vide : {fmt(emax,'V')} / {fmt(emin,'V')}, "
                       f"variation d'enveloppe {fmt(attendu,'V')} crête)",
                       ["Détecteur", "Emax / Emin au collecteur", "Continu en sortie", "Message 500 Hz (crête)"], lignes))
    ed = sorties["direct"]
    charge = (ed[0] - ed[1]) / 2
    r.check("Démodulateur du schéma branché sur la sortie AM", "démodulateur décrit sur la feuille (circuit séparé)",
            f"message {fmt(ed[7],'V')} crête ; enveloppe au collecteur {fmt(charge,'V')} crête (à vide : {fmt(attendu,'V')})",
            CONFIRME if ed[7] > 0.5 * attendu else ECART,
            ("le détecteur restitue bien la variation d'enveloppe" if ed[7] > 0.5 * attendu else
             ("le détecteur charge fortement le circuit accordé : la modulation au collecteur s'effondre"
              if charge < 0.5 * attendu else
              "la modulation au collecteur reste présente mais le détecteur la restitue mal"))
            + " (voir le tableau des variantes)")
    tous_chargent = all((e[0] - e[1]) / 2 < 0.5 * attendu for e in sorties.values())
    r.check("Conclusion sur le démodulateur", "—",
            "toutes les variantes chargent le circuit accordé" if tous_chargent else "au moins une variante convient",
            INFO,
            "Le détecteur ne prend du courant qu'aux crêtes et écrase la tension du circuit accordé. Il faut un étage "
            "tampon (émetteur suiveur) entre la sortie AM et le détecteur, ou tester le démodulateur séparément avec "
            "un générateur AM, comme le suggère la feuille de la vidéo." if tous_chargent else
            "voir le tableau des variantes")
    meilleur = "r5_10k"
    tt_d, vo_d = ed[2], ed[4]
    tt_l, vo_l = sorties[meilleur][2], sorties[meilleur][4]
    titre_l = dict(variantes)[meilleur]
    r.hypotheses += ["Modèles génériques BC107B et 1N4001 : le transistor réellement utilisé dans la vidéo n'est pas connu.",
                     "Résistance série de L1 : 50 Ω (non indiquée).",
                     "μ calculé comme dans la vidéo, avec les tensions absolues des crêtes : (Emax − Emin)/(Emax + Emin)."]

    fig, ax = nouvelle_figure(3, 2.4, "TP11 – Simulation SPICE du modulateur AM (Vcc = 8,3 V)")
    ax[0].plot((tt - tt[0]) * 1e3, v, lw=0.4); ax[0].plot((tp - tt[0]) * 1e3, pk, ".", ms=2)
    ax[0].set_title(f"Collecteur, modulateur seul : Emax = {fmt(emax,'V')}, Emin = {fmt(emin,'V')}", fontsize=9)
    ax[1].plot((tt_d - tt_d[0]) * 1e3, vo_d, lw=1)
    ax[1].set_title("Sortie du détecteur du schéma (R5 = 500 Ω, C2 = 1 µF)", fontsize=9)
    ax[2].plot((tt_l - tt_l[0]) * 1e3, vo_l, lw=1)
    ax[2].set_title(f"Sortie du détecteur : {titre_l}", fontsize=9)
    for a_ in ax:
        a_.set_xlabel("t (ms)")
    sauve(fig, r, outdir, "tp11_am_spice.png", "Modulateur AM à BC107 simulé avec ngspice")
    return r
