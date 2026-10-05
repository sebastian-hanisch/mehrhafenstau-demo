"""Plotly-Figuren der Mehrhafen-Stauplanung: Bucht-Ansicht (Stapel-Saeulen je Hafen-Schritt), Restows-
ueber-W-Kurve (mit Patience-Grenze und echtem Minimum), Hoehe-Kurve.

Konventionen des Portfolios: Achsen `fixedrange` (Touch-Scrollen), Vorlage plotly_white, Marker-Linien
in mittlerem Grau, Ueberschriften stehen als Markdown UEBER dem Diagramm. Plotly wird erst in den
Funktionen importiert, damit die reine Rechnung ohne Plotly testbar bleibt."""
import mhs_constants as C

LEGEND_BOTTOM = dict(orientation="h", yref="container", yanchor="bottom", y=0.0, x=0)

STACK_W = 1.0
STACK_GAP = 0.3
BOX_PAD = 0.06
BOX_H = 0.88


def _lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _blend(f):
    a, b = C.BAY_COLOR_SOON, C.BAY_COLOR_LATE
    return tuple(int(round(a[i] + f * (b[i] - a[i]))) for i in range(3))


# ---------------------------------------------------------------------------------------------------
# Restows-ueber-W-Kurve (Kernabschnitt und Vergleichs-Tab: dieselbe Figur)
# ---------------------------------------------------------------------------------------------------
def restow_curve_figure(curve, static_bound_value, dyn_min, current_w):
    """curve: {'blind': [...], 'sortiert': [...]} Restows je W=1..len; None wo infeasible. Gestrichelte
    graue Marke bei der Patience-Grenze, gestrichelte gruene Marke beim Mindestbedarf der Regel, eingestelltes W
    als roter Punkt auf der sortierten Kurve."""
    import plotly.graph_objects as go

    ws = list(range(1, len(curve[C.RULE_SORTIERT]) + 1))
    fig = go.Figure()
    for rule in C.RULE_KEYS:
        pts = [(w, v) for w, v in zip(ws, curve[rule]) if v is not None]
        if not pts:
            continue
        xs = [w for w, _ in pts]
        ys = [v for _, v in pts]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers", name=C.RULE_LABELS[rule],
                                 line=dict(color=C.RULE_COLORS[rule], width=2.5), marker=dict(size=6),
                                 hovertemplate=f"<b>{C.RULE_LABELS[rule]}</b><br>W=%{{x}}<br>%{{y}} Restows<extra></extra>"))
    if static_bound_value is not None and ws and static_bound_value <= ws[-1]:
        fig.add_vline(x=static_bound_value, line=dict(color=C.STATIC_BOUND_COLOR, width=2, dash="dot"),
                      annotation_text="Patience-Grenze (statisch)", annotation_position="top", annotation_font=dict(size=11))
    if dyn_min is not None:
        fig.add_vline(x=dyn_min, line=dict(color=C.DYN_MIN_COLOR, width=2, dash="dash"),
                      annotation_text="Mindestbedarf der Regel", annotation_position="bottom",
                      annotation_font=dict(size=11, color=C.DYN_MIN_COLOR))
    sorted_curve = curve[C.RULE_SORTIERT]
    cur_y = sorted_curve[current_w - 1] if 0 < current_w <= len(sorted_curve) else None
    if cur_y is not None:
        fig.add_trace(go.Scatter(x=[current_w], y=[cur_y], mode="markers",
                                 marker=dict(size=13, color=C.CURRENT_W_COLOR, line=dict(width=2, color="white")),
                                 name="eingestellt", hovertemplate="eingestellt: W=%{x}<br>%{y} Restows<extra></extra>"))
    fig.update_layout(template="plotly_white", height=C.CHART_HEIGHT, margin=dict(t=30, b=45), legend=LEGEND_BOTTOM,
                      hovermode="closest", xaxis_title="Stapelzahl W", yaxis_title="Restows")
    fig.update_xaxes(tickmode="array", tickvals=ws)
    fig.update_yaxes(rangemode="tozero")
    return _lock_axes(fig)


# ---------------------------------------------------------------------------------------------------
# Hoehe-Kurve
# ---------------------------------------------------------------------------------------------------
def height_curve_figure(h_curve, current_h):
    """h_curve: {H: mittlere noetige Stapelzahl}. Zeigt den Saettigungspunkt (Plan Abschnitt 6)."""
    import plotly.graph_objects as go

    hs = sorted(v for v in h_curve if h_curve[v] is not None)
    ys = [h_curve[h] for h in hs]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hs, y=ys, mode="lines+markers", line=dict(color=C.RULE_COLORS[C.RULE_SORTIERT], width=2.5),
                             marker=dict(size=7), hovertemplate="H=%{x}<br>%{y:.2f} Stapel im Mittel<extra></extra>"))
    if current_h in hs:
        idx = hs.index(current_h)
        fig.add_trace(go.Scatter(x=[current_h], y=[ys[idx]], mode="markers",
                                 marker=dict(size=13, color=C.CURRENT_W_COLOR, line=dict(width=2, color="white")),
                                 name="eingestellt", hovertemplate="eingestellt: H=%{x}<br>%{y:.2f}<extra></extra>"))
    fig.update_layout(template="plotly_white", height=C.CHART_HEIGHT, margin=dict(t=25, b=45), showlegend=False,
                      xaxis_title="Bucht-Höhe H", yaxis_title="Mittlere nötige Stapelzahl")
    fig.update_xaxes(tickmode="array", tickvals=hs)
    fig.update_yaxes(rangemode="tozero")
    return _lock_axes(fig)


