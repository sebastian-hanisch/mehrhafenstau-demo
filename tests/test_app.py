"""AppTest: Skelett und Footer, jedes Preset, Permalink mit berechneter W-Grenze, alle Regler an Min
und Max, Kennzahlen im 2 x 2-Raster, die bedingte Meldung in allen Zustaenden, Urteil in allen
Zustaenden, Vergleichstabelle, PDF, Texte."""
import pathlib

import pytest
from streamlit.testing.v1 import AppTest

import mhs_constants as C
import mhs_evaluation as E
import mhs_stories as ST
from mhs_presets import w_bounds, SETTING_SPECS

APP = str(pathlib.Path(__file__).resolve().parent.parent / "app.py")
FOOTER = ("Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
          "Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung für "
          "Ihr Unternehmen? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html)")


@pytest.fixture(autouse=True)
def clean_cache():
    """st.cache_data ist prozessweit: Tests, die Einstellungen aendern, duerfen keine
    zwischengespeicherten Ergebnisse anderer Tests sehen."""
    import streamlit as st
    st.cache_data.clear()
    yield


def fresh(**query):
    at = AppTest.from_file(APP, default_timeout=180)
    for k, v in query.items():
        at.query_params[k] = v
    at.run()
    assert not at.exception, at.exception
    return at


def set_and_run(at, **values):
    for key, value in values.items():
        (at.number_input if key.endswith("_input") else at.slider)(key=key).set_value(value)
    at.run()
    assert not at.exception, at.exception
    return at


def main_metrics(at):
    return [(m.label, m.value) for m in at.metric[:4]]


def click(at, label):
    next(b for b in at.button if b.label == label).click().run()
    assert not at.exception, at.exception
    return at


def message(at, needle):
    for group in (at.success, at.warning, at.info, at.error):
        for x in group:
            if needle in x.value:
                return x.value
    return None


# ---------------------------------------------------------------------------------------------------
# Skelett
# ---------------------------------------------------------------------------------------------------
def test_skeleton_and_footer():
    at = fresh()
    assert [h.value for h in at.sidebar.header] == ["⚙️ Einstellungen"]                # genau EIN Header
    assert len(at.title) == 1 and "Mehrhafen-Stauplanung" in at.title[0].value
    assert any(v.value.startswith("## 🎯") for v in at.markdown)
    assert any(v.value.startswith("### 📐") for v in at.markdown)
    assert [e.label for e in at.expander] == ["🔧 Wie wir das erreichen – Regeln im Vergleich", "Wie funktioniert diese Demo?", "📐 Mathematische Formulierung"]
    assert any(c.value == FOOTER for c in at.caption)
    presets = [b.label for b in at.button if b.label in C.PRESETS]
    assert presets == list(C.PRESETS) and len(presets) == 5 and all(len(n) <= 22 for n in presets)
    assert [s.label for s in at.sidebar.slider] == ["Häfen (Route)", "Stapel (Breite W)", "Höhe H", "Ladevolumen je Hafen"]
    assert [n.label for n in at.sidebar.number_input] == ["Seed"] and any(b.label == "🎲 Neue Route" for b in at.sidebar.button)


def test_main_metrics_are_2x2_with_the_right_labels():
    at = fresh()
    labels = [m[0] for m in main_metrics(at)]
    assert labels == ["Restows (sortiert)", "Restows (blind)", "Abstand zum Mindestbedarf", "Nullquote (Stichprobe)"]


def test_charts_are_present_with_unique_keys():
    at = fresh()
    charts = at.get("plotly_chart")
    keys = [c.key for c in charts]
    assert len(set(keys)) == len(keys) and all(keys)
    assert len(keys) == 7        # Buchtansicht, Restow-Kurve, Hoehe-Kurve, 2 Tab-Buchtansichten, Exakt-Kurve, Vergleichskurve


