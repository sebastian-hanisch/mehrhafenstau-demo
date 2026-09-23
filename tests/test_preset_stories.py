"""Abnahme der Presets an ECHTEN Daten: jede Geschichte traegt im Mittel ueber POPULATION_INSTANCES
Routen (`mhs_stories.criteria`, reproduziert seefracht-planung/messreihe_mehrhafenstau/sweep_data.json)
UND an der einen Route, die das Preset zeigt (`mhs_stories.shown_criteria`)."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import mhs_constants as C  # noqa: E402
import mhs_evaluation as E  # noqa: E402
import mhs_stories as ST  # noqa: E402

NAMES = list(C.PRESETS)
_POP = {}


def params(name):
    p = C.PRESETS[name]
    return E.Params(p["n_ports"], p["h"], p["volume"], p["w"])


def population(name):
    if name not in _POP:
        _POP[name] = E.sample(params(name), C.POPULATION_INSTANCES)
    return _POP[name]


@pytest.mark.parametrize("name", NAMES)
def test_story_holds_on_average_over_the_population(name):
    for ok, text in ST.criteria(name, population(name)):
        assert ok, f"{name}: {text}"


@pytest.mark.parametrize("name", NAMES)
def test_story_holds_at_the_route_the_preset_shows(name):
    seed = C.PRESETS[name]["seed"]
    shown = E.route_result(params(name), seed)
    for ok, text in ST.shown_criteria(name, shown):
        assert ok, f"{name}: {text}"


def test_the_preset_seed_lies_outside_the_population():
    assert all(preset["seed"] >= C.POPULATION_INSTANCES for preset in C.PRESETS.values())


def test_criteria_are_not_trivially_true_for_the_wrong_preset():
    """Die Geschichten unterscheiden sich: an den Daten eines anderen Presets kippt mindestens ein
    Kriterium (sonst waeren die Presets austauschbar)."""
    assert not all(ok for ok, _ in ST.criteria("Komfortable Bucht", population("Sehr knappe Bucht")))
    assert not all(ok for ok, _ in ST.criteria("Sehr knappe Bucht", population("Komfortable Bucht")))
    assert not all(ok for ok, _ in ST.criteria("Knappe Bucht", population("Komfortable Bucht")))


def test_the_population_reproduces_the_pre_measurement_sweep_data_exactly():
    """Unser Port von mhs_scenario/mhs_rules/mhs_exact ist unveraendert gegenueber
    messreihe_mehrhafenstau/mehrhafenstau.py - bei GLEICHER Stichprobengroesse (range(40)) muessen die
    Nullquoten exakt (nicht nur auf Marge) mit sweep_data.json uebereinstimmen."""
    expected = {
        "Komfortable Bucht": dict(sortiert=1.0, blind=0.975),
        "Knappe Bucht": dict(sortiert=0.95, blind=0.025),
        "Sehr knappe Bucht": dict(sortiert=0.625, blind=0.0),
        "Kurze Route, knapp": dict(sortiert=0.825, blind=0.125),
    }
    for name, exp in expected.items():
        preset = C.PRESETS[name]
        p = E.Params(preset["n_ports"], preset["h"], preset["volume"], preset["w"])
        pop = E.sample(p, C.POPULATION_INSTANCES)
        assert E.zero_share(pop, C.RULE_SORTIERT) == pytest.approx(exp["sortiert"], abs=1e-9)
        assert E.zero_share(pop, C.RULE_BLIND) == pytest.approx(exp["blind"], abs=1e-9)


def test_niedrige_bucht_reproduces_the_pre_measurement_sweep_data_exactly():
    preset = C.PRESETS["Niedrige Bucht"]
    p = E.Params(preset["n_ports"], preset["h"], preset["volume"], preset["w"])
    pop = E.sample(p, C.POPULATION_INSTANCES)
    assert E.zero_share(pop, C.RULE_SORTIERT) == pytest.approx(0.9459459459459459, abs=1e-9)
    assert E.infeasible_count(pop, C.RULE_SORTIERT) == 3
