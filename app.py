"""
Mehrhafen-Stauplanung - interaktive Fall-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Welle 2 der Seefracht-Linie: wie viele Stapelplaetze (Breite x Hoehe) braucht eine Bucht, damit ueber
die ganze Route kein Container wegen eines spaeter auslaufenden Nachbarn kurz umgesetzt werden muss
(Restow)? Anders als bei der Stapelplanung der Hafen-Linie (ein Hafen, geschaetzte Abfahrt) ist hier
die ganze Route mit mehreren Haefen im Spiel, und jedes Ziel ist von Anfang an exakt bekannt.

Lauffaehig mit: streamlit run app.py
"""
import streamlit as st

import mhs_constants as C
import mhs_evaluation as E
import mhs_rules as R
import mhs_scenario as SC
import mhs_visualization as V
from mhs_pdf_export import generate_mhs_pdf
from mhs_presets import (apply_preset, bounds, init_session_state_defaults, limit_dependent_state, load_permalink_settings,
                         randomize_seed, SETTING_SPECS, sync_query_params, w_bounds)
from mhs_ui_panel import render_bay_step, render_comparison_tab, render_exact_panel, render_metrics, render_rule_panel

st.set_page_config(page_title="Mehrhafen-Stauplanung - Sebastian Hanisch", layout="wide")

SCENARIO_KEYS = list(SETTING_SPECS)


@st.cache_data(show_spinner=False, max_entries=64)
def _compute_route(n_ports, volume, seed):
    return SC.make_scenario(int(n_ports), int(volume), int(seed))


@st.cache_data(show_spinner=False, max_entries=64)
def _compute_curve(n_ports, volume, seed, h, w_max):
    loads, _ = _compute_route(n_ports, volume, seed)
    return E.restow_curve(loads, h, w_max)


@st.cache_data(show_spinner=False, max_entries=32)
def _compute_height_curve(n_ports, volume, h_values, seeds):
    return E.height_curve(n_ports, volume, h_values, seeds)


@st.cache_data(show_spinner=False, max_entries=32)
def _compute_sample(n_ports, h, volume, w, n):
    return E.sample(E.Params(n_ports, h, volume, w), n)


