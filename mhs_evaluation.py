"""Auswertung: Stichprobe von Routen, Restows-ueber-W-Kurve, Hoehe-Kurve, gepaartes Urteil (sortiert
gegen blind), Diagnose (bedingte Meldung). Reine Rechnung ohne Streamlit.

"Restows" ist die Kennzahl dieser Demo (kein Kosten-Analog); alle Vergleiche sind gepaart (dieselbe
Route/derselbe Seed fuer beide Regeln)."""
import math
import statistics
from dataclasses import dataclass
from typing import NamedTuple, Optional

import mhs_constants as C
from mhs_exact import flatten_load_order, min_piles_patience, min_stacks_for_zero_restow
from mhs_rules import Infeasible, simulate
from mhs_scenario import make_scenario


class Params(NamedTuple):
    """Alle Einstellungen, die eine Route und ihre Auswertung bestimmen (ohne Seed)."""
    n_ports: int
    h: int
    volume: int
    w: int


def route(p, seed):
    """(loads, peak) fuer diese Einstellung (unabhaengig von W)."""
    return make_scenario(p.n_ports, p.volume, seed)


def static_bound(loads):
    """Patience-Sorting-Grenze (sichere, aber lockere obere Schranke) dieser Route."""
    return min_piles_patience(flatten_load_order(loads))


def exact_min(loads, h, w_max=C.W_SEARCH_MAX):
    """Exakter dynamischer Mindestbedarf (kleinstes W mit 0 Restows, Regel sortiert) dieser Route."""
    return min_stacks_for_zero_restow(loads, h, w_max)


def w_upper_bound(loads):
    """Obergrenze fuer den W-Regler: Patience-Grenze der Route plus Puffer (Faustregel-Naehe, Plan
    Abschnitt 5), begrenzt auf die Spezifikationsobergrenze."""
    return min(C.W_SPEC_MAX, static_bound(loads) + C.W_SLIDER_BUFFER)


# ---------------------------------------------------------------------------------------------------
# Restows-ueber-W-Kurve (eine Route, beide Regeln) und Hoehe-Kurve
# ---------------------------------------------------------------------------------------------------
def restow_curve(loads, h, w_max):
    """{'blind': [...], 'sortiert': [...]}: Restows je W = 1..w_max (None, wo infeasible)."""
    out = {}
    for rule in C.RULE_KEYS:
        vals = []
        for w in range(1, w_max + 1):
            try:
                res = simulate(loads, w, h, rule)
                vals.append(res["restows"])
            except Infeasible:
                vals.append(None)
        out[rule] = vals
    return out


def height_curve(n_ports, volume, h_values, seeds, w_max=C.W_SEARCH_MAX):
    """Mittlere exakte Mindest-Stapelzahl (Regel sortiert) je Hoehe H, gemittelt ueber `seeds`."""
    out = {}
    for h in h_values:
        needed = []
        for seed in seeds:
            loads, _ = make_scenario(n_ports, volume, seed)
            w = min_stacks_for_zero_restow(loads, h, w_max)
            if w is not None:
                needed.append(w)
        out[h] = statistics.fmean(needed) if needed else None
    return out


# ---------------------------------------------------------------------------------------------------
# Stichprobe ueber viele Routen (feste Einstellung n_ports/h/volume/w)
# ---------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class RouteResult:
    seed: int
    restows: dict           # rule -> int oder None (infeasible bei diesem W)
    exact_w: Optional[int]   # exakter Mindestbedarf dieser Route bei dieser Hoehe (unabhaengig von W)
    static_w: int            # Patience-Grenze dieser Route


def route_result(p, seed):
    loads, _ = route(p, seed)
    restows = {}
    for rule in C.RULE_KEYS:
        try:
            res = simulate(loads, p.w, p.h, rule)
            restows[rule] = res["restows"]
        except Infeasible:
            restows[rule] = None
    return RouteResult(seed, restows, exact_min(loads, p.h), static_bound(loads))


def sample(p, n=C.SAMPLE_INSTANCES, start=0):
    """n Routen (Seeds start..start+n-1, unabhaengig vom eingestellten Seed) mit den Einstellungen p."""
    return tuple(route_result(p, seed) for seed in range(start, start + n))


def zero_share(results, rule):
    """Anteil restow-freier Routen unter den FEASIBLE Routen dieser Regel; None ohne feasible Routen."""
    vals = [r.restows[rule] for r in results if r.restows[rule] is not None]
    if not vals:
        return None
    return sum(1 for v in vals if v == 0) / len(vals)


def mean_restows(results, rule):
    vals = [r.restows[rule] for r in results if r.restows[rule] is not None]
    if not vals:
        return None
    return statistics.fmean(vals)


def infeasible_count(results, rule):
    return sum(1 for r in results if r.restows[rule] is None)


# ---------------------------------------------------------------------------------------------------
# Gepaartes Urteil: sortiert gegen blind (dieselbe Route je Seed)
# ---------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Verdict:
    kind: str       # "better" (sortiert hat weniger Restows) | "worse" | "unclear"
    diff: float      # sortiert minus blind je Route (negativ = sortiert besser)
    se: float
    n: int


def _se(d):
    return statistics.stdev(d) / math.sqrt(len(d)) if len(d) > 1 else 0.0


def verdict(results):
    """Gepaarte Differenz sortiert - blind je Route (nur Routen, an denen BEIDE Regeln feasible sind).
    'Klar' heisst: |Differenz| > VERDICT_Z Standardfehler der gepaarten Differenz je Route."""
    d = [r.restows[C.RULE_SORTIERT] - r.restows[C.RULE_BLIND] for r in results
         if r.restows[C.RULE_SORTIERT] is not None and r.restows[C.RULE_BLIND] is not None]
    if not d:
        return Verdict("unclear", 0.0, 0.0, 0)
    diff, se = statistics.fmean(d), _se(d)
    if se == 0:
        kind = "unclear" if diff == 0 else ("better" if diff < 0 else "worse")
    else:
        kind = "unclear" if abs(diff) <= C.VERDICT_Z * se else ("better" if diff < 0 else "worse")
    return Verdict(kind, diff, se, len(d))


# ---------------------------------------------------------------------------------------------------
# Diagnose (bedingte Meldung, Plan Abschnitt 6)
# ---------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Diagnosis:
    kind: str            # "infeasible" | "too_narrow" | "at_limit" | "comfortable"
    gap: Optional[int]    # eingestelltes W minus exaktes Minimum (negativ = zu knapp)
    exact_w: Optional[int]


def diagnose(w, exact_w, restows_sortiert):
    """restows_sortiert: Restows der sortierten Regel bei (w, h) auf der gezeigten Route, None wenn
    diese Bucht-Groesse dort infeasible ist (Kapazitaet reicht nicht, unabhaengig von der Regel)."""
    if restows_sortiert is None:
        return Diagnosis("infeasible", None, exact_w)
    if exact_w is None:
        return Diagnosis("unknown", None, None)
    gap = w - exact_w
    kind = "too_narrow" if gap < 0 else ("at_limit" if gap == 0 else "comfortable")
    return Diagnosis(kind, gap, exact_w)
