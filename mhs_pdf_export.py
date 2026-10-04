"""PDF-Export des Ergebnisses (fpdf2, Helvetica-Kernschrift, nur Text und Tabellen).

Die Kernschriften kennen nur Latin-1: Umlaute sind erlaubt, aber "–" (Gedankenstrich), "−" (Minuszeichen),
"€", Emoji usw. lassen fpdf2 abstuerzen. Deshalb laeuft jeder Text durch pdf_text()."""
import time

import mhs_constants as C
import mhs_evaluation as E

_REPLACEMENTS = {
    "–": "-", "—": "-", "‑": "-", "−": "-", "≥": ">=", "≤": "<=", "→": "->", "≈": "ca.", "€": "EUR", "±": "+-",
    "·": "-", "“": '"', "”": '"', "„": '"', "‘": "'", "’": "'", "⚠️": "(!)", "⚠": "(!)", "✅": "", "ℹ️": "",
    "🙈": "", "🧭": "", "🎯": "", "📊": "", "🚢": "", "📐": "",
}


def pdf_text(text):
    """Text fuer die Helvetica-Kernschrift: bekannte Sonderzeichen ersetzen, den Rest Latin-1-sicher machen."""
    for old, new in _REPLACEMENTS.items():
        text = text.replace(old, new)
    return text.encode("latin-1", "replace").decode("latin-1")


def diagnosis_text(diag):
    if diag.kind == "infeasible":
        return "Diese Bucht-Größe reicht für den Verkehr dieser Route nicht (Kapazität W x H zu klein) - unabhängig von der Regel."
    if diag.kind == "too_narrow":
        return f"Bucht zu knapp: mindestens W={diag.exact_w} nötig für garantiert 0 Restows (eingestellt: {diag.exact_w + diag.gap})."
    if diag.kind == "at_limit":
        return f"Genau am Limit (W={diag.exact_w}): kein Puffer, jede zusätzliche Unregelmäßigkeit führt zu Restows."
    if diag.kind == "comfortable":
        return f"Komfortabel: {diag.gap} Stapel mehr als das exakte Minimum (W*={diag.exact_w}) - kein Handlungsbedarf."
    return "Kein Mindestbedarf innerhalb der Sicherheitsgrenze der Suche gefunden."


def verdict_text(v):
    if v.n == 0:
        return "Kein Vergleich möglich: keine Route ist für beide Regeln machbar."
    if v.kind == "better":
        return f"Zielhafen-sortiert gegen blind: im Mittel {abs(v.diff):.2f} weniger Restows je Route (Differenz {v.diff:+.2f}, Standardfehler {v.se:.2f}, n={v.n})."
    if v.kind == "worse":
        return f"Zielhafen-sortiert gegen blind: im Mittel {abs(v.diff):.2f} mehr Restows je Route (Differenz {v.diff:+.2f}, Standardfehler {v.se:.2f}, n={v.n})."
    return f"Kein klarer Unterschied zwischen sortiert und blind (Differenz {v.diff:+.2f} Restows, Standardfehler {v.se:.2f}, n={v.n})."


