"""TP10 – Modulateur FM à NE555 (astable modulé par la broche 5)."""
import math
import numpy as np

from common import Resultat, CONFIRME, ECART, INDETERMINE, INFO, fmt, fr, ecart_pct, nouvelle_figure, sauve

TITRE = "FM avec un NE555 (astable, message sur la broche 5)"
VCC = 5.0
R1, R2, C1, R3 = 1.5e3, 1.5e3, 0.1e-6, 10e3
IS, N, VT = 7.0e-9, 1.8, 0.02585          # diode 1N4007 (modèle SPICE courant)
VSAT = 0.1                                 # transistor de décharge (broche 7) saturé


def vcv_repos(r3=R3):
    """Tension de la broche 5 : pont interne 5 kΩ / 10 kΩ, avec R3 vers la masse."""
    bas = 10e3 if r3 is None else (10e3 * r3) / (10e3 + r3)
    return VCC * bas / (5e3 + bas)


def courant_charge(v, u0):
    """Résout (VCC − v − u)/R1 = Is(e^(u/nVt) − 1) + u/R2 ; u = tension aux bornes de D ∥ R2."""
    u = u0
    for _ in range(30):
        e = IS * math.expm1(u / (N * VT))
        f = (VCC - v - u) / R1 - e - u / R2
        df = -1 / R1 - (e + IS) / (N * VT) - 1 / R2
        du = f / df
        u -= du
        if abs(du) < 1e-9:
            break
    return (VCC - v - u) / R1, u


def simule(c1=C1, r3=R3, am=0.0, fm=200.0, duree=20e-3, dt=0.05e-6, diode=True):
    n = int(duree / dt)
    v = vcv_repos(r3) / 2
    charge = True
    u = 0.6
    t_bas = []
    out = np.empty(n)
    cap = np.empty(n)
    v0 = vcv_repos(r3)
    for k in range(n):
        t = k * dt
        vcv = v0 + am * math.sin(2 * math.pi * fm * t)
        if charge:
            if diode:
                i, u = courant_charge(v, u)
            else:
                i = (VCC - v) / (R1 + R2)
            v += i / c1 * dt
            if v >= vcv:
                charge = False
        else:
            v -= (v - VSAT) / (R2 * c1) * dt
            if v <= vcv / 2:
                charge = True
                t_bas.append(t)
        out[k] = 1.0 if charge else 0.0
        cap[k] = v
    tb = np.array(t_bas)
    return tb[1:], np.diff(tb), out, cap, dt


