"""TP01 – Modulation d'amplitude, maquette Omega ETB-96 (Dr. Lalchand Patle)."""
import numpy as np

import ngspice_outil as ng
from common import (Resultat, CONFIRME, ECART, INDETERMINE, INFO, LEVE, REDUIT, RESTE, fmt, fr, ecart_pct,
                    freq_moyenne, cretes_par_cycle, spectre, detecteur_enveloppe, passe_bas,
                    sinad_db, nouvelle_figure, sauve)

TITRE = "AM – maquette Omega ETB-96 (2 transistors BF-195, détecteur OA-79)"


def run(outdir):
    r = Resultat(1, TITRE, "Modèle comportemental (Python) : signal AM idéal + détecteur diode/RC.")
    # ---- valeurs relevées dans la vidéo
    fm_div, fm_tdiv = 4, 25e-6          # 4 div × 25 µs
    fc_div, fc_tdiv = 3, 2.5e-6         # 3 div × 2,5 µs
    vmax, vmin = 4.8, 0.8
    fm = 1 / (fm_div * fm_tdiv)
    fc = 1 / (fc_div * fc_tdiv)
    m = (vmax - vmin) / (vmax + vmin)
    ac = (vmax + vmin) / 2

    # ---- simulation du signal AM vu à l'oscilloscope
    fs = 20e6
    t = np.arange(0, 1.5e-3, 1 / fs)   # 200 périodes de porteuse, 15 du message
    msg = np.cos(2 * np.pi * fm * t)
    s = ac * (1 + m * msg) * np.cos(2 * np.pi * fc * t)

    f_msg_mes = freq_moyenne(msg, t)
    f_por_mes = freq_moyenne(np.cos(2 * np.pi * fc * t), t)
    tp, pk = cretes_par_cycle(s, t, fc)
    vmax_s, vmin_s = float(pk.max()), float(pk.min())
    m_s = (vmax_s - vmin_s) / (vmax_s + vmin_s)

    r.check("Fréquence du message", "4 div × 25 µs → 10 kHz (générateur : 10,0517 kHz)",
            fmt(f_msg_mes, "Hz", 4), CONFIRME if abs(ecart_pct(f_msg_mes, 10.0517e3)) < 1 else ECART,
            f"écart avec l'affichage du générateur : {fr(ecart_pct(f_msg_mes, 10.0517e3),2)} %")
    # résolution de lecture ± 0,2 div
    fc_lo, fc_hi = 1 / ((fc_div + 0.2) * fc_tdiv), 1 / ((fc_div - 0.2) * fc_tdiv)
    r.check("Fréquence de la porteuse", "3 div × 2,5 µs → ≈ 133 kHz", fmt(f_por_mes, "Hz", 4),
            CONFIRME, f"lecture ± 0,2 div → porteuse entre {fmt(fc_lo,'Hz')} et {fmt(fc_hi,'Hz')}")
    r.check("Vmax / Vmin de l'enveloppe", "4,8 V / 0,8 V", f"{fmt(vmax_s,'V')} / {fmt(vmin_s,'V')}",
            CONFIRME if abs(vmax_s - vmax) < 0.05 and abs(vmin_s - vmin) < 0.05 else ECART,
            "crêtes de chaque cycle de porteuse (lecture aux curseurs simulée)")
    r.check("Taux de modulation m", "0,714 (71,4 %)", f"{fr(m_s)} ({fr(100*m_s)} %)",
            CONFIRME if abs(m_s - 0.714) < 0.005 else ECART)

    # ---- spectre : raies à fc et fc ± fm
    f, X = spectre(s, fs, fenetre=False)
    def raie(f0):
        k = np.argmin(abs(f - f0)); return float(X[max(k-3,0):k+4].max())
    a_c, a_l, a_u = raie(fc), raie(fc - fm), raie(fc + fm)
    r.check("Raies latérales (fc ± fm)", "non mesurées dans la vidéo",
            f"porteuse {fmt(a_c,'V')} ; latérales {fmt(a_l,'V')} et {fmt(a_u,'V')} (théorie m·Ac/2 = {fmt(m*ac/2,'V')})",
            INFO, f"raies à {fmt(fc-fm,'Hz')} et {fmt(fc+fm,'Hz')} ; bande occupée B = 2·fm = {fmt(2*fm,'Hz')}")
    eta = m**2 / (2 + m**2)
    r.check("Rendement en puissance", "non calculé dans la vidéo", f"η = m²/(2+m²) = {fr(100*eta)} %", INFO)

    # ---- détecteur d'enveloppe de la maquette : OA-79 + 10 kΩ // 0,01 µF
    R, C = 10e3, 0.01e-6
    tau = R * C
    tau_max = np.sqrt(1 - m**2) / (m * 2 * np.pi * fm)
    fs2 = 50e6

    def essai(C_, fm_):
        global t2, sel
        t2 = np.arange(0, 0.3e-3 + 3 / fm_, 1 / fs2)
        sel = t2 > 0.3e-3
        s_ = ac * (1 + m * np.cos(2 * np.pi * fm_ * t2)) * np.cos(2 * np.pi * fc * t2)
        v_ = detecteur_enveloppe(s_, 1 / fs2, R, C_, vd=0.2, rs=300.0)
        vf = passe_bas(v_, fs2, 3 * fm_, 4)          # enlève l'ondulation résiduelle de porteuse
        return s_, v_, sinad_db(vf[sel], t2[sel], fm_)

    _, _, sin_1k = essai(C, 1e3)                      # même détecteur, message à 1 kHz
    _, v_ok, sin_ok = essai(1.5e-9, fm)               # τ = 15 µs, juste sous la limite
    s2, v, sin_db = essai(C, fm)
    r.check("Détecteur 10 kΩ / 0,01 µF : condition RC ≤ √(1−m²)/(m·ωm)",
            "message récupéré montré, distorsion non commentée",
            f"RC = {fmt(tau,'s')} > limite {fmt(tau_max,'s')} → SINAD {fr(sin_db)} dB à 10 kHz",
            ECART if tau > tau_max else CONFIRME,
            "La constante de temps est trop grande pour un message de 10 kHz à m = 0,71 : le condensateur ne suit pas "
            "la descente de l'enveloppe (écrêtage en diagonale), le message récupéré est déformé.")
    r.check("Même détecteur avec un message de 1 kHz", "—", f"SINAD {fr(sin_1k)} dB", INFO,
            "pas d'écrêtage en diagonale ; la distorsion restante vient du seuil de la diode (Vmin = 0,8 V est proche du seuil)")
    r.check("Détecteur avec RC = 15 µs (1,5 nF)", "—", f"SINAD {fr(sin_ok)} dB à 10 kHz", INFO,
            f"bonne restitution, mais l'ondulation de porteuse est forte (fc/fm = {fr(fc/fm)} seulement) et doit être filtrée")
    fm_ok = np.sqrt(1 - m**2) / (m * 2 * np.pi * tau)
    r.check("Fréquence maximale du message pour ce détecteur", "—", fmt(fm_ok, "Hz"), INFO,
            "au-delà, l'écrêtage en diagonale apparaît (m = 0,714, RC = 100 µs)")
    _ngspice(r, m, outdir)
    r.hypotheses += [
        "Signal AM idéal : la non-linéarité des transistors BF-195 n'est pas modélisée.",
        "Diode OA-79 (germanium) modélisée par un seuil de 0,2 V et 300 Ω en série.",
        "Valeurs du détecteur (10 kΩ, 0,01 µF) prises sur le schéma de la maquette ETB-96.",
    ]

    # ---- figures
    fig, ax = nouvelle_figure(3, 2.6, "TP01 – Signal AM simulé (fc ≈ 133 kHz, fm = 10 kHz, m = 0,714)")
    k = t < 0.3e-3
    ax[0].plot(t[k]*1e6, s[k], lw=0.6); ax[0].plot(tp[tp<0.3e-3]*1e6, pk[tp<0.3e-3], ".", ms=3)
    ax[0].axhline(vmax, ls="--", c="r", lw=0.8); ax[0].axhline(vmin, ls="--", c="g", lw=0.8)
    ax[0].set_xlabel("t (µs)"); ax[0].set_ylabel("V"); ax[0].set_title("Sortie AM et crêtes (Vmax = 4,8 V, Vmin = 0,8 V)", fontsize=9)
    kf = (f > 80e3) & (f < 190e3)
    ax[1].stem(f[kf]/1e3, X[kf], markerfmt=" ", basefmt=" "); ax[1].set_xlabel("f (kHz)"); ax[1].set_ylabel("V crête")
    ax[1].set_title("Spectre : porteuse et deux raies latérales", fontsize=9)
    k2 = t2 > 0.2e-3
    ax[2].plot(t2[k2]*1e6, s2[k2], lw=0.3, c="0.75", label="AM")
    ax[2].plot(t2[k2]*1e6, v[k2], lw=1.2, label="détecteur 10 kΩ / 0,01 µF")
    ax[2].plot(t2[k2]*1e6, v_ok[k2], lw=1.0, label="détecteur 10 kΩ / 1,5 nF")
    ax[2].set_xlabel("t (µs)"); ax[2].legend(fontsize=7, loc="upper right")
    ax[2].set_title("Démodulation : écrêtage en diagonale avec RC = 100 µs", fontsize=9)
    sauve(fig, r, outdir, "tp01_am.png", "Signal AM, spectre et détecteur d'enveloppe simulés")
    return r


