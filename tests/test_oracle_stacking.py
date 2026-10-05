"""Orakel-Tests: Vollaufzählung aller Platzierungen gegen den Mindestbedarf W* der sortierten Regel.

* W* (kleinstes W, bei dem die sortierte Regel 0 Restows erreicht) ist eine OBERE Schranke für das echte
  Minimum über alle Stapelverfahren, nicht dessen Wert: die Beispielroute unten braucht mit der Regel W=3,
  per Hand/Vollaufzählung genügen 2 Stapel.
* 0 Restows <=> jeder Stapel ist nach dem Laden von unten nach oben nicht aufsteigend (jede Inversion
  blockiert beim Entladen irgendwann einen Container): unabhängiges Kriterium gegen die Simulation.
* Patience-Grenze = längste streng steigende Teilfolge (O(n^2)-Dynamikprogramm).
"""
import random
from functools import lru_cache

import mhs_exact
from mhs_rules import Infeasible, simulate
from mhs_scenario import make_scenario

HAND_ROUTE = [[2, 4], [3, 2], [5, 3], [4, 5], [5, 5], []]


def _feasible_without_restow(loads, w, h):
    n = len(loads)

    @lru_cache(None)
    def go(p, state):
        if p == n:
            return True
        stacks = []
        for s in state:
            s = list(s)
            while s and s[-1] == p:
                s.pop()
            if p in s:
                return False
            stacks.append(tuple(s))
        dests = sorted(loads[p], reverse=True)

        def place(i, cur):
            if i == len(dests):
                return go(p + 1, tuple(sorted(cur)))
            d, seen = dests[i], set()
            for j, s in enumerate(cur):
                if s in seen or len(s) >= h or (s and s[-1] < d):
                    seen.add(s)
                    continue
                seen.add(s)
                nxt = list(cur)
                nxt[j] = s + (d,)
                if place(i + 1, nxt):
                    return True
            return False

        return place(0, stacks)

    return go(0, tuple(() for _ in range(w)))


def _true_min(loads, h, w_max=12):
    return next((w for w in range(1, w_max + 1) if _feasible_without_restow(loads, w, h)), None)


def test_rule_minimum_is_an_upper_bound_of_the_true_minimum_and_can_be_strictly_larger():
    assert mhs_exact.min_stacks_for_zero_restow(HAND_ROUTE, 4, 30) == 3
    assert _true_min(HAND_ROUTE, 4) == 2
    rng = random.Random(3)
    for _ in range(60):
        loads, _ = make_scenario(rng.randint(4, 7), rng.randint(1, 3), rng.randint(0, 9999))
        h = rng.randint(2, 5)
        assert _true_min(loads, h) <= mhs_exact.min_stacks_for_zero_restow(loads, h, 30)


def test_zero_restows_iff_every_stack_is_sorted_after_each_loading_step():
    rng = random.Random(8)
    for _ in range(60):
        loads, _ = make_scenario(rng.randint(4, 8), rng.randint(1, 3), rng.randint(0, 9999))
        h = rng.randint(2, 5)
        for w in range(1, 7):
            for rule in ("sortiert", "blind"):
                try:
                    res = simulate(loads, w, h, rule, record=True)
                except Infeasible:
                    continue
                ordered = all(s[i] >= s[i + 1] for st in res["steps"] for s in st["stacks"] for i in range(len(s) - 1))
                assert (res["restows"] == 0) == ordered
                assert res["n_loaded"] == res["n_unloaded"] == sum(len(x) for x in loads)


def test_patience_bound_equals_longest_strictly_increasing_subsequence():
    rng = random.Random(1)
    for _ in range(100):
        loads, _ = make_scenario(rng.randint(3, 10), rng.randint(1, 4), rng.randint(0, 9999))
        seq = mhs_exact.flatten_load_order(loads)
        best = []
        for i, v in enumerate(seq):
            best.append(1 + max((best[j] for j in range(i) if seq[j] < v), default=0))
        assert mhs_exact.min_piles_patience(seq) == max(best, default=0)
