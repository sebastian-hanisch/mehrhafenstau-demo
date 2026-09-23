"""Regler-Spezifikation, Permalink, Presets, Seed-Knopf (mhs_presets) - reine Logik ohne AppTest."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import mhs_constants as C  # noqa: E402
from mhs_presets import (bounds, clamp_w, default_w, parse_setting, SETTING_SPECS, w_bounds)  # noqa: E402


def test_bounds_reads_spec_range():
    assert bounds("n_ports_slider") == C.N_PORTS_RANGE
    assert bounds("h_slider") == C.H_RANGE
    assert bounds("volume_slider") == C.VOLUME_RANGE


def test_w_bounds_matches_the_measured_example():
    lo, hi = w_bounds(8, 4, 2, 0)
    assert lo == C.W_MIN
    assert hi == 4 + C.W_SLIDER_BUFFER          # static_bound=4 fuer diese Route (siehe sweep_data.json)


def test_w_bounds_changes_with_route_settings():
    lo1, hi1 = w_bounds(6, 4, 2, 0)
    lo2, hi2 = w_bounds(10, 2, 2, 0)
    assert (lo1, hi1) != (lo2, hi2)


def test_clamp_w_limits_instead_of_rejecting():
    lo, hi = w_bounds(8, 4, 2, 0)
    assert clamp_w(8, 4, 2, 0, hi + 10) == hi
    assert clamp_w(8, 4, 2, 0, lo - 10) == lo
    assert clamp_w(8, 4, 2, 0, lo + 1) == lo + 1


def test_default_w_is_within_bounds_and_leaves_headroom():
    lo, hi = w_bounds(C.N_PORTS_DEFAULT, C.H_DEFAULT, C.VOLUME_DEFAULT, C.SEED_DEFAULT)
    d = default_w()
    assert lo <= d <= hi
    if hi > lo:
        assert d < hi, "Default soll nicht am oberen Reglerrand liegen (das ist die komfortabelste, nicht die typische Einstellung)"
        assert d == hi - 1


# ---------------------------------------------------------------------------------------------------
# Permalink-Parsing
# ---------------------------------------------------------------------------------------------------
def test_parse_setting_clamps_to_spec_range():
    spec = SETTING_SPECS["n_ports_slider"]
    assert parse_setting(spec, "99") == C.N_PORTS_RANGE[1]
    assert parse_setting(spec, "0") == C.N_PORTS_RANGE[0]


def test_parse_setting_ignores_garbage():
    spec = SETTING_SPECS["seed_input"]
    assert parse_setting(spec, "not-a-number") is None


def test_parse_setting_rejects_non_finite_floats():
    spec = SETTING_SPECS["h_slider"]
    assert parse_setting(spec, "nan") is None


# ---------------------------------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------------------------------
def test_every_preset_has_all_five_fields_within_spec_bounds():
    for name, preset in C.PRESETS.items():
        assert set(preset) == {"n_ports", "w", "h", "volume", "seed"}
        assert C.N_PORTS_RANGE[0] <= preset["n_ports"] <= C.N_PORTS_RANGE[1]
        assert C.H_RANGE[0] <= preset["h"] <= C.H_RANGE[1]
        assert C.VOLUME_RANGE[0] <= preset["volume"] <= C.VOLUME_RANGE[1]
        assert C.SEED_RANGE[0] <= preset["seed"] <= C.SEED_RANGE[1]


def test_every_preset_w_is_within_its_own_computed_bounds():
    for name, preset in C.PRESETS.items():
        lo, hi = w_bounds(preset["n_ports"], preset["h"], preset["volume"], preset["seed"])
        assert lo <= preset["w"] <= hi, name


def test_preset_seeds_lie_outside_the_population():
    assert all(preset["seed"] >= C.POPULATION_INSTANCES for preset in C.PRESETS.values())


def test_preset_names_are_short_for_the_button_row():
    assert all(len(name) <= 22 for name in C.PRESETS)
    assert len(C.PRESETS) == 5
