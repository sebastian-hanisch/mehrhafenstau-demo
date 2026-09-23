"""Abnahmekriterien der Presets (mhs_stories) an KUENSTLICHEN Werten geprueft: jedes Kriterium muss
knapp ueber seiner Schwelle erfuellt sein und knapp darunter kippen - unabhaengig von echten Messdaten.
Ergaenzt test_preset_stories.py (das an echten Daten prueft, ob die Geschichten tragen)."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import mhs_constants as C  # noqa: E402
import mhs_stories as ST  # noqa: E402


class _Fake:
    def __init__(self, restows):
        self.restows = restows


def make_pop(n, z_s, z_b, infeasible_s_share=0.0):
    """n Routen; `infeasible_s_share` davon haben Restows(sortiert)=None, von den restlichen haben
    genau `z_s` (Anteil) 0 Restows, der Rest 3; unabhaengig davon haben `z_b` (Anteil von n) Routen
    Restows(blind)=0, der Rest 5."""
    infeasible_n = round(n * infeasible_s_share)
    feasible_n = n - infeasible_n
    zero_s_n = round(feasible_n * z_s)
    zero_b_n = round(n * z_b)
    results = []
    for i in range(n):
        rs = None if i < infeasible_n else (0 if i < infeasible_n + zero_s_n else 3)
        rb = 0 if i < zero_b_n else 5
        results.append(_Fake({C.RULE_SORTIERT: rs, C.RULE_BLIND: rb}))
    return results


def _ok(name, results, index):
    return ST.criteria(name, results)[index][0]


N = 40


# ---------------------------------------------------------------------------------------------------
# Komfortable Bucht: sortiert >= 95 %, blind >= 90 %
# ---------------------------------------------------------------------------------------------------
def test_komfortabel_sortiert_threshold_tips_at_95_percent():
    assert _ok("Komfortable Bucht", make_pop(N, 0.95, 1.0), 0) is True
    assert _ok("Komfortable Bucht", make_pop(N, 0.925, 1.0), 0) is False


def test_komfortabel_blind_threshold_tips_at_90_percent():
    assert _ok("Komfortable Bucht", make_pop(N, 1.0, 0.90), 1) is True
    assert _ok("Komfortable Bucht", make_pop(N, 1.0, 0.875), 1) is False


# ---------------------------------------------------------------------------------------------------
# Knappe Bucht: sortiert >= 90 %, blind <= 10 %
# ---------------------------------------------------------------------------------------------------
def test_knapp_sortiert_threshold_tips_at_90_percent():
    assert _ok("Knappe Bucht", make_pop(N, 0.90, 0.0), 0) is True
    assert _ok("Knappe Bucht", make_pop(N, 0.875, 0.0), 0) is False


def test_knapp_blind_threshold_tips_at_10_percent():
    assert _ok("Knappe Bucht", make_pop(N, 1.0, 0.10), 1) is True
    assert _ok("Knappe Bucht", make_pop(N, 1.0, 0.125), 1) is False


# ---------------------------------------------------------------------------------------------------
# Sehr knappe Bucht: sortiert 40-80 % (beide Enden inklusive), blind <= 5 %
# ---------------------------------------------------------------------------------------------------
def test_sehr_knapp_sortiert_lower_threshold_tips_at_40_percent():
    assert _ok("Sehr knappe Bucht", make_pop(N, 0.40, 0.0), 0) is True
    assert _ok("Sehr knappe Bucht", make_pop(N, 0.375, 0.0), 0) is False


def test_sehr_knapp_sortiert_upper_threshold_tips_at_80_percent():
    assert _ok("Sehr knappe Bucht", make_pop(N, 0.80, 0.0), 0) is True
    assert _ok("Sehr knappe Bucht", make_pop(N, 0.825, 0.0), 0) is False


def test_sehr_knapp_blind_threshold_tips_at_5_percent():
    assert _ok("Sehr knappe Bucht", make_pop(N, 0.5, 0.05), 1) is True
    assert _ok("Sehr knappe Bucht", make_pop(N, 0.5, 0.075), 1) is False


# ---------------------------------------------------------------------------------------------------
# Kurze Route, knapp: sortiert 70-90 %, blind <= 20 %
# ---------------------------------------------------------------------------------------------------
def test_kurze_route_sortiert_lower_threshold_tips_at_70_percent():
    assert _ok("Kurze Route, knapp", make_pop(N, 0.70, 0.0), 0) is True
    assert _ok("Kurze Route, knapp", make_pop(N, 0.675, 0.0), 0) is False


def test_kurze_route_sortiert_upper_threshold_tips_at_90_percent():
    assert _ok("Kurze Route, knapp", make_pop(N, 0.90, 0.0), 0) is True
    assert _ok("Kurze Route, knapp", make_pop(N, 0.925, 0.0), 0) is False


def test_kurze_route_blind_threshold_tips_at_20_percent():
    assert _ok("Kurze Route, knapp", make_pop(N, 0.8, 0.20), 1) is True
    assert _ok("Kurze Route, knapp", make_pop(N, 0.8, 0.225), 1) is False


# ---------------------------------------------------------------------------------------------------
# Niedrige Bucht: sortiert (unter den machbaren) >= 90 %, Anteil infeasible in (0 %, 25 %]
# ---------------------------------------------------------------------------------------------------
def test_niedrige_bucht_sortiert_threshold_tips_at_90_percent():
    # infeasible_s_share=0 hier bewusst: die Nullquote-Schwelle wird unter den FEASIBLE Routen geprueft
    # (siehe E.zero_share), 40 glatt teilbare feasible Routen machen 90 %/87,5 % exakt treffbar.
    assert _ok("Niedrige Bucht", make_pop(N, 0.90, 0.0), 0) is True
    assert _ok("Niedrige Bucht", make_pop(N, 0.875, 0.0), 0) is False


def test_niedrige_bucht_infeasible_share_must_be_strictly_positive():
    assert _ok("Niedrige Bucht", make_pop(N, 0.90, 0.0, infeasible_s_share=0.0), 1) is False
    assert _ok("Niedrige Bucht", make_pop(N, 0.90, 0.0, infeasible_s_share=0.025), 1) is True


def test_niedrige_bucht_infeasible_share_threshold_tips_at_25_percent():
    assert _ok("Niedrige Bucht", make_pop(N, 0.90, 0.0, infeasible_s_share=0.25), 1) is True
    assert _ok("Niedrige Bucht", make_pop(N, 0.90, 0.0, infeasible_s_share=0.275), 1) is False


def test_unknown_preset_name_raises_for_both_criteria_functions():
    with pytest.raises(KeyError):
        ST.criteria("Nicht existent", make_pop(N, 1.0, 1.0))
    with pytest.raises(KeyError):
        ST.shown_criteria("Nicht existent", _Fake({C.RULE_SORTIERT: 0, C.RULE_BLIND: 0}))


# ---------------------------------------------------------------------------------------------------
# shown_criteria: Restows sind ganzzahlig, Schwellen kippen bei exakten Zaehlwerten
# ---------------------------------------------------------------------------------------------------
def _ok_shown(name, restows_s, restows_b, index):
    return ST.shown_criteria(name, _Fake({C.RULE_SORTIERT: restows_s, C.RULE_BLIND: restows_b}))[index][0]


def test_komfortabel_shown_needs_exactly_zero_restows_sortiert():
    assert _ok_shown("Komfortable Bucht", 0, 0, 0) is True
    assert _ok_shown("Komfortable Bucht", 1, 0, 0) is False


def test_knapp_shown_blind_threshold_tips_at_two_restows():
    assert _ok_shown("Knappe Bucht", 0, 2, 1) is True
    assert _ok_shown("Knappe Bucht", 0, 1, 1) is False


def test_sehr_knapp_shown_needs_at_least_one_restow_sortiert():
    assert _ok_shown("Sehr knappe Bucht", 1, 5, 0) is True
    assert _ok_shown("Sehr knappe Bucht", 0, 5, 0) is False


def test_sehr_knapp_shown_blind_margin_tips_at_sortiert_plus_two():
    assert _ok_shown("Sehr knappe Bucht", 1, 3, 1) is True
    assert _ok_shown("Sehr knappe Bucht", 1, 2, 1) is False


def test_niedrige_bucht_shown_sortiert_must_be_feasible_and_at_most_one():
    assert _ok_shown("Niedrige Bucht", 1, 2, 0) is True
    assert _ok_shown("Niedrige Bucht", 2, 2, 0) is False
    assert ST.shown_criteria("Niedrige Bucht", _Fake({C.RULE_SORTIERT: None, C.RULE_BLIND: 2}))[0][0] is False
