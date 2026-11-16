"""TP11 – Modulation d'amplitude à transistor BC107 (simulation ngspice : ngspice/tp11_am_bc107.cir)."""
import numpy as np

from common import (Resultat, CONFIRME, ECART, INDETERMINE, INFO, LEVE, REDUIT, RESTE, fmt, fr, ecart_pct,
                    cretes_par_cycle, ajuste_sinus, nouvelle_figure, sauve)
import ngspice_outil as ng

TITRE = "AM à transistor BC107BP + détecteur d'enveloppe (ngspice)"
FC, FM = 10e3, 500.0
CIRCUIT = "tp11_am_bc107.cir"
SANS_DETECTEUR = dict(R5V="1T", C2V="1p")


def mesure(t, vc, vout):
    """Emax / Emin de l'enveloppe du collecteur sur les 10 dernières ms (comme aux curseurs)."""
    sel = t > 20e-3
    tt, v, vo = t[sel], vc[sel], vout[sel]
    tp, pk = cretes_par_cycle(v, tt, FC)
    amp_dem, *_ = ajuste_sinus(vo, tt, FM)
    return dict(emax=float(pk.max()), emin=float(pk.min()), t=tt, v=v, vo=vo, tp=tp, pk=pk, dem=amp_dem,
                vdc=float(np.mean(v)))