st.title("🚢 Mehrhafen-Stauplanung: Wie viele Stapelplätze für null Restows?")
st.markdown(
    """
Ein Container, der auf ein **spät auslaufendes Ziel** gestapelt wird, blockiert jeden darunterliegenden Container mit einem **früheren** Ziel: beim Löschen muss er kurz umgesetzt werden (**Restow**)
- ein unproduktiver Kranhub extra. Anders als bei der Stapelplanung der Hafen-Linie (ein Hafen, geschätzte Abfahrt) ist hier die **ganze Route** mit mehreren Anlaufhäfen im Spiel, und jedes Ziel ist
von Anfang an **exakt bekannt**. Diese Demo zeigt, wie viele Stapelplätze eine Bucht dafür braucht - und was an der Kapazitätsgrenze passiert. Wie das Modell funktioniert, steht im Expander "Wie
funktioniert diese Demo?" weiter unten, die formale Beschreibung im Expander "📐 Mathematische Formulierung".
"""
)

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
PRESET_HELP = {
    "Komfortable Bucht": "Normal bemessene Bucht: die sortierte Regel ist praktisch immer perfekt - bewusst der \"unspektakuläre\" Referenzfall.",
    "Knappe Bucht": "An der Kapazitätsgrenze zeigt sich der Unterschied: sortiert bleibt fast perfekt, blind bricht spürbar ein.",
    "Sehr knappe Bucht": "Am absoluten Limit: selbst die sortierte Regel schafft es nicht immer, blind versagt praktisch immer.",
    "Kurze Route, knapp": "Auch bei kürzerer Route zeigt sich dieselbe Lücke, nur schwächer ausgeprägt.",
    "Niedrige Bucht": "Wenig Höhe zwingt zu mehr Breite - zeigt den Höhe-Breite-Kompromiss und dass zu wenig Höhe auch schlicht unmöglich machen kann.",
}
preset_names = list(C.PRESETS.keys())
for row in (preset_names[:3], preset_names[3:]):
    cols = st.columns(3)
    for col, name in zip(cols, row):
        with col:
            st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=PRESET_HELP[name])

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()
limit_dependent_state()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    n_ports = st.slider("Häfen (Route)", *bounds("n_ports_slider"), key="n_ports_slider", help="Routenlänge (Anzahl Häfen).")
    # Stapel (Breite W) steht laut Skelett direkt hinter den Häfen, ihre Grenze haengt aber auch von
    # Hoehe/Volumen/Seed ab - deren Widgets sind erst weiter unten an der Reihe. Wir lesen den noch
    # ausstehenden Wert direkt aus dem session_state (von load_permalink_settings/apply_preset/
    # limit_dependent_state bereits gesetzt); das Erzeugen der Widgets unten aendert daran nichts.
    _h_now = st.session_state.get("h_slider", C.H_DEFAULT)
    _volume_now = st.session_state.get("volume_slider", C.VOLUME_DEFAULT)
    _seed_now = st.session_state.get("seed_input", C.SEED_DEFAULT)
    _w_lo, _w_hi = w_bounds(n_ports, _h_now, _volume_now, _seed_now)
    _loads_preview, _ = _compute_route(int(n_ports), int(_volume_now), int(_seed_now))
    _exact_preview = E.exact_min(_loads_preview, int(_h_now))
    if _w_hi > _w_lo:
        w = st.slider("Stapel (Breite W)", int(_w_lo), int(_w_hi), key="w_slider",
                      help=f"Grenze berechnet (Patience-Grenze der Route + Puffer). Mindestbedarf der sortierten Regel bei dieser Höhe/Route: W* = {_exact_preview}.")
    else:
        w = _w_lo
        st.session_state["w_slider"] = w
        st.caption(f"Stapel (Breite W): {w} (bei dieser Route gibt es keinen Spielraum). Mindestbedarf der sortierten Regel: W* = {_exact_preview}.")
    h = st.slider("Höhe H", *bounds("h_slider"), key="h_slider", help="Stapelhöhe; siehe Sättigungspunkt im Kernabschnitt.")
    volume = st.slider("Ladevolumen je Hafen", *bounds("volume_slider"), key="volume_slider", help="Zahl neuer Container, die jeder Hafen außer dem letzten lädt (genau so viele; zufällig sind nur ihre Zielhäfen).")
    seed = st.number_input("Seed", *bounds("seed_input"), key="seed_input", step=1, help="Bestimmt die Ladeliste (Zielhäfen je Hafen).")
    st.button("🎲 Neue Route", width="stretch", on_click=randomize_seed, help="Würfelt einen neuen Seed für die Ladeliste.")

sync_query_params({key: st.session_state[key] for key in SCENARIO_KEYS})

n_ports, h, volume, w, seed = int(n_ports), int(h), int(volume), int(w), int(seed)
loads, peak = _compute_route(n_ports, volume, seed)
static_bound_value = E.static_bound(loads)
dyn_min = E.exact_min(loads, h)

try:
    result_sortiert = R.simulate(loads, w, h, C.RULE_SORTIERT, record=True)
    restows_sortiert = result_sortiert["restows"]
except R.Infeasible:
    result_sortiert, restows_sortiert = None, None
try:
    restows_blind = R.simulate(loads, w, h, C.RULE_BLIND)["restows"]
except R.Infeasible:
    restows_blind = None

diag = E.diagnose(w, dyn_min, restows_sortiert)

with st.spinner("Rechne Stichprobe..."):
    sample_results = _compute_sample(n_ports, h, volume, w, C.SAMPLE_INSTANCES)
zero_share_sample = E.zero_share(sample_results, C.RULE_SORTIERT)
mean_gap_sample = None
if dyn_min is not None:
    gaps = [w - r.exact_w for r in sample_results if r.exact_w is not None]
    if gaps:
        mean_gap_sample = sum(gaps) / len(gaps)

# ---------------------------------------------------------------------------------------------------
# Hauptansicht
# ---------------------------------------------------------------------------------------------------
st.markdown("## 🎯 Wie viele Restows entstehen mit dieser Bucht?")
st.caption(f"{n_ports} Häfen, Höhe {h}, Stapelzahl W={w}, Ladevolumen {volume} je Hafen, Seed {seed}.")

