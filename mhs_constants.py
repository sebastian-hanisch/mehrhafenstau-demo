"""Konstanten der Mehrhafen-Stauplanungs-Demo (Welle 2 Seefracht-Linie).

Modell und Zahlen aus messreihe_mehrhafenstau/ (siehe seefracht-planung/plan_mehrhafenstau.html,
ERGEBNIS.md). Presets werden mit tools/tune_presets.py gegen die Abnahmekriterien in mhs_stories.py
geprueft; die Seeds hier sind das Ergebnis dieser Abstimmung (siehe tools/PRESET_SWEEP.md)."""

# --- Regler --------------------------------------------------------------------------------------------
N_PORTS_RANGE, N_PORTS_DEFAULT = (4, 12), 8
H_RANGE, H_DEFAULT = (2, 10), 4
VOLUME_RANGE, VOLUME_DEFAULT = (1, 4), 2
SEED_RANGE, SEED_DEFAULT = (0, 9999), 0
# W (Stapelzahl) hat eine BERECHNETE Obergrenze (Patience-Grenze der aktuellen Route + Puffer); die
# Spezifikationsgrenze hier ist die weiteste denkbare, der Regler in der App begrenzt enger, siehe
# mhs_presets.w_bounds(). W_SPEC_MAX ist zugleich die Obergrenze der Slider-Spezifikation fuer den
# Permalink (garantiert nie kleiner als jede erreichbare Obergrenze bei den Regler-Bereichen oben).
W_MIN = 1
W_SPEC_MAX = 40
# Hartes Sicherheitsnetz der Mindestbedarfs-Suche (kein Zeitlimit noetig, siehe ERGEBNIS.md: die Suche
# braucht auch bei der groessten Route deutlich unter 1 ms, gemessen in AP 0).
W_SEARCH_MAX = 30
# Zusaetzlicher Spielraum ueber der Patience-Grenze, damit der Regler auch eine "komfortable" Bucht
# zeigen kann, nicht nur knapp bis zur Faustregel.
W_SLIDER_BUFFER = 2

# --- Auswertung -----------------------------------------------------------------------------------------
SAMPLE_INSTANCES = 30        # Instanzen je Urteil/Kurve im Kernabschnitt (Plan Abschnitt 6)
POPULATION_INSTANCES = 40    # Instanzen fuer die Preset-Abnahme (Plan Abschnitt 7; reproduziert die
                              # Stichprobengroesse von messreihe_mehrhafenstau/sweep.py range(40))
VERDICT_Z = 2.0               # klar ab mehr als VERDICT_Z Standardfehlern der gepaarten Differenz

# --- Bausteine (Plan Abschnitt 3): zwei Regeln plus eine abgeleitete exakte Groesse --------------------
RULE_BLIND, RULE_SORTIERT = "blind", "sortiert"
RULE_KEYS = (RULE_BLIND, RULE_SORTIERT)
RULE_LABELS = {RULE_BLIND: "🙈 Blind", RULE_SORTIERT: "🧭 Zielhafen-sortiert"}
RULE_SHORT = {RULE_BLIND: "Blind", RULE_SORTIERT: "Zielhafen-sortiert"}
RULE_DESCRIPTIONS = {
    RULE_BLIND: "Ignoriert die Zielhaefen und verteilt nach freiem Platz (Lastausgleich). Die Kontrast-Baseline: "
                "zeigt, was ohne Zielhafen-Bewusstsein passiert.",
    RULE_SORTIERT: "Bevorzugt einen Stapel, dessen oberster Container ein Ziel groesser oder gleich dem neuen hat "
                   "(die Sortierung oben = naechstes Ziel bleibt erhalten), bestfit = knappster passender Top. Kein "
                   "solcher Stapel frei -> kleinste Sortierverletzung. Die operative Regel der Hauptansicht.",
}
EXACT_TAB_KEY = "exakt"
EXACT_TAB_LABEL = "🎯 Exakter Mindestbedarf"
COMPARISON_TAB_LABEL = "📊 Vergleich"

# --- Darstellung ----------------------------------------------------------------------------------------
RULE_COLORS = {RULE_BLIND: "#8a94a3", RULE_SORTIERT: "#2a6fb0"}
STATIC_BOUND_COLOR = "#9aa5b4"    # Patience-Grenze (grau gestrichelt)
DYN_MIN_COLOR = "#2e7d4f"          # echtes Minimum (gruen gestrichelt)
CURRENT_W_COLOR = "#c0392b"
MARKER_LINE_COLOR = "#808895"

# Bucht-Blockdarstellung: Farbe = Zielhafen (dunkel = naechster Hafen auf der Route, hell = spaeter)
BAY_COLOR_SOON = (31, 58, 95)
BAY_COLOR_LATE = (208, 224, 240)
BAY_STACK_BG = "#f0f2f5"
BAY_STACK_LINE = "#c9d1db"
RESTOW_COLOR = "#e8850c"          # gerade umgesetzt (Restow) in diesem Schritt
LOADED_COLOR = "#2e7d4f"          # gerade neu geladen in diesem Schritt

BAY_FIGURE_TIER_PX = 38
BAY_FIGURE_BASE_PX = 70
CHART_HEIGHT = 380

# --- Presets (Plan Abschnitt 7; Seeds >= POPULATION_INSTANCES, per tools/tune_presets.py abgestimmt) ----
PRESETS = {
    "Komfortable Bucht": dict(n_ports=6, w=6, h=4, volume=2, seed=42),
    "Knappe Bucht": dict(n_ports=10, w=4, h=4, volume=2, seed=41),
    "Sehr knappe Bucht": dict(n_ports=10, w=3, h=4, volume=2, seed=47),
    "Kurze Route, knapp": dict(n_ports=8, w=3, h=4, volume=2, seed=43),
    "Niedrige Bucht": dict(n_ports=8, w=4, h=2, volume=2, seed=45),
}
