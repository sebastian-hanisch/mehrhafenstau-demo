"""Exakter Mindestbedarf und Patience-Sorting-Referenz (mhs_exact): min_piles_patience gegen Brute
Force (wie messreihe_mehrhafenstau/check.py), Monotonie-Hypothese, min_stacks_for_zero_restow."""
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from mhs_exact import flatten_load_order, min_piles_patience, min_stacks_for_zero_restow  # noqa: E402
from mhs_rules import Infeasible, simulate  # noqa: E402
from mhs_scenario import make_scenario  # noqa: E402


def _feasible_with_k(seq, k):
    def rec(i, tops):
        if i == len(seq):
            return True
        v = seq[i]
        for j in range(k):
            if tops[j] is None or tops[j] >= v:
                old = tops[j]
                tops[j] = v
                if rec(i + 1, tops):
                    return True
                tops[j] = old
        return False
    return rec(0, [None] * k)


def _brute_min_piles(seq):
    for k in range(1, len(seq) + 1):
        if _feasible_with_k(seq, k):
            return k
    return len(seq)


def test_min_piles_patience_matches_brute_force_over_300_random_sequences():
    """Wie check.py: 300 Zufallsfolgen, 0 Abweichungen erwartet."""
    rng = random.Random(0)
    bad = 0
    for _ in range(300):
        n = rng.randint(1, 7)
        seq = [rng.randint(0, 5) for _ in range(n)]
        got = min_piles_patience(seq)
        want = _brute_min_piles(seq)
        if got != want:
            bad += 1
    assert bad == 0


def test_min_piles_patience_of_strictly_decreasing_sequence_is_one():
    assert min_piles_patience([5, 4, 3, 2, 1]) == 1


def test_min_piles_patience_of_strictly_increasing_sequence_is_its_length():
    assert min_piles_patience([1, 2, 3, 4]) == 4


def test_min_piles_patience_of_empty_sequence_is_zero():
    assert min_piles_patience([]) == 0


def test_flatten_load_order_sorts_each_port_descending_and_concatenates():
    loads = [[2, 5], [3], []]
    assert flatten_load_order(loads) == [5, 2, 3]


# ---------------------------------------------------------------------------------------------------
# Monotonie-Hypothese: dynamische Simulation braucht nie mehr Stapel als die statische Patience-Grenze
# ---------------------------------------------------------------------------------------------------
def test_dynamic_minimum_never_exceeds_the_static_patience_bound_over_60_random_routes():
    """Wie check.py: 60 Zufallsinstanzen, 0 Verletzungen erwartet."""
    bad = 0
    for seed in range(60):
        n_ports = random.Random(seed + 900).randint(3, 8)
        vol = random.Random(seed + 901).randint(1, 3)
        loads, peak = make_scenario(n_ports, vol, seed)
        static_bound = min_piles_patience(flatten_load_order(loads))
        dyn_w = None
        for w in range(1, static_bound + 1):
            try:
                r = simulate(loads, w=w, h=peak, rule_name="sortiert")
            except Infeasible:
                continue
            if r["restows"] == 0:
                dyn_w = w
                break
        if dyn_w is None:
            bad += 1
    assert bad == 0


# ---------------------------------------------------------------------------------------------------
# min_stacks_for_zero_restow
# ---------------------------------------------------------------------------------------------------
def test_min_stacks_for_zero_restow_matches_direct_search():
    loads, peak = make_scenario(8, 2, 0)
    got = min_stacks_for_zero_restow(loads, h=4, w_max=20)
    assert got == 3          # siehe sweep_data.json (example, seed 0, 8 Haefen, Hoehe 4)
    # direkt nachgerechnet: W=got-1 hat noch Restows (oder ist infeasible), W=got hat 0
    try:
        prev = simulate(loads, got - 1, 4, "sortiert")["restows"]
        assert prev > 0
    except Infeasible:
        pass
    assert simulate(loads, got, 4, "sortiert")["restows"] == 0


def test_min_stacks_for_zero_restow_can_be_exactly_one():
    """Kuerzeste Route (2 Haefen, 1 Container): ein einziger Stapel reicht immer, unabhaengig von der
    Regel - deckt ab, dass die Suche wirklich bei W=1 beginnt (nicht erst bei W=2)."""
    loads, _ = make_scenario(2, 1, 0)
    assert min_stacks_for_zero_restow(loads, h=1, w_max=5) == 1


def test_min_stacks_for_zero_restow_returns_none_when_search_range_too_small():
    loads, peak = make_scenario(10, 4, 0)
    assert min_stacks_for_zero_restow(loads, h=1, w_max=1) is None


def test_min_stacks_for_zero_restow_is_monotonically_non_increasing_in_height():
    """Mehr Hoehe darf den Mindestbedarf nie erhoehen (siehe ERGEBNIS.md: Hoehe hilft, saettigt aber)."""
    loads, peak = make_scenario(8, 2, 3)
    prev = None
    for h in (2, 3, 4, 6, 10):
        w = min_stacks_for_zero_restow(loads, h, w_max=20)
        if prev is not None and w is not None:
            assert w <= prev
        if w is not None:
            prev = w
