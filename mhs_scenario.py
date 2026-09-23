"""Szenario: Ladeliste je Hafen einer Mehrhafen-Route.

Unveraendert aus seefracht-planung/messreihe_mehrhafenstau/mehrhafenstau.py (make_scenario) uebernommen
- gegen check.py verifiziert (Erhaltungssatz, Monotonie-Hypothese, 60/60 Zufallsinstanzen, 0
Abweichungen). Das Szenario wird UNABHAENGIG von W/H erzeugt, damit derselbe Verkehr gegen
verschiedene Bucht-Groessen simuliert werden kann (fairer Vergleich blind/sortiert/exakt)."""
import random


def make_scenario(n_ports, volume_per_port, seed, max_dest_spread=None):
    """Ladeliste je Hafen p (0..n_ports-2): volume_per_port Container, Ziel gleichverteilt unter den
    erreichbaren spaeteren Haefen (bzw. den naechsten max_dest_spread davon, falls gesetzt - simuliert
    kurzlebigere Fracht). Liefert (loads, peak_occupancy) - peak_occupancy ist die noetige Mindest-
    kapazitaet, unabhaengig von jeder Bucht-Aufteilung."""
    rng = random.Random(seed)
    peak = 0
    loads = [[] for _ in range(n_ports)]
    aboard_list = []  # Multimenge der aktuell an Bord befindlichen Zielhaefen
    for p in range(n_ports - 1):
        aboard_list = [d for d in aboard_list if d != p]
        remaining_route = n_ports - 1 - p
        spread = remaining_route if max_dest_spread is None else min(remaining_route, max_dest_spread)
        for _ in range(volume_per_port):
            d = p + 1 + rng.randrange(spread)
            loads[p].append(d)
            aboard_list.append(d)
        peak = max(peak, len(aboard_list))
    return loads, peak