metric_rows = [st.columns(2), st.columns(2)]
render_metrics(metric_rows[0] + metric_rows[1], restows_sortiert, restows_blind, diag.gap, zero_share_sample)

if diag.kind == "infeasible":
    st.error(f"⛔ Diese Bucht-Größe reicht für den Verkehr dieser Route nicht (Kapazität W×H={w * h} zu klein) - unabhängig von der Regel. Die sortierte Regel braucht mindestens W={dyn_min}, um 0 Restows zu erreichen.")
elif diag.kind == "too_narrow":
    st.warning(f"⚠️ Bucht zu knapp: die sortierte Regel braucht mindestens **W={diag.exact_w}** für 0 Restows (eingestellt: W={w}, {abs(diag.gap)} zu wenig).")
elif diag.kind == "at_limit":
    st.info(f"ℹ️ Genau am Limit (**W={diag.exact_w}**): kein Puffer, jede zusätzliche Unregelmäßigkeit führt sofort zu Restows.")
elif diag.kind == "comfortable":
    st.success(f"✅ Komfortabel: **{diag.gap} Stapel mehr** als der Mindestbedarf der sortierten Regel (W*={diag.exact_w}) - kein Handlungsbedarf.")
else:
    st.info("ℹ️ Kein Mindestbedarf innerhalb der Sicherheitsgrenze der Suche gefunden.")

st.markdown("#### 🗺️ Bucht-Zustand über die Route (Regel: zielhafen-sortiert)")
if result_sortiert is not None:
    render_bay_step("main", result_sortiert["steps"], w, h, n_ports, C.RULE_LABELS[C.RULE_SORTIERT])
else:
    st.info("Keine Route-Ansicht: diese Bucht-Größe ist bei dieser Route nicht machbar.")

pdf_slot = st.container()

st.markdown("---")

# ---------------------------------------------------------------------------------------------------
# Kernabschnitt
# ---------------------------------------------------------------------------------------------------
st.markdown("### 📐 Wie viele Stapelplätze braucht die Bucht?")
st.markdown(
    """
Kernfrage dieser Demo: bei welcher Bucht-Größe kommt die Route mit der zielhafen-sortierten Regel ohne Restows aus - und wie eng ist die Lehrbuch-Faustregel (Patience Sorting) an dieser dynamischen Grenze dran?
Links: Restows über der Stapelzahl W für **Ihre Route**, beide Regeln, mit der Patience-Grenze (grau gestrichelt) und dem Mindestbedarf der Regel (grün gestrichelt). Rechts: wie viele Stapel bei welcher
Höhe im Mittel mindestens nötig sind, bei Ihren Häfen/Ihrem Ladevolumen - der Sättigungspunkt, ab dem mehr Höhe nichts mehr bringt.
"""
)
curve = _compute_curve(n_ports, volume, seed, h, C.W_SEARCH_MAX)
h_values = tuple(sorted({2, 3, 4, 6, 8, 10} & set(range(C.H_RANGE[0], C.H_RANGE[1] + 1))))
height_curve_data = _compute_height_curve(n_ports, volume, h_values, tuple(range(C.SAMPLE_INSTANCES)))

col_left, col_right = st.columns(2)
with col_left:
    st.plotly_chart(V.restow_curve_figure(curve, static_bound_value, dyn_min, w), width="stretch", key="main_restow_curve_chart")
with col_right:
    st.plotly_chart(V.height_curve_figure(height_curve_data, h), width="stretch", key="main_height_curve_chart")

st.caption(f"Basis: {C.SAMPLE_INSTANCES} Routen derselben Einstellung (nicht Ihr Seed). Rechenzeit gemessen: die Mindestbedarfs-Suche (W bis {C.W_SEARCH_MAX} durchprobieren) braucht auch bei der "
          f"größten Route ({C.N_PORTS_RANGE[1]} Häfen, Höhe {C.H_RANGE[1]}) deutlich unter 1 ms - ohne Knopf möglich, live bei jedem Reglerzug.")

st.markdown("**Urteil über die Stichprobe** (gepaarte Differenz je Route, klar ab mehr als zwei Standardfehlern)")
v = E.verdict(sample_results)
if v.n == 0:
    st.info("ℹ️ Kein Vergleich möglich: keine Route der Stichprobe ist für beide Regeln machbar.")