def run(outdir):
    r = Resultat(10, TITRE, "Simulation pas à pas (Python) du 555 : comparateurs, bascule, décharge, diode 1N4007 "
                            "(modèle de Shockley), broche 5 modulée.")
    v0 = vcv_repos()
    r.check("Tension de repos de la broche 5", "non mesurée",
            f"{fmt(v0,'V')} (au lieu de 2/3·Vcc = {fmt(2/3*VCC,'V')}, à cause de R3 = 10 kΩ)", INFO,
            f"seuils de basculement : {fmt(v0,'V')} et {fmt(v0/2,'V')}")
    tb, per, out, cap, dt = simule(duree=3e-3)
    f_libre = 1 / per[2:].mean()
    duty = out[int(1e-3/dt):].mean()
    r.check("Fréquence sans message (C1 = 0,1 µF)", "≈ 11 kHz mesurés", fmt(f_libre, "Hz"), ECART,
            f"écart {fr(ecart_pct(f_libre, 11e3),2)} % : les valeurs lues sur le schéma ne donnent pas 11 kHz")
    c_eq = C1 * f_libre / 11e3
    r.check("Condensateur qui donnerait 11 kHz", "C1 lu « 0,1 µF »", fmt(c_eq, "F"), INDETERMINE,
            "f est inversement proportionnelle à C1 : un condensateur de 47 nF (valeur normalisée) donnerait ≈ 11 kHz ; "
            "à vérifier sur la photo du montage")
    tb47, per47, *_ = simule(c1=47e-9, duree=2e-3)
    r.check("Hypothèse C1 = 47 nF", "≈ 11 kHz", fmt(1 / per47[2:].mean(), "Hz"), INFO,
            "hypothèse compatible avec la mesure de la vidéo")
    r.check("Rapport cyclique avec la diode", "« diode : charge et décharge égales »", f"{fr(100*duty)} %",
            CONFIRME if 40 < 100 * duty < 60 else ECART,
            "Avec R3 = 10 kΩ, les seuils sont 2,5 V et 1,25 V : la charge vers ≈ 4,4 V (5 V − diode) est plus rapide "
            "que la décharge vers 0 V, même avec R1 = R2. Sans R3 (seuils 3,33 V et 1,67 V) on obtiendrait ≈ 56 %.")
    r.check("Amplitude de sortie", "≈ 5,4 V avec Vcc = 5 V", "NE555 bipolaire : niveau haut ≈ Vcc − 1,7 V ≈ 3,3 V",
            INDETERMINE, "5,4 V dépasse l'alimentation : lecture crête-à-crête avec dépassement, sonde mal réglée ou 555 CMOS")

    # ---- FM : message 200 Hz, 3 Vpp sur la broche 5 (C2 = 10 µF : réactance 80 Ω à 200 Hz, négligeable)
    am = 1.5
    for c1, nom in ((C1, "0,1 µF"), (47e-9, "47 nF")):
        tb, per, out, cap, dt = simule(c1=c1, am=am, duree=15e-3)
        f = 1 / per
        sel = tb > 5e-3
        fmin, fmax = f[sel].min(), f[sel].max()
        r.tableaux.append((f"Tableau de la vidéo rempli par la simulation (C1 = {nom}, message 200 Hz, 3 Vpp)",
                           ["Segment", "Fréquence simulée"],
                           [["Alternance positive (fmin)", fmt(fmin, "Hz")], ["Alternance négative (fmax)", fmt(fmax, "Hz")],
                            ["Δf = (fmax − fmin)/2", fmt((fmax - fmin) / 2, "Hz")]]))
        if c1 == C1:
            tb_p, f_p = tb, f
    r.check("Sens de la modulation", "fréquence basse sur l'alternance positive",
            "broche 5 plus haute → seuils plus hauts → charge plus longue → fréquence plus basse", CONFIRME)
    r.check("Linéarité", "—", "Δf asymétrique : la charge ralentit fortement quand Vcv approche Vcc − 0,6 V", INFO,
            "avec 1,5 V crête autour de 2,5 V, la broche 5 monte à 4 V : le 555 est très non linéaire ; un message plus faible serait plus fidèle")
    r.hypotheses += ["Pont interne 5 kΩ / 5 kΩ / 5 kΩ du 555 ; transistor de décharge saturé à 0,1 V.",
                     "Diode 1N4007 : Is = 7 nA, n = 1,8 ; sortie du générateur idéale."]

    fig, ax = nouvelle_figure(2, 2.6, "TP10 – 555 en modulateur FM (simulation)")
    tb, per, out, cap, dt = simule(c1=47e-9, am=0.0, duree=0.4e-3)
    tt = np.arange(len(cap)) * dt * 1e6
    ax[0].plot(tt, cap, lw=1, label="tension de C1 (broches 2 et 6)")
    ax[0].plot(tt, out * 3.3, lw=0.8, label="sortie (broche 3)")
    ax[0].axhline(v0, ls="--", c="r", lw=0.7); ax[0].axhline(v0 / 2, ls="--", c="g", lw=0.7)
    ax[0].set_xlabel("t (µs)"); ax[0].legend(fontsize=7, loc="upper right"); ax[0].set_title("Sans message (C1 = 47 nF)", fontsize=9)
    ax[1].plot(tb_p * 1e3, f_p / 1e3, ".", ms=2)
    ax[1].set_xlabel("t (ms)"); ax[1].set_ylabel("kHz"); ax[1].set_title("Fréquence de chaque cycle, message 200 Hz 3 Vpp (C1 = 0,1 µF)", fontsize=9)
    sauve(fig, r, outdir, "tp10_555.png", "Astable 555 et fréquence instantanée modulée")
    return r
