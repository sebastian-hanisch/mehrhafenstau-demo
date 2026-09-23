"""Preset-Abstimmung: traegt die Geschichte jedes Presets im MITTEL ueber viele Routen, und an der
einen Route, die das Preset zeigt?

Aufruf (im Projektordner): ./venv/Scripts/python.exe tools/tune_presets.py <modus>
  population   Grundgesamtheit (Seeds 0..POPULATION-1): Nullquote-Kriterien aller Presets
  seeds        je Seed ab POPULATION: welche Presets tragen an diesem Seed, wie nah am Median

Grundsatz (aus den Hafen-Demos): den Seed nicht nach dem schoensten Einzelfall waehlen, sondern
typisch (10.-90. Perzentil der Restows der sortierten Regel in der Population); der Preset-Seed liegt
AUSSERHALB der Grundgesamtheit (Seeds ab POPULATION). Alles ist deterministisch (kein Loeser mit
Zeitgrenze): die Ergebnisse haengen nicht vom Rechner ab."""
import sys

sys.path.insert(0, ".")
import mhs_constants as C
import mhs_evaluation as E
import mhs_stories as ST
from mhs_presets import w_bounds

NAMES = list(C.PRESETS)
POPULATION = C.POPULATION_INSTANCES
SEED_SEARCH = range(POPULATION, POPULATION + 800)


def params(name):
    p = C.PRESETS[name]
    return E.Params(p["n_ports"], p["h"], p["volume"], p["w"])


def cmd_population():
    for name in NAMES:
        res = E.sample(params(name), POPULATION)
        print(f"\n### {name}")
        for ok, text in ST.criteria(name, res):
            print(("  OK   " if ok else "  FAIL ") + text)
        z_s = E.zero_share(res, C.RULE_SORTIERT)
        z_b = E.zero_share(res, C.RULE_BLIND)
        print(f"  Nullquote sortiert={z_s}, blind={z_b}, infeasible(sortiert)={E.infeasible_count(res, C.RULE_SORTIERT)}/{len(res)}")


def cmd_seeds():
    """Sucht je Preset einen Seed, der shown_criteria() erfuellt - unter den Treffern wird NICHT der
    dramatischste Kontrast gewaehlt (das waere Cherry-Picking des schoensten Einzelfalls), sondern der
    mit Restows(sortiert)/Restows(blind) am naechsten am Populations-Mittel (mean_restows)."""
    for name in NAMES:
        p = params(name)
        pop = E.sample(p, POPULATION)
        mean_s = E.mean_restows(pop, C.RULE_SORTIERT) or 0.0
        mean_b = E.mean_restows(pop, C.RULE_BLIND) or 0.0
        best = None
        holds_count = 0
        for seed in SEED_SEARCH:
            lo, hi = w_bounds(p.n_ports, p.h, p.volume, seed)
            if not (lo <= p.w <= hi):
                continue    # der Regler wuerde W bei diesem Seed enger begrenzen als das Preset braucht
            r = E.route_result(p, seed)
            if not all(ok for ok, _ in ST.shown_criteria(name, r)):
                continue
            holds_count += 1
            rs, rb = r.restows[C.RULE_SORTIERT], r.restows[C.RULE_BLIND]
            score = abs((rs or 0) - mean_s) + abs((rb or 0) - mean_b)
            if best is None or score < best[0]:
                best = (score, seed, r)
        print(f"\n### {name}: traegt an {holds_count} von {len(SEED_SEARCH)} Seeds (Suchbereich {SEED_SEARCH.start}..{SEED_SEARCH.stop - 1}); Populationsmittel sortiert={mean_s:.2f}, blind={mean_b:.2f}")
        if best:
            score, seed, r = best
            print(f"  bester Seed (naechster am Populationsmittel): {seed}  Restows(sortiert)={r.restows[C.RULE_SORTIERT]}  Restows(blind)={r.restows[C.RULE_BLIND]}")
        else:
            print("  KEIN Seed im Suchbereich erfuellt shown_criteria() - Kriterien oder Suchbereich pruefen.")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "population"
    {"population": cmd_population, "seeds": cmd_seeds}.get(mode, lambda: sys.exit(__doc__))()