# ---------------------------------------------------------------------------------------------------
# Presets, Permalink
# ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_loads_within_widget_bounds_and_shows_its_story(name):
    at = fresh()
    click(at, name)
    preset = C.PRESETS[name]
    assert at.slider(key="n_ports_slider").value == preset["n_ports"] and at.slider(key="h_slider").value == preset["h"]
    assert at.slider(key="volume_slider").value == preset["volume"] and at.slider(key="w_slider").value == preset["w"]
    assert at.number_input(key="seed_input").value == preset["seed"]

    p = E.Params(preset["n_ports"], preset["h"], preset["volume"], preset["w"])
    shown = E.route_result(p, preset["seed"])
    for ok, text in ST.shown_criteria(name, shown):
        assert ok, f"{name}: {text}"

    labels = [m[0] for m in main_metrics(at)]
    values = [m[1] for m in main_metrics(at)]
    assert labels[0] == "Restows (sortiert)" and values[0] == str(shown.restows[C.RULE_SORTIERT])
    assert labels[1] == "Restows (blind)" and values[1] == str(shown.restows[C.RULE_BLIND])


def test_permalink_is_clamped_snapped_and_ignores_garbage():
    at = fresh(np="99", vol="abc", h="1", junk="ignored")
    assert at.slider(key="n_ports_slider").value == C.N_PORTS_RANGE[1]      # geklemmt
    assert at.slider(key="volume_slider").value == C.VOLUME_DEFAULT          # Muell ignoriert
    assert at.slider(key="h_slider").value == C.H_RANGE[0]                   # unter der Spezifikationsuntergrenze geklemmt


def test_permalink_limits_the_stack_count_instead_of_dropping_it():
    at = fresh(np="4", h="2", w="40")
    lo, hi = w_bounds(4, 2, C.VOLUME_DEFAULT, C.SEED_DEFAULT)
    assert at.slider(key="n_ports_slider").value == 4 and at.slider(key="h_slider").value == 2
    assert at.slider(key="w_slider").value == hi and at.slider(key="w_slider").max == hi


def test_permalink_roundtrip_reflects_settings():
    at = fresh(np="6", h="3", vol="3", seed="11")
    values = {k: at.session_state[k] for k in SETTING_SPECS if k != "w_slider"}
    assert values == {"n_ports_slider": 6, "h_slider": 3, "volume_slider": 3, "seed_input": 11}
    for key, spec in SETTING_SPECS.items():
        got = at.query_params[spec.url_param]
        got = got[0] if isinstance(got, list) else got
        assert got == spec.encoder(at.session_state[key]), key


def test_changing_ports_or_height_limits_the_stack_slider():
    at = fresh()
    at = set_and_run(at, n_ports_slider=4, h_slider=10)
    lo, hi = w_bounds(4, 10, at.session_state["volume_slider"], at.session_state["seed_input"])
    if hi > lo:
        assert at.slider(key="w_slider").max == hi
    else:
        assert not any(s.key == "w_slider" for s in at.slider)


def test_new_route_button_changes_only_the_seed():
    at = fresh()
    before = {k: at.session_state[k] for k in SETTING_SPECS if k != "seed_input"}
    click(at, "🎲 Neue Route")
    assert {k: at.session_state[k] for k in SETTING_SPECS if k != "seed_input"} == before
    assert C.SEED_RANGE[0] <= at.session_state["seed_input"] <= C.SEED_RANGE[1]


# ---------------------------------------------------------------------------------------------------
# Regler an den Grenzen
# ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("key,value", [("n_ports_slider", 4), ("n_ports_slider", 12), ("h_slider", 2), ("h_slider", 10), ("volume_slider", 1), ("volume_slider", 4)])
def test_every_slider_works_at_its_minimum_and_maximum(key, value):
    at = set_and_run(fresh(), **{key: value})
    assert at.session_state[key] == value and len(at.metric) >= 4


def test_seed_input_works_at_its_minimum_and_maximum():
    at = set_and_run(fresh(), seed_input=C.SEED_RANGE[0])
    assert at.session_state["seed_input"] == C.SEED_RANGE[0]
    at = set_and_run(fresh(), seed_input=C.SEED_RANGE[1])
    assert at.session_state["seed_input"] == C.SEED_RANGE[1]


def test_extreme_combination_runs_without_exception():
    at = fresh(np="4", h="2", vol="1", seed="0")
    assert not at.exception
    at = fresh(np="12", h="10", vol="4", seed="9999")
    assert not at.exception


# ---------------------------------------------------------------------------------------------------
# Bedingte Meldung
# ---------------------------------------------------------------------------------------------------
def test_message_too_narrow_when_w_below_exact_minimum():
    at = fresh(np="10", h="4", vol="2", seed="41", w="3")   # W*=4 bei diesem Seed, W=3 ist feasible aber zu knapp
    msg = message(at, "Bucht zu knapp")
    assert msg is not None and "nötig" in msg


