"""Wiederverwendbares Panel: Kennzahlen (2 x 2), Bucht-Ansicht mit Zeitschrittregler, Baustein-Tabs
(Blind, Zielhafen-sortiert, Exakter Mindestbedarf, Vergleich) - Plan Abschnitt 6/8."""
import pandas as pd
import streamlit as st

import mhs_constants as C
import mhs_evaluation as E
import mhs_rules as R
import mhs_visualization as V


def fmt_restows(v):
    return "nicht machbar" if v is None else str(v)


def fmt_gap(gap):
    return "–" if gap is None else f"{gap:+d}"


def render_metrics(columns, restows_sortiert, restows_blind, gap, zero_share_value):
    """Vier Kennzahlen (Plan Abschnitt 6): Restows (sortiert), Restows (blind), Abstand zum
    Mindestbedarf (eingestelltes W minus Mindestbedarf der Regel), Nullquote (Stichprobe, Regel sortiert)."""
    m = columns
    m[0].metric("Restows (sortiert)", fmt_restows(restows_sortiert), help="Restows der zielhafen-sortierten Regel auf der gezeigten Route bei der eingestellten Bucht-Größe.")
    m[1].metric("Restows (blind)", fmt_restows(restows_blind), help="Restows der blinden Regel (Kontrast-Baseline) auf derselben Route.")
    m[2].metric("Abstand zum Mindestbedarf", fmt_gap(gap), help="Eingestelltes W minus Mindestbedarf W* der sortierten Regel bei dieser Höhe/Route; negativ = zu knapp, 0 = genau am Limit.")
    zero_txt = "–" if zero_share_value is None else f"{zero_share_value * 100:.1f} %"
    m[3].metric("Nullquote (Stichprobe)", zero_txt, help=f"Anteil restow-freier Routen (Regel sortiert) unter {C.SAMPLE_INSTANCES} Stichprobenrouten mit denselben Einstellungen (nicht der gezeigte Seed).")


def render_bay_step(prefix, steps, w, h, n_ports, rule_label):
    """Zeitschrittregler (0 = vor dem ersten Hafen) + Bucht-Saeulen (kein Abspielen - eine bewusste
    Ansicht je Schritt, wie bei den Hafen-Demos)."""
    key = f"{prefix}_step_slider"
    if key in st.session_state:
        st.session_state[key] = min(st.session_state[key], n_ports)
    step_idx = st.slider("Hafen-Schritt", 0, n_ports, key=key, help="0 = vor dem ersten Hafen; zeigt den Buchtzustand, nachdem dieser Hafen entladen und beladen wurde.")
    port_index, stacks, restowed, loaded = V.state_at(steps, w, step_idx)
    restows_so_far = V.cumulative_restows(steps, step_idx)
    title = V.bay_title(rule_label, port_index, n_ports, restows_so_far)
    st.plotly_chart(V.bay_figure(stacks, h, n_ports, title, restowed, loaded), width="stretch", key=f"{prefix}_bay_chart_{step_idx}")
    st.caption("Farbe = Zielhafen (dunkel = nächster Hafen auf der Route, hell = später), Zahl = Zielhafen. Oranger Rand = gerade umgesetzt (Restow), grüner Rand = gerade neu geladen.")


def render_rule_panel(prefix, rule, loads, w, h, n_ports):
    """Beschreibung, Restows-Kennzahl und Bucht-Ansicht einer Regel (je Tab im Vergleich-Expander)."""
    st.markdown(C.RULE_DESCRIPTIONS[rule])
    try:
        result = R.simulate(loads, w, h, rule, record=True)
        st.metric("Restows (diese Route)", result["restows"])
        render_bay_step(prefix, result["steps"], w, h, n_ports, C.RULE_LABELS[rule])
    except R.Infeasible:
        st.warning("⚠️ Diese Bucht-Größe reicht für den Verkehr dieser Route nicht (Kapazität W x H zu klein) - unabhängig von der Regel.")


def render_exact_panel(loads, h, n_ports, curve, static_bound_value, dyn_min, current_w):
    """Suchtabelle W -> Restows (Regel sortiert), Patience-Grenze als lockere Referenz, Mindestbedarf der Regel."""
    st.markdown(
        "Sucht das kleinste W, ab dem die **zielhafen-sortierte Regel** über die ganze Route **0 Restows** erreicht - kein eigener Löser, dieselbe Simulation nur wiederholt für "
        "W = 1, 2, 3, ... Die klassische Patience-Sorting-Formel (längste streng steigende Teilfolge der Ladereihenfolge) ist eine sichere, aber SEHR lockere obere Schranke: sie "
        "ignoriert, dass echtes Zwischenentladen unterwegs Platz freigibt."
    )
    if dyn_min is not None:
        st.success(f"✅ Mindestbedarf der sortierten Regel auf dieser Route (Höhe {h}): **W = {dyn_min}**. Lehrbuch-Faustregel (Patience Sorting): W = {static_bound_value} - {static_bound_value - dyn_min} Stapel mehr, als die Regel braucht.")
    else:
        st.warning("⚠️ Kein W bis zur Sicherheitsgrenze der Suche erreicht 0 Restows bei dieser Höhe.")
    rows = []
    sorted_curve = curve[C.RULE_SORTIERT]
    for w, restows in enumerate(sorted_curve, start=1):
        rows.append({"W": w, "Restows (sortiert)": "nicht machbar" if restows is None else str(restows), "0 Restows?": "✅" if restows == 0 else ("—" if restows is None else "")})
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.plotly_chart(V.restow_curve_figure(curve, static_bound_value, dyn_min, current_w), width="stretch", key="exact_tab_curve_chart")


def render_comparison_tab(results, curve, static_bound_value, dyn_min, current_w, mean_gap):
    rows = []
    for rule in C.RULE_KEYS:
        mean_r = E.mean_restows(results, rule)
        zshare = E.zero_share(results, rule)
        infeasible_n = E.infeasible_count(results, rule)
        rows.append({
            "Regel": C.RULE_LABELS[rule],
            "Restows (Mittel, Stichprobe)": "–" if mean_r is None else f"{mean_r:.2f}",
            "Nullquote": "–" if zshare is None else f"{zshare * 100:.1f} %",
            "nicht machbar": f"{infeasible_n}/{len(results)}",
            "Abstand zum Mindestbedarf": "–" if (rule != C.RULE_SORTIERT or mean_gap is None) else f"{mean_gap:+.2f}",
        })
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.plotly_chart(V.restow_curve_figure(curve, static_bound_value, dyn_min, current_w), width="stretch", key="comparison_tab_curve_chart")
    st.caption("Eine Route, zwei Regeln: der Unterschied ist an einer komfortabel bemessenen Bucht klein - er zeigt sich erst an der knappen Kapazitätsgrenze (Presets \"Knapp\"/\"Sehr knapp\").")
