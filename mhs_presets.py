"""Regler-Spezifikation, Permalink, Presets und Seed-Knopf (Standardmuster aus dem OR-Demo-Portfolio,
siehe lcr_presets.py in leercontainer-demo).

Die Stapelzahl W hat eine BERECHNETE Grenze (Patience-Grenze der aktuellen Route + Puffer, siehe
mhs_evaluation.w_upper_bound). `clamp_w` begrenzt sie, statt sie zu verwerfen; die App ruft
limit_dependent_state() vor dem Erzeugen der Regler auf (Permalink, Preset, geaenderte Haefen/Hoehe/
Volumen/Seed) - wie beim Vorschau-Fenster der Leercontainer-Demo."""
import math
import random
from dataclasses import dataclass
from typing import Callable, Optional

import streamlit as st

import mhs_constants as C
from mhs_evaluation import w_upper_bound
from mhs_scenario import make_scenario


def _int_text(value):
    return str(int(value))


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: Callable
    default: object
    lo: Optional[float] = None
    hi: Optional[float] = None
    step: Optional[int] = None
    encoder: Callable = _int_text


SETTING_SPECS = {
    "n_ports_slider": SettingSpec("np", int, C.N_PORTS_DEFAULT, *C.N_PORTS_RANGE, 1),
    "w_slider": SettingSpec("w", int, None, C.W_MIN, C.W_SPEC_MAX, 1),   # Default haengt von der Route ab, siehe init_session_state_defaults
    "h_slider": SettingSpec("h", int, C.H_DEFAULT, *C.H_RANGE, 1),
    "volume_slider": SettingSpec("vol", int, C.VOLUME_DEFAULT, *C.VOLUME_RANGE, 1),
    "seed_input": SettingSpec("seed", int, C.SEED_DEFAULT, *C.SEED_RANGE, 1),
}

PRESET_STATE_KEYS = {
    "n_ports": "n_ports_slider", "w": "w_slider", "h": "h_slider", "volume": "volume_slider", "seed": "seed_input",
}


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def parse_setting(spec, raw):
    """Wert aus der Adresszeile: umwandeln, auf den Bereich begrenzen, auf die Schrittweite runden.
    None, wenn er sich nicht auswerten laesst."""
    try:
        value = spec.caster(raw)
    except (ValueError, TypeError):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if spec.lo is not None:
        value = max(spec.lo, value)
    if spec.hi is not None:
        value = min(spec.hi, value)
    if spec.step and spec.step > 1 and spec.lo is not None:
        value = spec.lo + round((value - spec.lo) / spec.step) * spec.step
        value = min(spec.hi, value)
    return value


def w_bounds(n_ports, h, volume, seed):
    """Berechnete Obergrenze des W-Reglers fuer diese Route (Patience-Grenze + Puffer)."""
    loads, _ = make_scenario(int(n_ports), int(volume), int(seed))
    return C.W_MIN, w_upper_bound(loads)


def default_w(n_ports=C.N_PORTS_DEFAULT, h=C.H_DEFAULT, volume=C.VOLUME_DEFAULT, seed=C.SEED_DEFAULT):
    """Default fuer W: zwei ueber dem exakten Mindestbedarf der Standardroute (klar komfortabel, aber
    nicht am oberen Reglerrand) - Faustregel-Marke plus etwas Puffer, nicht die knappe Kapazitaetsgrenze
    (die zeigen die Presets)."""
    lo, hi = w_bounds(n_ports, h, volume, seed)
    return max(lo, hi - 1)


def clamp_w(n_ports, h, volume, seed, w):
    lo, hi = w_bounds(n_ports, h, volume, seed)
    return max(lo, min(int(w), hi))


def limit_dependent_state():
    """Begrenzt die abhaengige Stapelzahl W im session_state (vor dem Erzeugen der Widgets aufrufen)."""
    s = st.session_state
    s["w_slider"] = clamp_w(s["n_ports_slider"], s["h_slider"], s["volume_slider"], s["seed_input"], s["w_slider"])


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            if state_key == "w_slider":
                st.session_state[state_key] = default_w()
            else:
                st.session_state[state_key] = spec.default


def load_permalink_settings():
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            value = parse_setting(spec, qp[spec.url_param])
            if value is not None:
                st.session_state[state_key] = value
    if "w_slider" not in st.session_state:
        st.session_state["w_slider"] = default_w(
            st.session_state.get("n_ports_slider", C.N_PORTS_DEFAULT),
            st.session_state.get("h_slider", C.H_DEFAULT),
            st.session_state.get("volume_slider", C.VOLUME_DEFAULT),
            st.session_state.get("seed_input", C.SEED_DEFAULT),
        )
    st.session_state["permalink_loaded"] = True


def sync_query_params(values):
    """values: dict state_key -> aktueller Wert (aus den Widgets)."""
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = SETTING_SPECS[state_key].encoder(value)
    except Exception:
        pass


def apply_preset(name):
    for field, state_key in PRESET_STATE_KEYS.items():
        st.session_state[state_key] = C.PRESETS[name][field]


def randomize_seed():
    """Wuerfelt einen neuen Seed fuer die Route (Ladeliste je Hafen)."""
    st.session_state["seed_input"] = random.randint(*C.SEED_RANGE)