def _ngspice(r, m, outdir):
    if not ng.disponible():
        r.check("[ngspice] Détecteur OA-79", "—", "ngspice absent sur cette machine", INDETERMINE,
                "la simulation tourne dans GitHub Actions")
        return
    res = {}
    for fm, c, tstop in ((10e3, "0.01u", "1m"), (1e3, "0.01u", "4m"), (10e3, "1.5n", "1m")):
        t, (am, out) = ng.lance("tp01_detecteur_oa79.cir", pas=0.02e-6, FMSG=f"{fm:g}", CDET=c, TSTOP=tstop)
        fs = 1 / (t[1] - t[0])
        sel = t > t[-1] - 3 / fm
        vf = passe_bas(out, fs, 3 * fm, 4)
        res[(fm, c)] = (sinad_db(vf[sel], t[sel], fm), t, am, out)
    s10, s1, s15 = res[(10e3, "0.01u")][0], res[(1e3, "0.01u")][0], res[(10e3, "1.5n")][0]
    r.check("[ngspice] Détecteur de la maquette (OA-79, 10 kΩ, 0,01 µF), message 10 kHz", "message montré déformé ?",
            f"SINAD {fr(s10)} dB", ECART if s10 < 20 else CONFIRME,
            "même conclusion que le modèle Python : écrêtage en diagonale à 10 kHz")
    r.check("[ngspice] Même détecteur, message 1 kHz", "—", f"SINAD {fr(s1)} dB", INFO)
    r.check("[ngspice] Détecteur avec 1,5 nF, message 10 kHz", "—", f"SINAD {fr(s15)} dB", INFO)
    r.doute("Le détecteur de la maquette restitue-t-il le message de 10 kHz utilisé dans la vidéo ?", LEVE,
            f"Non : ngspice (diode germanium SPICE) donne un SINAD de {fr(s10)} dB à 10 kHz contre {fr(s1)} dB à 1 kHz. "
            "La constante de temps 10 kΩ × 0,01 µF = 100 µs est faite pour un message audio de 1 à 2 kHz.")
    r.doute("Circuit interne de l'oscillateur de porteuse (≈ 133 kHz)", RESTE,
            "Il n'est pas imprimé sur la maquette : la porteuse est mesurée, pas simulée.")
    _, t, am, out = res[(10e3, "0.01u")]
    fig, ax = nouvelle_figure(1, 3, "TP01 – ngspice : détecteur OA-79, 10 kΩ // 0,01 µF, message 10 kHz")
    k = t > 0.6e-3
    ax[0].plot((t[k] - 0.6e-3) * 1e6, am[k], lw=0.3, c="0.7", label="signal AM")
    ax[0].plot((t[k] - 0.6e-3) * 1e6, out[k], lw=1.3, label="sortie du détecteur")
    ax[0].set_xlabel("t (µs)"); ax[0].legend(fontsize=7, loc="upper right")
    sauve(fig, r, outdir, "tp01_detecteur_ngspice.png", "Écrêtage en diagonale simulé dans ngspice")