elif v.kind == "better":
    st.success(f"✅ **Zielhafen-sortiert gegen blind**: im Mittel **{abs(v.diff):.2f} weniger Restows** je Route (Differenz {v.diff:+.2f}, Standardfehler {v.se:.2f}, n={v.n}).")
elif v.kind == "worse":
    st.warning(f"⚠️ **Zielhafen-sortiert gegen blind**: im Mittel **{abs(v.diff):.2f} mehr Restows** je Route (Differenz {v.diff:+.2f}, Standardfehler {v.se:.2f}, n={v.n}).")
else:
    st.info(f"ℹ️ Kein klarer Unterschied zwischen sortiert und blind bei dieser Einstellung (Differenz {v.diff:+.2f} Restows, Standardfehler {v.se:.2f}, n={v.n}).")

with pdf_slot:
    st.download_button(
        "📄 Ergebnis als PDF herunterladen",
        data=generate_mhs_pdf(n_ports, w, h, volume, seed, restows_sortiert, restows_blind, diag, static_bound_value, dyn_min,
                              curve=curve, sample_results=sample_results, verdict=v),
        file_name="mehrhafenstau_ergebnis.pdf", mime="application/pdf", key="primary_pdf_download",
        help="Route, Restows je Regel, Diagnose, Restow-über-W-Kurve und die Stichprobe mit Urteil.")

st.markdown("---")

# ---------------------------------------------------------------------------------------------------
# Bausteine im Vergleich
# ---------------------------------------------------------------------------------------------------
with st.expander("🔧 Wie wir das erreichen – Regeln im Vergleich"):
    tabs = st.tabs([C.RULE_LABELS[C.RULE_BLIND], C.RULE_LABELS[C.RULE_SORTIERT], C.EXACT_TAB_LABEL, C.COMPARISON_TAB_LABEL])
    with tabs[0]:
        render_rule_panel("tab_blind", C.RULE_BLIND, loads, w, h, n_ports)
    with tabs[1]:
        render_rule_panel("tab_sortiert", C.RULE_SORTIERT, loads, w, h, n_ports)
    with tabs[2]:
        render_exact_panel(loads, h, n_ports, curve, static_bound_value, dyn_min, w)
    with tabs[3]:
        render_comparison_tab(sample_results, curve, static_bound_value, dyn_min, w, mean_gap_sample)