def run(outdir):
    r = Resultat(11, TITRE, "Simulation ngspice du schéma de la vidéo (modèles génériques BC107B et 1N4001).")
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
            "Le collecteur est polarisé à Vcc par L1. En couplage continu (DC) à l'oscilloscope, les crêtes lues "
            "contiennent ces 8,3 V : la formule (Emax − Emin)/(Emax + Emin) sous-estime alors μ d'un facteur ≈ 4.")
    r.check("Détecteur : 1/fc ≪ R5·C2 ≪ 1/fm", "1/fc = 100 µs, 1/fm = 2 ms", f"R5·C2 = {fmt(500e-6,'s')}", CONFIRME,
            "condition respectée (5 périodes de porteuse, 1/4 de période du message)")

    if not ng.disponible():
        r.check("Simulation ngspice", "—", "ngspice absent sur cette machine", INDETERMINE,
                "la simulation tourne dans GitHub Actions (ngspice installé par le workflow)")
        return r

    # 1) modulateur seul (comme pendant la mesure de Emax / Emin)
    m0 = mesure(*_courbes(VALIM=8.3, **SANS_DETECTEUR))
    mu_s = (m0["emax"] - m0["emin"]) / (m0["emax"] + m0["emin"])
    mu_ac = (m0["emax"] - m0["emin"]) / (m0["emax"] + m0["emin"] - 2 * m0["vdc"])
    r.check("[ngspice] Emax / Emin au collecteur, modulateur seul (8,3 V)", "≈ 11,8 V / ≈ 11 V",
            f"{fmt(m0['emax'],'V')} / {fmt(m0['emin'],'V')}",
            CONFIRME if abs(m0["emax"] - 11.8) < 1.0 and abs(m0["emin"] - 11.0) < 1.0 else INDETERMINE,
            "crêtes de chaque cycle de porteuse sur 10 ms")
    r.check("[ngspice] μ avec la formule de la vidéo (tensions absolues)", "≈ 0,03", f"μ = {fr(mu_s)}",
            CONFIRME if abs(mu_s - 0.035) < 0.03 else INDETERMINE,
            "la simulation retrouve la valeur de la vidéo avec un BC107 ordinaire")
    r.check("[ngspice] μ sur la seule partie alternative", f"{fr(mu_corr)} en corrigeant la vidéo", f"μ = {fr(mu_ac)}",
            CONFIRME if abs(mu_ac - mu_corr) < 0.03 else INDETERMINE,
            f"tension continue du collecteur : {fmt(m0['vdc'],'V')}. Le vrai taux de modulation est ≈ 13 %, pas 3 %.")
    m12 = mesure(*_courbes(VALIM=12, **SANS_DETECTEUR))
    r.check("[ngspice] Même modulateur sous 12 V (valeur du schéma)", "—",
            f"Emax = {fmt(m12['emax'],'V')} ; Emin = {fmt(m12['emin'],'V')} ; "
            f"μ (partie alternative) = {fr((m12['emax']-m12['emin'])/(m12['emax']+m12['emin']-2*m12['vdc']))}", INFO)

    # 2) démodulateur branché sur la sortie AM
    attendu = (m0["emax"] - m0["emin"]) / 2
    variantes = [("schéma : R5 = 500 Ω, C2 = 1 µF", dict(R5V="500", C2V="1u")),
                 ("R5 = 10 kΩ, C2 = 47 nF", dict(R5V="10k", C2V="47n"))]
    lignes, sorties = [], []
    for nom, p in variantes:
        e = mesure(*_courbes(VALIM=8.3, **p))
        sorties.append((nom, e))
        lignes.append([nom, f"{fmt(e['emax'],'V')} / {fmt(e['emin'],'V')}", fmt(float(np.mean(e["vo"])), "V"), fmt(e["dem"], "V")])
    r.tableaux.append((f"Démodulateur branché sur la sortie AM (collecteur à vide : {fmt(m0['emax'],'V')} / "
                       f"{fmt(m0['emin'],'V')}, variation d'enveloppe {fmt(attendu,'V')} crête)",
                       ["Détecteur", "Emax / Emin au collecteur", "Continu en sortie", "Message 500 Hz (crête)"], lignes))
    tous_chargent = all((e["emax"] - e["emin"]) / 2 < 0.5 * attendu for _, e in sorties)
    ed = sorties[0][1]
    r.check("[ngspice] Démodulateur du schéma branché sur la sortie AM", "démodulateur décrit sur la feuille (circuit séparé)",
            f"message {fmt(ed['dem'],'V')} crête ; enveloppe au collecteur {fmt((ed['emax']-ed['emin'])/2,'V')} crête "
            f"(à vide : {fmt(attendu,'V')})", ECART if tous_chargent else CONFIRME,
            "Le détecteur ne prend du courant qu'aux crêtes et écrase la tension du circuit accordé, même avec R5 = 10 kΩ. "
            "Il faut un étage tampon (émetteur suiveur) entre la sortie AM et le détecteur." if tous_chargent else
            "le détecteur restitue la variation d'enveloppe")

    r.doute("Le μ très faible vient-il du transistor de remplacement ?", LEVE,
            f"Non. Avec un BC107 ordinaire, ngspice donne aussi μ ≈ {fr(mu_s)} avec la formule de la vidéo. La valeur faible "
            f"vient des 8,3 V continus inclus dans Emax et Emin ; sans eux μ ≈ {fr(mu_ac)}.")
    r.doute("μ = 0,029 ou 0,035 ?", LEVE,
            "Les deux sont des calculs sur des tensions absolues. La grandeur physique est μ ≈ 0,13 (partie alternative).")
    r.doute("Le démodulateur peut-il être branché directement sur la sortie AM ?", LEVE if tous_chargent else REDUIT,
            "Non : il charge le circuit accordé et la modulation s'effondre ; un étage tampon est nécessaire.")
    r.doute("Référence exacte du transistor « two and triple five »", RESTE,
            "La simulation ne peut pas identifier le composant ; elle montre seulement qu'il ne change pas la conclusion.")
    r.hypotheses += ["Modèles génériques BC107B et 1N4001 ; résistance série de L1 : 50 Ω (non indiquée).",
                     "μ calculé comme dans la vidéo avec les crêtes absolues, puis sur la seule partie alternative."]

    fig, ax = nouvelle_figure(2, 2.6, "TP11 – Simulation ngspice du modulateur AM (Vcc = 8,3 V)")
    ax[0].plot((m0["t"] - m0["t"][0]) * 1e3, m0["v"], lw=0.4); ax[0].plot((m0["tp"] - m0["t"][0]) * 1e3, m0["pk"], ".", ms=2)
    ax[0].axhline(m0["vdc"], c="0.5", ls="--", lw=0.8, label="tension continue du collecteur"); ax[0].legend(fontsize=7)
    ax[0].set_title(f"Collecteur, modulateur seul : Emax = {fmt(m0['emax'],'V')}, Emin = {fmt(m0['emin'],'V')}", fontsize=9)
    ax[1].plot((ed["t"] - ed["t"][0]) * 1e3, ed["v"], lw=0.4, label="collecteur avec détecteur")
    ax[1].plot((ed["t"] - ed["t"][0]) * 1e3, ed["vo"], lw=1, label="sortie du détecteur")
    ax[1].set_title("Détecteur du schéma branché : la modulation s'effondre", fontsize=9); ax[1].legend(fontsize=7)
    for a_ in ax:
        a_.set_xlabel("t (ms)")
    sauve(fig, r, outdir, "tp11_am_ngspice.png", "Modulateur AM à BC107 simulé avec ngspice")
    return r


def _courbes(**params):
    t, (vc, vo) = ng.lance(CIRCUIT, pas=0.5e-6, **params)
    return t, vc, vo
