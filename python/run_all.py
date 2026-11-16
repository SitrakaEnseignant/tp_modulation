"""Lance les simulations des 13 TP et écrit results/RAPPORT.md + results/resultats.json.

Usage : python python/run_all.py [numéros de TP ...]
"""
import importlib
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RACINE, ecrire_json, CONFIRME, ECART, INDETERMINE, INFO, LIENS  # noqa: E402

MODULES = {
    1: "tp01_am_omega", 2: "tp02_fm_kit", 3: "tp03_pam_st2110", 4: "tp04_pwm_st2110",
    5: "tp05_pwm_excel", 6: "tp06_pwm_dcl08", 7: "tp07_fm_icl8038", 8: "tp08_pam_excel",
    9: "tp09_pll_lm565", 10: "tp10_fm_555", 11: "tp11_am_bc107", 12: "tp12_pam_st2110",
    13: "tp13_pam_vinytics",
}
ICONE = {CONFIRME: "✅", ECART: "❌", INDETERMINE: "⚠️", INFO: "ℹ️"}


def md_table(entetes, lignes):
    out = ["| " + " | ".join(entetes) + " |", "|" + "---|" * len(entetes)]
    for l in lignes:
        out.append("| " + " | ".join(str(c).replace("|", "/").replace("\n", " ") for c in l) + " |")
    return "\n".join(out)


def main(selection):
    res_dir = RACINE / "results"
    fig_dir = res_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    tous, erreurs = [], []
    for n in selection:
        nom = MODULES[n]
        t0 = time.time()
        try:
            mod = importlib.import_module(nom)
            r = mod.run(fig_dir).to_dict()
            r["duree_s"] = round(time.time() - t0, 1)
            tous.append(r)
            print(f"TP{n:02d} terminé en {r['duree_s']} s : " +
                  ", ".join(f"{c['statut']}" for c in r["checks"]))
        except Exception:
            tb = traceback.format_exc()
            print(f"TP{n:02d} ERREUR\n{tb}", file=sys.stderr)
            erreurs.append((n, tb))

    ecrire_json(res_dir / "resultats.json", tous)

    # ------------------------------------------------------ rapport Markdown
    L = ["# Rapport des simulations – TP de modulation (AM, FM, PAM, PWM)", "",
         "Ce rapport est produit automatiquement par GitHub Actions (`.github/workflows/simulations.yml`).",
         "Chaque TP compare les valeurs relevées dans la vidéo avec une simulation.", "",
         "Légende : ✅ confirmé · ❌ écart (la simulation contredit la vidéo) · "
         "⚠️ à vérifier (dépend d'une valeur inconnue) · ℹ️ valeur prédite", ""]
    tot = {CONFIRME: 0, ECART: 0, INDETERMINE: 0, INFO: 0}
    synth = []
    for r in tous:
        cnt = {k: sum(c["statut"] == k for c in r["checks"]) for k in tot}
        for k in tot:
            tot[k] += cnt[k]
        synth.append([f"TP{r['tp']:02d}", r["titre"], cnt[CONFIRME], cnt[ECART], cnt[INDETERMINE], cnt[INFO]])
    L += ["## Synthèse", "", md_table(["TP", "Sujet", "✅", "❌", "⚠️", "ℹ️"], synth), "",
          f"**Total : {tot[CONFIRME]} confirmés, {tot[ECART]} écarts, {tot[INDETERMINE]} à vérifier, {tot[INFO]} valeurs prédites.**", ""]
    if erreurs:
        L += ["## Erreurs d'exécution", ""] + [f"- TP{n:02d} : voir le journal GitHub Actions" for n, _ in erreurs] + [""]
    for r in tous:
        L += [f"## TP{r['tp']:02d} – {r['titre']}", "",
              f"Vidéo : {r['lien']}  ", f"Méthode : {r['methode']}", ""]
        L.append(md_table(["", "Grandeur", "Vidéo", "Simulation", "Commentaire"],
                          [[ICONE[c["statut"]], c["nom"], c["video"], c["simulation"], c["commentaire"]]
                           for c in r["checks"]]))
        L.append("")
        for titre, ent, lignes in r["tableaux"]:
            L += [f"**{titre}**", "", md_table(ent, lignes), ""]
        if r["hypotheses"]:
            L += ["Hypothèses de la simulation :", ""] + [f"- {h}" for h in r["hypotheses"]] + [""]
        for f in r["figures"]:
            L += [f"![{f['legende']}]({f['fichier']})", f"*{f['legende']}*", ""]
    (res_dir / "RAPPORT.md").write_text("\n".join(L), encoding="utf-8")
    print(f"\nRapport : {res_dir / 'RAPPORT.md'}")
    return 1 if erreurs else 0


if __name__ == "__main__":
    sel = [int(a) for a in sys.argv[1:]] or sorted(MODULES)
    sys.exit(main(sel))