# ---------------------------------------------------------------------------------------------------
# Bucht-Ansicht (Stapel als Saeulen, Zeitschritt)
# ---------------------------------------------------------------------------------------------------
def bay_title(label, port_index, n_ports, restows_so_far):
    if port_index is None:
        return f"<b>{label}</b><br><sub>Vor Hafen 1 · Restows bisher: {restows_so_far}</sub>"
    return f"<b>{label}</b><br><sub>Nach Hafen {port_index + 1} von {n_ports} · Restows bisher: {restows_so_far}</sub>"


def state_at(steps, w, index):
    """Bucht-Zustand nach `index` bearbeiteten Haefen (0 = leer, vor Hafen 1). `steps` kommt aus
    mhs_rules.simulate(..., record=True)["steps"]. Gibt (port_index, stacks, restowed, loaded) zurueck;
    port_index ist None fuer index=0."""
    if index == 0:
        return None, tuple(() for _ in range(w)), (), ()
    step = steps[index - 1]
    return step["port"], step["stacks"], step["restowed"], step["loaded"]


def cumulative_restows(steps, index):
    return sum(len(s["restowed"]) for s in steps[:index])


def bay_figure(stacks, h, n_ports, title, restowed_positions=(), loaded_positions=()):
    """stacks: Tupel von Tupeln (unten->oben) von Zielhafen-Indizes. restowed_positions/
    loaded_positions: (Stapelindex, Zielhafen)-Paare, die in diesem Schritt neu hinzugekommen sind
    (Rand-Hervorhebung: orange = Restow, gruen = neu geladen)."""
    import plotly.graph_objects as go

    w = len(stacks)
    fig = go.Figure()
    for i in range(w):
        x0 = i * (STACK_W + STACK_GAP)
        fig.add_shape(type="rect", x0=x0, x1=x0 + STACK_W, y0=0, y1=h, layer="below",
                      fillcolor=C.BAY_STACK_BG, line=dict(color=C.BAY_STACK_LINE, width=1))

    denom = max(1, n_ports - 1)
    xs, ys, texts, colors, hovers = [], [], [], [], []
    for i, s in enumerate(stacks):
        x0 = i * (STACK_W + STACK_GAP)
        restow_remaining = [d for (j, d) in restowed_positions if j == i]
        loaded_remaining = [d for (j, d) in loaded_positions if j == i]
        for t, c in enumerate(s):
            border = None
            if c in restow_remaining:
                border = C.RESTOW_COLOR
                restow_remaining.remove(c)
                state = "gerade umgesetzt (Restow)"
            elif c in loaded_remaining:
                border = C.LOADED_COLOR
                loaded_remaining.remove(c)
                state = "gerade geladen"
            else:
                state = ""
            f = c / denom
            r, g, b = _blend(f)
            fig.add_shape(type="rect", x0=x0 + BOX_PAD, x1=x0 + STACK_W - BOX_PAD, y0=t + (1 - BOX_H) / 2,
                          y1=t + (1 - BOX_H) / 2 + BOX_H, fillcolor=f"rgb({r},{g},{b})", layer="below",
                          line=dict(color=border, width=3) if border else dict(width=0))
            xs.append(x0 + STACK_W / 2)
            ys.append(t + 0.5)
            texts.append(str(c + 1))
            colors.append("white" if f < 0.5 else "#1c2430")
            hovers.append(f"<b>Zielhafen {c + 1}</b>{' · ' + state if state else ''}<br>Stapel {i + 1}, Ebene {t + 1}")

    fig.add_trace(go.Scatter(x=xs, y=ys, mode="text", text=texts, textfont=dict(size=12, color=colors),
                             hovertext=hovers, hoverinfo="text", showlegend=False))
    total_w = w * STACK_W + max(0, w - 1) * STACK_GAP
    fig.update_layout(title=dict(text=title, font=dict(size=14), x=0.02), template="plotly_white", showlegend=False,
                      height=C.BAY_FIGURE_BASE_PX + 14 + h * C.BAY_FIGURE_TIER_PX, margin=dict(l=8, r=8, t=58, b=8))
    fig.update_xaxes(range=[-0.1, total_w + 0.1], visible=False)
    fig.update_yaxes(range=[-0.05, h + 0.05], visible=False)
    return _lock_axes(fig)
