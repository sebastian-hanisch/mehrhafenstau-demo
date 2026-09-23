"""Figuren (mhs_visualization): Achsen fest (fixedrange), Restow-Kurve, Hoehe-Kurve, Bucht-Ansicht mit
Zeitschritt-Zustand."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import mhs_constants as C  # noqa: E402
import mhs_visualization as V  # noqa: E402
from mhs_rules import simulate  # noqa: E402
from mhs_scenario import make_scenario  # noqa: E402


def _assert_locked(fig):
    for ax in list(fig.layout.xaxis) + list(fig.layout.yaxis):
        pass
    assert fig.layout.xaxis.fixedrange is True
    assert fig.layout.yaxis.fixedrange is True


def test_restow_curve_figure_is_locked_and_has_a_trace_per_rule():
    loads, _ = make_scenario(8, 2, 0)
    from mhs_evaluation import restow_curve
    curve = restow_curve(loads, 4, 6)
    fig = V.restow_curve_figure(curve, static_bound_value=4, dyn_min=3, current_w=5)
    _assert_locked(fig)
    names = [t.name for t in fig.data if t.name]
    assert C.RULE_LABELS[C.RULE_SORTIERT] in names and C.RULE_LABELS[C.RULE_BLIND] in names


def test_restow_curve_figure_handles_missing_dyn_min_and_static_bound():
    curve = {C.RULE_SORTIERT: [None, None], C.RULE_BLIND: [None, None]}
    fig = V.restow_curve_figure(curve, static_bound_value=None, dyn_min=None, current_w=1)
    _assert_locked(fig)


def test_height_curve_figure_is_locked_and_marks_the_current_height():
    hc = {2: 4.0, 4: 3.0, 6: 2.9}
    fig = V.height_curve_figure(hc, current_h=4)
    _assert_locked(fig)
    assert len(fig.data) == 2  # Linie + Marker fuer die eingestellte Hoehe


def test_height_curve_figure_without_matching_current_height_still_renders():
    hc = {2: 4.0, 4: 3.0}
    fig = V.height_curve_figure(hc, current_h=5)
    _assert_locked(fig)
    assert len(fig.data) == 1


# ---------------------------------------------------------------------------------------------------
# Bucht-Ansicht
# ---------------------------------------------------------------------------------------------------
def test_state_at_index_zero_is_empty_bay_with_w_stacks():
    loads = [[4], [3], [], [], []]
    res = simulate(loads, w=1, h=2, rule_name="sortiert", record=True)
    port, stacks, restowed, loaded = V.state_at(res["steps"], w=1, index=0)
    assert port is None and stacks == ((),) and restowed == () and loaded == ()


def test_state_at_advances_through_the_recorded_steps():
    loads = [[4], [3], [], [], []]
    res = simulate(loads, w=1, h=2, rule_name="sortiert", record=True)
    port, stacks, restowed, loaded = V.state_at(res["steps"], w=1, index=2)
    assert port == 1 and stacks == ((4, 3),) and loaded == ((0, 3),)


def test_cumulative_restows_counts_up_to_the_given_index():
    loads, _ = make_scenario(10, 2, 41)   # Knappe-Bucht-Preset-Route: hat echte Restows
    res = simulate(loads, w=4, h=4, rule_name="blind", record=True)
    total = sum(len(s["restowed"]) for s in res["steps"])
    assert V.cumulative_restows(res["steps"], len(res["steps"])) == total
    assert V.cumulative_restows(res["steps"], 0) == 0


def test_bay_figure_is_locked_and_has_one_text_entry_per_container():
    stacks = ((4, 3), (5,))
    fig = V.bay_figure(stacks, h=3, n_ports=8, title="Test")
    _assert_locked(fig)
    assert len(fig.data[0].x) == 3   # 3 Container insgesamt


def test_bay_figure_highlights_restowed_and_loaded_cells():
    stacks = ((4, 3),)
    fig = V.bay_figure(stacks, h=3, n_ports=8, title="Test", restowed_positions=((0, 3),), loaded_positions=((0, 4),))
    # Zwei Rechtecke mit farbigem Rand (eines je Container) zusaetzlich zu den w Stapel-Hintergruenden
    colored_borders = [s for s in fig.layout.shapes if s.line.width == 3]
    assert len(colored_borders) == 2


def test_bay_title_distinguishes_before_start_from_after_a_port():
    assert "Vor Hafen 1" in V.bay_title("Regel", None, 8, 0)
    assert "Nach Hafen 3 von 8" in V.bay_title("Regel", 2, 8, 5)