def generate_mhs_pdf(n_ports, w, h, volume, seed, restows_sortiert, restows_blind, diag, static_bound_value,
                     dyn_min, curve=None, sample_results=None, verdict=None, compress=True):
    """Ergebnis der aktuellen Einstellung als PDF: Route, Restows je Regel, Diagnose, Patience-Grenze
    gegen echtes Minimum, Restow-ueber-W-Kurve, Urteil ueber die Stichprobe, Hinweise zum Modell."""
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    pdf = FPDF()
    pdf.set_compression(compress)
    pdf.add_page()

    def line(text, height=7, width=0):
        pdf.cell(width, height, pdf_text(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def heading(text):
        pdf.set_font("Helvetica", "B", 12)
        line(text, 8)
        pdf.set_font("Helvetica", "", 10)

    def pairs(rows):
        for label, value in rows:
            pdf.cell(75, 6, pdf_text(label), border=0)
            line(value, 6)

    def table(headers, widths, rows):
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(230, 230, 230)
        for header, width in zip(headers, widths):
            pdf.cell(width, 7, pdf_text(header), border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.ln(7)
        pdf.set_font("Helvetica", "", 9)
        for row in rows:
            for value, width in zip(row, widths):
                pdf.cell(width, 7, pdf_text(str(value)), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.ln(7)

    def keep_together(height):
        if pdf.get_y() + height > pdf.h - pdf.b_margin:
            pdf.add_page()

    def note(text, size=8):
        pdf.set_font("Helvetica", "I", size)
        pdf.set_text_color(110, 110, 110)
        pdf.multi_cell(0, 5, pdf_text(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)

    pdf.set_font("Helvetica", "B", 16)
    line("Mehrhafen-Stauplanung: Wie viele Stapelplätze für null Restows?", 10)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(120, 120, 120)
    line(f"Erstellt: {time.strftime('%d.%m.%Y %H:%M')}  -  sebastianhanisch.net", 6)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    heading("Route und Bucht")
    pairs([("Häfen", str(n_ports)), ("Stapel (Breite W) / Höhe H", f"{w} / {h}"), ("Ladevolumen je Hafen", str(volume)), ("Seed", str(seed))])
    pdf.ln(3)

    heading("Zusammenfassung")
    note(diagnosis_text(diag), 9)
    pairs([("Restows (sortiert)", "nicht machbar" if restows_sortiert is None else str(restows_sortiert)),
           ("Restows (blind)", "nicht machbar" if restows_blind is None else str(restows_blind)),
           ("Echtes Minimum W*", "-" if dyn_min is None else str(dyn_min)),
           ("Patience-Grenze (statisch, locker)", str(static_bound_value))])
    pdf.ln(3)

    if curve is not None:
        keep_together(90)
        heading("Restows über der Stapelzahl W (Regel sortiert)")
        rows = [[w_i, "nicht machbar" if r is None else r] for w_i, r in enumerate(curve[C.RULE_SORTIERT], start=1)]
        table(["W", "Restows"], [30, 60], rows)
        note(f"Echtes Minimum W*={dyn_min}, Patience-Sorting-Faustregel={static_bound_value} (sicher, aber locker - Zwischenentladen schafft real zusätzliche Kapazität, die die Formel ignoriert).")
        pdf.ln(3)

    if sample_results is not None and verdict is not None:
        keep_together(60)
        heading("Urteil über die Stichprobe")
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, pdf_text("- " + verdict_text(verdict)), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        note(f"Basis: {len(sample_results)} Routen (Seeds 0-{len(sample_results) - 1}, nicht der eingestellte Seed) mit den eingestellten Werten. Klar heißt: Unterschied größer als zwei Standardfehler der gepaarten Differenz.")
        pdf.ln(3)

    keep_together(70)
    heading("Hinweise zum Modell")
    pdf.set_font("Helvetica", "", 9)
    for text in [
        "Route mit fester Reihenfolge; an jedem Hafen wird zuerst entladen (blockierende Container werden kurz umgesetzt = Restow), dann geladen. Der Zielhafen jedes Containers ist von Anfang an exakt bekannt.",
        "Zielhafen-sortierte Regel: bestfit unter Stapeln, deren Sortierung (oben = nächstes Ziel) erhalten bleibt; sonst kleinste Verletzung. Blinde Regel: reiner Lastausgleich, ignoriert Ziele.",
        "Exakter Mindestbedarf: kleinstes W mit 0 Restows für die sortierte Regel, per wiederholter Simulation gesucht (kein separater Löser).",
        "Patience-Sorting-Grenze ist eine sichere, aber SEHR lockere obere Schranke - die echte dynamische Mindestzahl liegt im Mittel bei nur etwa 55 bis 80 % davon (je nach Stapelhöhe und Volumen; in der Voreinstellung 65 %).",
        "Nur eine Bucht, kein Gewicht/keine Stabilität (das ist die Domäne der Hafen-Linie-Schiffsstauplanung). Ladevolumen gleichverteilt über die Restroute, nicht abnehmend zu fernen Zielen.",
    ]:
        pdf.multi_cell(0, 5, pdf_text("- " + text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    return bytes(pdf.output())
