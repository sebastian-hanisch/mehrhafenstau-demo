"""Auswertung (mhs_evaluation): Restows-ueber-W-Kurve, Hoehe-Kurve, Stichprobe, gepaartes Urteil,
Diagnose - gegen Direktrechnung und in allen Zustaenden."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import mhs_constants as C  # noqa: E402
import mhs_evaluation as E  # noqa: E402
from mhs_rules import Infeasible, simulate  # noqa: E402
from mhs_scenario import make_scenario  # noqa: E402


def test_restow_curve_matches_direct_simulation():
    loads, _ = make_scenario(8, 2, 0)
    curve = E.restow_curve(loads, h=4, w_max=6)
    for rule in C.RULE_KEYS:
        for w in range(1, 7):
            try:
                want = simulate(loads, w, 4, rule)["restows"]
            except Infeasible:
                want = None
            assert curve[rule][w - 1] == want


def test_restow_curve_reproduces_the_measured_example_from_sweep_data():
    """Seed 0, 8 Haefen, Hoehe 4: aus seefracht-planung/messreihe_mehrhafenstau/sweep_data.json."""
    loads, _ = make_scenario(8, 2, 0)
    curve = E.restow_curve(loads, h=4, w_max=10)
    assert curve["sortiert"] == [None, 3, 0, 0, 0, 0, 0, 0, 0, 0]
    assert curve["blind"] == [None, 3, 4, 2, 2, 0, 0, 0, 0, 0]


def test_static_bound_and_exact_min_match_the_measured_example():
    loads, _ = make_scenario(8, 2, 0)
    assert E.static_bound(loads) == 4
    assert E.exact_min(loads, 4) == 3


def test_height_curve_matches_direct_search_per_height():
    n_ports, volume, seeds = 8, 2, range(5)
    hc = E.height_curve(n_ports, volume, (2, 4, 6), seeds)
    for h in (2, 4, 6):
        needed = []
        for seed in seeds:
            loads, _ = make_scenario(n_ports, volume, seed)
            from mhs_exact import min_stacks_for_zero_restow
            w = min_stacks_for_zero_restow(loads, h, C.W_SEARCH_MAX)
            if w is not None:
                needed.append(w)
        import statistics
        assert hc[h] == statistics.fmean(needed)


def test_height_curve_is_non_increasing_in_height_on_average():
    hc = E.height_curve(8, 2, (2, 3, 4, 6, 10), range(10))
    vals = [hc[h] for h in (2, 3, 4, 6, 10)]
    assert all(vals[i] >= vals[i + 1] - 1e-9 for i in range(len(vals) - 1))


def test_w_upper_bound_is_static_bound_plus_buffer_capped_at_spec_max():
    loads, _ = make_scenario(8, 2, 0)
    assert E.w_upper_bound(loads) == min(C.W_SPEC_MAX, E.static_bound(loads) + C.W_SLIDER_BUFFER)


# ---------------------------------------------------------------------------------------------------
# Stichprobe
# ---------------------------------------------------------------------------------------------------
def test_sample_returns_n_route_results_independent_of_a_shown_seed():
    p = E.Params(n_ports=8, h=4, volume=2, w=5)
    results = E.sample(p, n=10)
    assert len(results) == 10
    assert [r.seed for r in results] == list(range(10))


def test_route_result_restows_match_direct_simulation():
    p = E.Params(n_ports=8, h=4, volume=2, w=5)
    r = E.route_result(p, seed=0)
    loads, _ = make_scenario(8, 2, 0)
    assert r.restows[C.RULE_SORTIERT] == simulate(loads, 5, 4, "sortiert")["restows"]
    assert r.restows[C.RULE_BLIND] == simulate(loads, 5, 4, "blind")["restows"]
    assert r.exact_w == E.exact_min(loads, 4)
    assert r.static_w == E.static_bound(loads)


def test_route_result_records_none_when_infeasible():
    p = E.Params(n_ports=10, h=1, volume=4, w=1)
    r = E.route_result(p, seed=0)
    assert r.restows[C.RULE_SORTIERT] is None or r.restows[C.RULE_SORTIERT] >= 0  # kein Crash


def test_zero_share_and_mean_restows_and_infeasible_count_are_consistent():
    p = E.Params(n_ports=10, h=4, volume=2, w=3)
    results = E.sample(p, n=40)
    z = E.zero_share(results, C.RULE_SORTIERT)
    m = E.mean_restows(results, C.RULE_SORTIERT)
    n_inf = E.infeasible_count(results, C.RULE_SORTIERT)
    feasible = [r for r in results if r.restows[C.RULE_SORTIERT] is not None]
    assert n_inf == len(results) - len(feasible)
    assert z == sum(1 for r in feasible if r.restows[C.RULE_SORTIERT] == 0) / len(feasible)
    import statistics
    assert m == statistics.fmean(r.restows[C.RULE_SORTIERT] for r in feasible)


def test_zero_share_is_none_without_any_feasible_route():
    class Fake:
        def __init__(self):
            self.restows = {C.RULE_SORTIERT: None}
    assert E.zero_share([Fake(), Fake()], C.RULE_SORTIERT) is None


# ---------------------------------------------------------------------------------------------------
# Gepaartes Urteil
# ---------------------------------------------------------------------------------------------------
class _FakeResult:
    def __init__(self, sortiert, blind):
        self.restows = {C.RULE_SORTIERT: sortiert, C.RULE_BLIND: blind}


def test_verdict_better_when_sorted_has_fewer_restows_on_average():
    results = [_FakeResult(0, 5) for _ in range(10)]
    v = E.verdict(results)
    assert v.kind == "better" and v.diff < 0 and v.n == 10


def test_verdict_worse_when_sorted_has_more_restows_on_average():
    results = [_FakeResult(5, 0) for _ in range(10)]
    v = E.verdict(results)
    assert v.kind == "worse" and v.diff > 0


def test_verdict_unclear_with_noisy_small_difference():
    results = [_FakeResult(2, 2), _FakeResult(3, 1), _FakeResult(1, 3), _FakeResult(2, 2)]
    v = E.verdict(results)
    assert v.kind == "unclear"


def test_verdict_ignores_routes_infeasible_for_either_rule():
    results = [_FakeResult(0, 5), _FakeResult(None, 5), _FakeResult(0, None)]
    v = E.verdict(results)
    assert v.n == 1


def test_verdict_unclear_with_no_comparable_routes():
    v = E.verdict([_FakeResult(None, 5)])
    assert v.kind == "unclear" and v.n == 0


def test_verdict_standard_error_uses_sqrt_n_not_n():
    """d = [1, 3]: stdev = sqrt(2), se = stdev / sqrt(2) = 1.0 exakt - eine Verwechslung mit
    stdev/len(d) (0,707...) waere hier klar unterscheidbar."""
    results = [_FakeResult(5, 4), _FakeResult(7, 4)]   # Differenzen sortiert-blind: 1 und 3
    v = E.verdict(results)
    assert v.diff == pytest.approx(2.0) and v.se == pytest.approx(1.0)


def test_verdict_is_unclear_exactly_at_the_two_standard_error_boundary():
    """Mit denselben Daten wie oben: |diff|=2.0, Z*se=2*1.0=2.0 - GENAU auf der Schwelle gilt noch als
    unclear (<=, nicht <)."""
    results = [_FakeResult(5, 4), _FakeResult(7, 4)]
    v = E.verdict(results)
    assert v.kind == "unclear"


# ---------------------------------------------------------------------------------------------------
# Diagnose
# ---------------------------------------------------------------------------------------------------
def test_diagnose_infeasible_when_restows_sortiert_is_none():
    d = E.diagnose(w=1, exact_w=3, restows_sortiert=None)
    assert d.kind == "infeasible"


def test_diagnose_too_narrow_when_w_below_exact_minimum():
    d = E.diagnose(w=2, exact_w=3, restows_sortiert=1)
    assert d.kind == "too_narrow" and d.gap == -1


def test_diagnose_at_limit_when_w_equals_exact_minimum():
    d = E.diagnose(w=3, exact_w=3, restows_sortiert=0)
    assert d.kind == "at_limit" and d.gap == 0


def test_diagnose_comfortable_when_w_above_exact_minimum():
    d = E.diagnose(w=5, exact_w=3, restows_sortiert=0)
    assert d.kind == "comfortable" and d.gap == 2


def test_diagnose_unknown_when_exact_w_is_none_but_route_is_feasible():
    d = E.diagnose(w=5, exact_w=None, restows_sortiert=2)
    assert d.kind == "unknown"
