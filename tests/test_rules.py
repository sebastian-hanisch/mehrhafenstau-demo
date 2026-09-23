"""Platzierungsregeln und Restow-Simulation (mhs_rules.simulate): Handinstanzen aus
seefracht-planung/messreihe_mehrhafenstau/check.py, Erhaltungssatz, Infeasible, record=True."""
import pathlib
import random
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from mhs_rules import Infeasible, simulate  # noqa: E402
from mhs_scenario import make_scenario  # noqa: E402


# ---------------------------------------------------------------------------------------------------
# Handinstanzen aus check.py
# ---------------------------------------------------------------------------------------------------
def test_hand_instance_conflict_free_by_sorting_has_zero_restows():
    """Hafen0 laedt Ziel 4, Hafen1 laedt Ziel 3 (1 Stapel, Hoehe 2): die sortierte Regel stapelt 3 auf
    4 (Sortierung bleibt erhalten), kein Restow noetig."""
    loads = [[4], [3], [], [], []]
    res = simulate(loads, w=1, h=2, rule_name="sortiert")
    assert res["restows"] == 0
    assert res["n_loaded"] == res["n_unloaded"] == 2


def test_hand_instance_infeasible_when_height_cannot_hold_both_containers():
    """1 Stapel, Hoehe 1: kann nur einen Container gleichzeitig halten - 2 gleichzeitig an Bord ist
    unmoeglich, muss Infeasible auesloesen statt eines falschen Restow-Werts."""
    with pytest.raises(Infeasible):
        simulate([[4, 3], [], [], [], []], w=1, h=1, rule_name="sortiert")


def test_hand_instance_two_stacks_enough_capacity_needs_no_restow():
    """2 Stapel, Hoehe 2: Hafen0 laedt Ziel 4 und 5 (je ein Stapel), Hafen1 laedt Ziel 2 und 3 - beide
    valide (Top 4/5 >= 2/3), bestfit waehlt den engsten Top, kein Restow noetig."""
    loads = [[4, 5], [2, 3], [], [], [], []]
    res = simulate(loads, w=2, h=2, rule_name="sortiert")
    assert res["restows"] == 0


# ---------------------------------------------------------------------------------------------------
# Erhaltungssatz: jeder geladene Container wird genau einmal am richtigen Hafen entladen
# ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("seed", range(20))
def test_conservation_law_holds_with_capacity_equal_to_peak(seed):
    """W=peak, H=1: jeder Container bekommt einen eigenen Stapel -> garantiert machbar und 0 Restows;
    prueft, dass alles geladene auch wieder entladen wird (kein Zielhafen-Fehler, siehe assert in
    simulate())."""
    n_ports = random.Random(seed + 900).randint(3, 8)
    vol = random.Random(seed + 901).randint(1, 3)
    loads, peak = make_scenario(n_ports, vol, seed)
    total = sum(len(pl) for pl in loads)
    res = simulate(loads, w=max(peak, 1), h=1, rule_name="sortiert")
    assert res["restows"] == 0
    assert res["n_loaded"] == res["n_unloaded"] == total


@pytest.mark.parametrize("rule", ["sortiert", "blind"])
@pytest.mark.parametrize("seed", range(10))
def test_conservation_law_holds_for_both_rules_at_generous_capacity(seed, rule):
    loads, peak = make_scenario(7, 2, seed)
    total = sum(len(pl) for pl in loads)
    res = simulate(loads, w=peak, h=peak, rule_name=rule)
    assert res["n_loaded"] == res["n_unloaded"] == total


# ---------------------------------------------------------------------------------------------------
# Regeln: Verhalten
# ---------------------------------------------------------------------------------------------------
def test_sorted_rule_never_needs_more_restows_than_blind_on_a_generous_bay():
    """Nicht bewiesen im Allgemeinen, aber an vielen Zufallsinstanzen bei ausreichender Bucht robust:
    die sortierte Regel ist nie schlechter als blind."""
    for seed in range(15):
        loads, peak = make_scenario(8, 2, seed)
        r_sorted = simulate(loads, w=peak, h=4, rule_name="sortiert")
        r_blind = simulate(loads, w=peak, h=4, rule_name="blind")
        assert r_sorted["restows"] <= r_blind["restows"]


def test_infeasible_raised_when_capacity_below_peak_demand():
    loads, peak = make_scenario(8, 3, 0)
    with pytest.raises(Infeasible):
        simulate(loads, w=1, h=1, rule_name="sortiert")


def test_blind_rule_also_raises_infeasible_when_all_stacks_are_completely_full():
    """Wenn keine Regel noch Platz findet, muss auch die blinde Regel Infeasible werfen statt einen
    bereits vollen Stapel weiter zu befuellen (Ueberlauf ueber h hinaus). 1 Stapel, Hoehe 1, aber 2
    Container gleichzeitig noetig (beide Ziel Hafen 1): die zweite Ladung darf keinen Platz mehr
    finden - waere sie erlaubt, wuerde der Stapel unbemerkt auf Hoehe 2 anwachsen."""
    loads = [[1, 1], [], []]
    with pytest.raises(Infeasible):
        simulate(loads, w=1, h=1, rule_name="blind")


def test_load_order_desc_sorts_each_ports_loads_descending():
    """Hafen0 laedt fuer 2 und 5 (unsortierte Ladeliste); load_order='desc' laedt 5 zuerst, dann 2 -
    auf 1 Stapel Hoehe 2 bedeutet das: 5 unten, 2 oben (sortiert, kein Restow noetig)."""
    loads = [[2, 5], [], [], [], [], []]
    res = simulate(loads, w=1, h=2, rule_name="sortiert", load_order="desc")
    assert res["restows"] == 0


# ---------------------------------------------------------------------------------------------------
# record=True: Kernlogik unveraendert, nur zusaetzliche Schnappschuesse
# ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("seed", range(10))
def test_record_true_reports_the_same_restow_count_as_record_false(seed):
    loads, peak = make_scenario(8, 2, seed)
    plain = simulate(loads, w=peak, h=4, rule_name="sortiert", record=False)
    recorded = simulate(loads, w=peak, h=4, rule_name="sortiert", record=True)
    assert plain["restows"] == recorded["restows"]
    assert plain["n_loaded"] == recorded["n_loaded"]
    assert "steps" in recorded and len(recorded["steps"]) == len(loads)


def test_record_steps_track_which_stack_received_each_new_container():
    loads = [[4], [3], [], [], []]
    res = simulate(loads, w=1, h=2, rule_name="sortiert", record=True)
    steps = res["steps"]
    assert steps[0]["loaded"] == ((0, 4),)
    assert steps[1]["loaded"] == ((0, 3),)
    assert steps[0]["stacks"] == ((4,),)
    assert steps[1]["stacks"] == ((4, 3),)
    # Hafen 3 entlaedt Ziel 3 (oben), Hafen 4 entlaedt Ziel 4
    assert steps[3]["unloaded"] == (3,)
    assert steps[4]["unloaded"] == (4,)


def test_record_steps_count_ends_empty_and_no_restows_recorded_when_none_occurred():
    loads = [[4], [3], [], [], []]
    res = simulate(loads, w=1, h=2, rule_name="sortiert", record=True)
    assert res["steps"][-1]["stacks"] == ((),)
    assert all(s["restowed"] == () for s in res["steps"])
