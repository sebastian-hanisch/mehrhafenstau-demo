"""Exakter Mindestbedarf und Patience-Sorting-Referenz.

Unveraendert aus seefracht-planung/messreihe_mehrhafenstau/mehrhafenstau.py uebernommen
(min_piles_patience, flatten_load_order, min_stacks_for_zero_restow) - min_piles_patience gegen Brute
Force verifiziert (check.py, 300 Zufallsfolgen, 0 Abweichungen), min_stacks_for_zero_restow <=
min_piles_patience als Monotonie-Hypothese ueber 60 Zufallsinstanzen bestaetigt (0 Verletzungen)."""
import bisect

from mhs_rules import Infeasible, simulate


def min_piles_patience(seq):
    """Minimale Zahl Stapel (unbegrenzte Hoehe), um seq (Zielhaefen in EINER Beladereihenfolge, OHNE
    Zwischenentladen) restow-frei zu stapeln = Laenge der laengsten streng steigenden Teilfolge von seq
    (klassisches Patience-Sorting-Resultat). Nur als STATISCHE Referenz - ignoriert, dass echtes
    Entladen zwischendurch Platz freigibt; sicher, aber sehr locker (siehe ERGEBNIS.md: im Mittel nur
    60-64 % davon werden dynamisch tatsaechlich gebraucht)."""
    tops = []
    for v in seq:
        idx = bisect.bisect_left(tops, v)
        if idx < len(tops):
            tops[idx] = v
        else:
            tops.append(v)
    return len(tops)


def flatten_load_order(loads):
    """Alle Ladeereignisse in der tatsaechlichen Reihenfolge (Hafen fuer Hafen, je Hafen absteigend
    nach Ziel wie in simulate()) - Eingabe fuer min_piles_patience()."""
    seq = []
    for port_loads in loads:
        seq.extend(sorted(port_loads, reverse=True))
    return seq


def min_stacks_for_zero_restow(loads, h, w_max, rule_name="sortiert"):
    """Kleinstes W (bei fester Hoehe h), fuer das die DYNAMISCHE Simulation (mit echtem Zwischen-
    entladen) 0 Restows erreicht. Lineares Hochzaehlen (w_max ist klein genug fuer die Demo-Groessen,
    gemessen deutlich unter 50 ms auch bei der groessten Route - siehe ERGEBNIS.md); w_max bleibt ein
    hartes Sicherheitsnetz im Code, kein Zeitlimit."""
    for w in range(1, w_max + 1):
        try:
            res = simulate(loads, w, h, rule_name)
        except Infeasible:
            continue
        if res["restows"] == 0:
            return w
    return None
