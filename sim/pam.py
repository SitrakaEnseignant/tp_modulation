"""Moteur PAM commun aux TP03, TP08, TP12 et TP13."""
import numpy as np

from common import sinad_db, passe_bas

FS_SIM = 2.048e6  # multiple entier de toutes les fréquences d horloge (2 à 64 kHz)


def horloge(t, fs, rapport):
    """Train d'impulsions unipolaire 0/1 de fréquence fs et de rapport cyclique `rapport`."""
    return ((t * fs) % 1.0 < rapport).astype(float)


def pam(t, msg, fs, rapport=0.5, mode="naturel"):
    """Signal PAM.

    naturel  : m(t)·p(t) (le sommet suit le message)
    flat-top : m(nTs) maintenu pendant τ = rapport·Ts
    sh       : sample & hold, m(nTs) maintenu pendant Ts
    """
    if mode == "naturel":
        return msg * horloge(t, fs, rapport)
    n = np.floor(t * fs)
    t_ech = n / fs
    idx = np.clip(np.searchsorted(t, t_ech), 0, len(t) - 1)
    tenu = msg[idx]
    if mode == "sh":
        return tenu
    return tenu * horloge(t, fs, rapport)


def demodule(x, fc, ordre):
    return passe_bas(x, FS_SIM, fc, ordre)


def essai(fm, fs, mode="naturel", rapport=0.5, fc=3.4e3, ordre=4, amp=1.0, duree=None):
    """Renvoie (t, msg, pam, sortie, sinad_dB)."""
    if duree is None:
        duree = 12e-3 + 10 / fm
    t = np.arange(0, duree, 1 / FS_SIM)
    msg = amp * np.sin(2 * np.pi * fm * t)
    p = pam(t, msg, fs, rapport, mode)
    y = demodule(p, fc, ordre)
    sel = t > 10e-3
    return t, msg, p, y, sinad_db(y[sel], t[sel], fm)


def qualite(sinad):
    if sinad >= 30:
        return "correct"
    if sinad >= 20:
        return "limite"
    return "dégradé"


def attenuation_ouverture(f, tau):
    """Effet d'ouverture du flat-top : |sinc(f·τ)|."""
    return abs(np.sinc(f * tau))


def txt_sinad(sd):
    """Texte du SINAD ; au-delà de 60 dB le modèle idéal n'a plus de sens physique."""
    from common import fr
    return "> 60 dB" if sd > 60 else f"{fr(sd)} dB"
