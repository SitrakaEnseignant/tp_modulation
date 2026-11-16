"""Moteur PWM commun aux TP04, TP05 et TP06 (comparateur message / rampe)."""
import numpy as np

from common import sinad_db, passe_bas

FS_SIM = 2.048e6


def rampe(t, fs, amp):
    """Dent de scie de −amp à +amp, fréquence fs."""
    return amp * (2 * ((t * fs) % 1.0) - 1)


def pwm(t, msg, fs, amp_rampe=1.0, vhaut=5.0):
    """Sortie haute quand le message dépasse la rampe : largeur ∝ amplitude du message."""
    return np.where(msg > rampe(t, fs, amp_rampe), vhaut, 0.0)


def largeurs(x, t):
    """Largeur de chaque impulsion haute (s)."""
    h = x > 0.5 * x.max()
    d = np.diff(h.astype(int))
    up = np.where(d == 1)[0]
    dn = np.where(d == -1)[0]
    if len(up) == 0 or len(dn) == 0:
        return np.array([]), np.array([])
    dn = dn[dn > up[0]]
    n = min(len(up), len(dn))
    return t[up[:n]], (dn[:n] - up[:n]) / FS_SIM


def essai(fm, fs, amp, amp_rampe=1.0, fc=None, ordre=4, vhaut=5.0, duree=None):
    if duree is None:
        duree = 12e-3 + 10 / fm
    if fc is None:
        fc = min(3.4e3, fs / 3)
    t = np.arange(0, duree, 1 / FS_SIM)
    msg = amp * np.sin(2 * np.pi * fm * t)
    p = pwm(t, msg, fs, amp_rampe, vhaut)
    y = passe_bas(p, FS_SIM, fc, ordre)
    sel = t > 10e-3
    return t, msg, p, y, sinad_db(y[sel], t[sel], fm)