with st.expander("Wie funktioniert diese Demo?"):
    st.markdown(
        """
**Route und Bucht.** N Häfen in fester Reihenfolge; an jedem Hafen wird zuerst entladen (Container mit Ziel = dieser Hafen; blockierende Container mit späterem Ziel werden kurz umgesetzt = Restow),
dann geladen (neue Container mit Ziel > dieser Hafen, absteigend nach Ziel). Anders als bei der Stapelplanung der Hafen-Linie (geschätzte Abfahrt) ist der Zielhafen jedes Containers von Anfang an
**exakt bekannt** - die Frage ist reine Kombinatorik, kein Schätzfehler.

**Die zielhafen-sortierte Regel und warum sie meistens reicht.** Sie bevorzugt einen Stapel, dessen oberster Container ein Ziel ≥ dem neuen hat (die Sortierung "oben = nächstes Ziel" bleibt
erhalten), bestfit unter den gültigen Stapeln. Bei komfortabel bemessener Bucht ist sie fast immer perfekt (0 Restows) - ein reiner Vergleich gegen die blinde Regel wäre dort langweilig. Erst an der
echten Kapazitätsgrenze (Presets "Knapp"/"Sehr knapp") zeigt sich ein robuster Unterschied.

**Der Mindestbedarf der Regel und die Lehrbuch-Faustregel.** W* ist das kleinste W, für das die sortierte Regel über die ganze Route 0 Restows erreicht - per Suche live berechnet, kein separater Löser.
Das ist der Bedarf **dieser Regel**, nicht das Minimum über alle denkbaren Stapelverfahren: eine Vollaufzählung aller Platzierungen fand in 12 von 260 Zufallsrouten (4-7 Häfen, Volumen 1-3, Höhe 2-5) ein
Verfahren mit weniger Stapeln (Beispiel: Ladeliste [[2,4],[3,2],[5,3],[4,5],[5,5],[]] bei Höhe 4 - die Regel braucht W=3, mit zwei Stapeln geht es per Hand: 4 und 2 getrennt auf zwei Stapel legen).
Die klassische Patience-Sorting-Formel (längste streng steigende Teilfolge der Ladereihenfolge) ist eine sichere, aber SEHR lockere obere Schranke: sie ignoriert, dass echtes Zwischenentladen
unterwegs Platz freigibt - der dynamische Mindestbedarf der Regel liegt im Mittel nur bei etwa 55 bis 80 % der Faustregel (Voreinstellung 8 Häfen, H = 4, Volumen 2: 65 %; bei höheren Stapeln etwa 63 %, bei niedrigen Stapeln und hohem Volumen näher an der Faustregel).

**Grenzen dieses Modells** (bewusst so gewählt, damit die Aussage ehrlich bleibt):

- **Ladevolumen gleichverteilt** über die Restroute (jedes spätere Ziel gleich wahrscheinlich) - echte Fahrpläne haben eher abnehmende Nachfrage zu weit entfernten Zielen.
- **Nur eine Bucht**, keine Umverteilung zwischen mehreren Buchten.
- **Restow-Wiedereinlagerung** nutzt dieselbe Regel wie reguläres Laden, keine eigene "Restow-Zielregel".
- **Ladereihenfolge je Hafen** ist eine plausible, aber nicht die einzig mögliche Operator-Regel (absteigend nach Ziel).
- **Kein Gewicht, keine Stabilität, keine Kranreichweite** - das ist die Domäne der Hafen-Linie-Schiffsstauplanung (`stauplanung-demo`: ein Bay mit Schwerpunkt und Gleichgewicht).
        """
    )

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Route und Bucht.** Häfen $p \in \{0, \dots, N-1\}$ in fester Reihenfolge; Bucht mit $W$ Stapeln, Höhe $H$; jeder Container hat einen Zielhafen $d > $ Ladehafen.

**Zulässige Platzierung.** Auf Stapel $s$ ist ein Container mit Ziel $d$ zulässig, wenn $s$ leer ist oder das Top-Ziel von $s \geq d$ (die Sortierung "oben = nächstes Ziel" bleibt erhalten).

**Restow.** Beim Entladen an Hafen $p$: für jeden Stapel wird jeder Container mit Ziel $> p$, der über einem Container mit Ziel $= p$ liegt, kurz umgesetzt (1 Ereignis) und danach per Platzierungsregel
neu eingelagert.

**Mindestbedarf der Regel.** $W^\ast(H) = \min\{W : \text{zielhafen-sortierte Regel erreicht über die ganze Route 0 Restows}\}$ - per linearer Suche über $W = 1, 2, \dots$ bestimmt. Eine obere Schranke für den
Bedarf des besten denkbaren Verfahrens, nicht dessen Wert.

**Statische Referenz (Patience Sorting).** Ohne Zwischenentladen, bei unbegrenzter Höhe, ist die minimale Stapelzahl gleich der Länge der längsten streng steigenden Teilfolge der tatsächlichen
Ladereihenfolge (klassisches Patience-Sorting-Resultat) - beweisbar eine obere Schranke für $W^\ast(\infty)$, da echtes Zwischenentladen nie mehr Stapel braucht als der statische Fall.

**Vergleich über Routen.** Für die sortierte Regel gegen blind auf denselben Routen $i = 1, \dots, N$ ist $\Delta_i$ die Differenz der Restows (negativ = sortiert besser); berichtet werden Mittel und
Standardfehler der gepaarten Differenz. Ein Unterschied gilt als klar, wenn $|\bar\Delta| > 2 \, \mathrm{SE}(\Delta)$.

Implementiert in `mhs_scenario.py` (Route), `mhs_rules.py` (Platzierungsregeln, Restow-Simulation), `mhs_exact.py` (Patience-Sorting-Referenz, Mindestbedarfs-Suche) und `mhs_evaluation.py`
(Stichprobe, Kurven, Urteil, Diagnose).
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zum Thema: [Seefracht optimieren](https://sebastianhanisch.net/seefracht-optimierung.html)."
)
