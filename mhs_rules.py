"""Platzierungsregeln und Restow-Simulation der Mehrhafen-Stauplanung.

Kernlogik (Infeasible, _choose_sorted, _choose_blind, simulate) unveraendert aus
seefracht-planung/messreihe_mehrhafenstau/mehrhafenstau.py uebernommen - gegen Brute Force und
Handinstanzen verifiziert (check.py, 0 Abweichungen). `simulate()` bekommt zusaetzlich einen
`record=True`-Zweig fuer die Route-Ansicht (Bucht-Zustand je Hafen-Schritt), nach demselben Muster
wie lcr_rolling.py in leercontainer-demo (record=True erweitert, Kernlogik unangetastet - die
Verzweigungen/Reihenfolge der Operationen sind identisch zum Original)."""

INF = float("inf")


class Infeasible(Exception):
    """Bucht zu klein fuer den Verkehr (Kapazitaet reicht nicht, unabhaengig von der Regel)."""


def _choose_sorted(stacks, dest, h):
    """Zielhafen-sortierte Regel: bevorzugt eine Position, die die Stapel-Sortierung (oben = naechstes
    Ziel) erhaelt; bestfit = knappster passender Stapel. Kein passender Stapel -> kleinste Verletzung
    (Top-Ziel am naechsten unter dem neuen Ziel)."""
    valid = []
    forced = []
    for i, s in enumerate(stacks):
        if len(s) >= h:
            continue
        if not s or s[-1] >= dest:
            valid.append((s[-1] if s else INF, i))
        else:
            forced.append((dest - s[-1], i))
    if valid:
        valid.sort()
        return valid[0][1]
    if forced:
        forced.sort()
        return forced[0][1]
    return None


def _choose_blind(stacks, dest, h):
    """Blinde Regel: ignoriert Zielhaefen, waehlt den Stapel mit dem meisten freien Platz (Lastausgleich)."""
    room = [(h - len(s), i) for i, s in enumerate(stacks) if len(s) < h]
    if not room:
        return None
    room.sort(reverse=True)
    return room[0][1]


RULES = {"sortiert": _choose_sorted, "blind": _choose_blind}


def simulate(loads, w, h, rule_name, load_order="desc", record=False):
    """Fuehrt die ganze Route gegen eine feste Ladeliste; gibt Kennzahlen zurueck. Wirft Infeasible,
    wenn die Bucht (w*h) an irgendeinem Punkt nicht reicht - unabhaengig von der Regel.

    Bei record=True enthaelt das Ergebnis zusaetzlich "steps": je Hafen ein Zustands-Schnappschuss
    (stacks nach dem Bearbeiten dieses Hafens; "restowed"/"loaded" als (Stapelindex, Zielhafen)-Paare,
    damit die Route-Ansicht genau weiss, welche Zelle neu hinzugekommen ist) - fuer die Route-Ansicht
    mit Zeitschrittregler."""
    choose = RULES[rule_name]
    n_ports = len(loads)
    stacks = [[] for _ in range(w)]
    restow_events = 0
    n_loaded = n_unloaded = 0
    steps = [] if record else None
    for p in range(n_ports):
        restowed_here = []
        unloaded_here = []
        for s in stacks:
            if p not in s:
                continue
            setaside = []
            while s and p in s:
                top = s[-1]
                if top == p:
                    s.pop()
                    n_unloaded += 1
                    unloaded_here.append(p)
                else:
                    setaside.append(s.pop())
                    restow_events += 1
            for c in setaside:
                j = choose(stacks, c, h)
                if j is None:
                    raise Infeasible(f"kein Platz bei Wiedereinlagerung, Hafen {p}")
                stacks[j].append(c)
                restowed_here.append((j, c))
        dests = sorted(loads[p], reverse=(load_order == "desc"))
        loaded_here = []
        for d in dests:
            j = choose(stacks, d, h)
            if j is None:
                raise Infeasible(f"kein Platz beim Laden, Hafen {p}")
            stacks[j].append(d)
            n_loaded += 1
            loaded_here.append((j, d))
        if record:
            steps.append(dict(port=p, stacks=tuple(tuple(s) for s in stacks), restowed=tuple(restowed_here),
                              unloaded=tuple(unloaded_here), loaded=tuple(loaded_here)))
    assert all(len(s) == 0 for s in stacks), "Container am Ende noch an Bord - Zielhafen-Fehler"
    result = dict(restows=restow_events, n_loaded=n_loaded, n_unloaded=n_unloaded)
    if record:
        result["steps"] = steps
    return result
