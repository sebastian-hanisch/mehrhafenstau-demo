"""Abnahmekriterien der Presets (Detailplan plan_mehrhafenstau.html, Abschnitt 7): welche Geschichte
erzaehlt jedes Beispielszenario, und woran erkennt man, dass sie traegt?

Einzige Quelle fuer `tools/tune_presets.py` (Abstimmung) und `tests/test_preset_stories.py` (Abnahme).
Zwei getrennte Kriterien-Funktionen, weil Restows je Route ganzzahlig sind (0, 1, 2, ...) - anders als
z. B. ein Kosten-Aufschlag in Prozent gibt es auf EINER Route keine "Nullquote von 62,5 %", die waere
immer 0 % oder 100 %:

- `criteria()`: Population-Kriterien ueber die NULLQUOTE einer Regel, gemessen ueber viele Routen
  (typischerweise POPULATION_INSTANCES) - direkt aus dem Detailplan Abschnitt 7 uebernommen.
- `shown_criteria()`: Kriterien an der EINEN gezeigten Route - zeigt sie den behaupteten Kontrast
  zwischen den Regeln, nicht die Population-Rate (die auf einer Route nicht definiert ist)?"""
import mhs_constants as C
import mhs_evaluation as E


def _pct(v):
    return "–" if v is None else f"{v * 100:.1f} %"


def criteria(name, results):
    """Population-Kriterien ueber `results` (Liste von RouteResult, ueblicherweise viele Routen).
    Rueckgabe: Liste (erfuellt, Text)."""
    z_s = E.zero_share(results, C.RULE_SORTIERT)
    z_b = E.zero_share(results, C.RULE_BLIND)
    if name == "Komfortable Bucht":
        return [(z_s is not None and z_s >= 0.95, f"sortiert Nullquote >= 95 %: {_pct(z_s)}"),
                (z_b is not None and z_b >= 0.90, f"blind Nullquote >= 90 %: {_pct(z_b)}")]
    if name == "Knappe Bucht":
        return [(z_s is not None and z_s >= 0.90, f"sortiert Nullquote >= 90 %: {_pct(z_s)}"),
                (z_b is not None and z_b <= 0.10, f"blind Nullquote <= 10 %: {_pct(z_b)}")]
    if name == "Sehr knappe Bucht":
        return [(z_s is not None and 0.40 <= z_s <= 0.80, f"sortiert Nullquote 40-80 %: {_pct(z_s)}"),
                (z_b is not None and z_b <= 0.05, f"blind Nullquote <= 5 %: {_pct(z_b)}")]
    if name == "Kurze Route, knapp":
        return [(z_s is not None and 0.70 <= z_s <= 0.90, f"sortiert Nullquote 70-90 %: {_pct(z_s)}"),
                (z_b is not None and z_b <= 0.20, f"blind Nullquote <= 20 %: {_pct(z_b)}")]
    if name == "Niedrige Bucht":
        infeasible_n = E.infeasible_count(results, C.RULE_SORTIERT)
        share_infeasible = infeasible_n / len(results) if results else 0.0
        return [(z_s is not None and z_s >= 0.90, f"sortiert Nullquote (unter den machbaren) >= 90 %: {_pct(z_s)}"),
                (0.0 < share_infeasible <= 0.25, f"Anteil nicht machbarer Stichprobenrouten in (0 %, 25 %]: {share_infeasible * 100:.1f} %")]
    raise KeyError(name)


def shown_criteria(name, result):
    """Kriterien an der EINEN gezeigten Route (result = ein RouteResult): zeigt sie den behaupteten
    Kontrast zwischen sortiert und blind? Rueckgabe: Liste (erfuellt, Text)."""
    rs, rb = result.restows[C.RULE_SORTIERT], result.restows[C.RULE_BLIND]
    if name == "Komfortable Bucht":
        return [(rs == 0, f"sortiert 0 Restows auf der gezeigten Route: {rs}"),
                (rb is not None, f"blind auf der gezeigten Route machbar: {rb}")]
    if name == "Knappe Bucht":
        return [(rs == 0, f"sortiert 0 Restows auf der gezeigten Route: {rs}"),
                (rb is not None and rb >= 2, f"blind sichtbar schlechter (>= 2 Restows): {rb}")]
    if name == "Sehr knappe Bucht":
        return [(rs is not None and rs >= 1, f"sortiert zeigt einen echten Restow (>= 1): {rs}"),
                (rb is not None and rs is not None and rb >= rs + 2, f"blind deutlich schlechter (>= sortiert + 2): sortiert={rs}, blind={rb}")]
    if name == "Kurze Route, knapp":
        return [(rs is not None, f"sortiert auf der gezeigten Route machbar: {rs}"),
                (rb is not None and rs is not None and rb >= rs + 2, f"blind deutlich schlechter (>= sortiert + 2): sortiert={rs}, blind={rb}")]
    if name == "Niedrige Bucht":
        return [(rs is not None and rs <= 1, f"sortiert auf der gezeigten Route machbar und fast perfekt (<= 1 Restow): {rs}"),
                (rb is not None and rs is not None and rb > rs, f"blind schlechter als sortiert: sortiert={rs}, blind={rb}")]
    raise KeyError(name)