def test_message_at_limit_when_w_equals_exact_minimum():
    at = fresh(np="8", h="4", vol="2", seed="0")
    lo, hi = w_bounds(8, 4, 2, 0)
    exact = 3   # siehe sweep_data.json Beispiel (Seed 0, 8 Haefen, Hoehe 4)
    at = set_and_run(at, w_slider=exact)
    msg = message(at, "Genau am Limit")
    assert msg is not None


def test_message_comfortable_when_w_above_exact_minimum():
    at = fresh(np="8", h="4", vol="2", seed="0")
    at = set_and_run(at, w_slider=6)   # oberhalb des Minimums (3) und der Patience-Grenze (4)
    msg = message(at, "Komfortabel")
    assert msg is not None


def test_message_infeasible_when_capacity_below_peak_demand():
    at = fresh(np="10", h="1", vol="4", seed="0", w="1")
    msg = message(at, "reicht")
    assert msg is not None


# ---------------------------------------------------------------------------------------------------
# Kernabschnitt: Urteil
# ---------------------------------------------------------------------------------------------------
def test_verdict_sentence_present_with_the_right_label():
    at = fresh()
    texts = [x.value for group in (at.success, at.warning, at.info) for x in group if "gegen blind" in x.value]
    assert len(texts) >= 1
    assert any("Zielhafen-sortiert gegen blind" in t for t in texts)


def _fake_verdict(monkeypatch, kind, diff, se=1.0, n=20):
    import mhs_evaluation as E_mod
    monkeypatch.setattr(E_mod, "verdict", lambda res: E_mod.Verdict(kind, diff, se, n))


def test_verdict_sentence_better_and_worse(monkeypatch):
    _fake_verdict(monkeypatch, "better", -3.0)
    at = fresh()
    assert any("weniger Restows" in x.value for x in at.success)
    _fake_verdict(monkeypatch, "worse", 3.0)
    at = fresh()
    assert any("mehr Restows" in x.value for x in at.warning)


def test_verdict_sentence_unclear(monkeypatch):
    _fake_verdict(monkeypatch, "unclear", 0.2)
    at = fresh()
    assert any("Kein klarer Unterschied" in x.value for x in at.info)


def test_verdict_sentence_no_comparable_routes(monkeypatch):
    _fake_verdict(monkeypatch, "unclear", 0.0, se=0.0, n=0)
    at = fresh()
    assert any("Kein Vergleich möglich" in x.value for x in at.info)


# ---------------------------------------------------------------------------------------------------
# Bausteine im Vergleich, PDF, Texte
# ---------------------------------------------------------------------------------------------------
def test_comparison_table_has_one_row_per_rule():
    at = fresh()
    dfs = at.dataframe
    comparison_df = dfs[-1].value
    assert list(comparison_df["Regel"]) == [C.RULE_LABELS[C.RULE_BLIND], C.RULE_LABELS[C.RULE_SORTIERT]]
    assert "Nullquote" in comparison_df.columns and "Abstand zum Mindestbedarf" in comparison_df.columns


def test_exact_tab_shows_a_row_per_stack_count():
    at = fresh()
    dfs = at.dataframe
    exact_df = dfs[0].value
    assert list(exact_df.columns) == ["W", "Restows (sortiert)", "0 Restows?"]
    assert len(exact_df) == C.W_SEARCH_MAX


def test_each_rule_tab_shows_a_bay_view():
    at = fresh()
    charts = at.get("plotly_chart")
    assert sum(1 for c in charts if c.key.startswith("tab_blind_") or c.key.startswith("tab_sortiert_")) == 2


def test_pdf_download_button_is_offered():
    at = fresh()
    buttons = at.get("download_button")
    assert len(buttons) == 1 and buttons[0].proto.label == "📄 Ergebnis als PDF herunterladen"


def test_texts_state_the_model_and_the_limits():
    at = fresh()
    text = "\n".join(m.value for m in at.expander[1].markdown)
    for needle in ("Restow", "zielhafen-sortierte Regel", "Mindestbedarf", "Patience-Sorting", "Gewicht"):
        assert needle in text, needle
    math_text = "\n".join(m.value for m in at.expander[2].markdown)
    for needle in ("Zulässige Platzierung", "W^\\ast", "Patience Sorting", "2 \\, \\mathrm{SE}"):
        assert needle in math_text, needle
