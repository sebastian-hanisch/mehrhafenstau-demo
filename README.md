# Mehrhafen-Stauplanung: Wie viele Stapelplätze für null Restows? – Streamlit-Demo

**[→ Demo live ausprobieren](https://sebastianhanisch-mehrhafenstau-demo.streamlit.app/)**

Interaktive Fall-Demo zur **Mehrhafen-Stauplanung** einer Reederei: ein Container, der auf ein spät auslaufendes Ziel gestapelt wird, blockiert jeden darunterliegenden Container mit einem früheren Ziel –
beim Löschen muss er kurz umgesetzt werden (**Restow**), ein unproduktiver Kranhub extra. Die Demo beantwortet: **Wie viele Stapelplätze (Breite × Höhe) braucht eine Bucht, damit über die ganze Route
garantiert kein Restow entsteht – und was kostet es, knapp darunter zu bleiben?**

Teil des Portfolios für die Website „Sebastian Hanisch – Operations Research und Machine Learning", **Welle 2 der Seefracht-Linie** (Schwesterlinie zur Hafen-Linie), Nachfolger von `stapelplanung-demo`
(Hafen-Linie): dort ein Stapelblock für **einen** Hafen mit **geschätzter** Abfahrt, hier eine Bucht für die **ganze Route** mit mehreren Anlaufhäfen, bei der jedes Ziel von Anfang an **exakt bekannt** ist.
Vehikel: eine Bucht (W Stapel, Höhe H) auf einer Route mit fester Hafenreihenfolge.

## Warum dieses Problem

Ein reiner „Heuristik gegen Exakt"-Vergleich wäre bei normal bemessener Bucht **langweilig**: die zielhafen-sortierte Regel erreicht dort praktisch immer 0 Restows (100 % Nullquote im Basisfall). Die
eigentliche Frage ist deshalb nicht „welche Regel gewinnt", sondern **wie viele Stapelplätze eine Route überhaupt für garantiert null Restows braucht** – und erst an der echten Kapazitätsgrenze zeigt
sich der Unterschied zur blinden Regel deutlich (Nullquote 62,5 % gegen 0,0 % bei „Sehr knappe Bucht"). Überraschung: die klassische Lehrbuch-Faustregel für die Mindest-Stapelzahl (Patience Sorting)
ist eine sichere, aber sehr lockere obere Schranke – die echte, dynamische Mindestzahl liegt im Mittel nur bei etwa 55–80 % davon, je nach Stapelhöhe und Volumen (in der Voreinstellung 8 Häfen, H = 4, Volumen 2: 65 %; die Messreihe bei H = 6 fand 60–64 %, siehe `seefracht-planung/messreihe_mehrhafenstau/ERGEBNIS.md`).

## Modell

N Häfen in fester Reihenfolge 0…N−1. An jedem Hafen p wird zuerst entladen (Container mit Ziel = p; blockierende Container mit späterem Ziel werden kurz umgesetzt = Restow), dann geladen (neue
Container mit Ziel > p, absteigend nach Ziel). Die Bucht hat W Stapel, Höhe H; ein Container passt genau in ein Feld (kein Gewicht, keine Stabilität – das ist die Domäne der Hafen-Linie-
Schiffsstauplanung). Anders als bei der Stapelplanung der Hafen-Linie ist der Zielhafen jedes Containers von Anfang an **exakt bekannt** – die Frage ist reine Kombinatorik, kein Schätzfehler. Formal im
Expander „📐 Mathematische Formulierung" der App.

## Methodik – drei Bausteine statt einer Reglerfamilie

Anders als bei der Leercontainer-Demo (ein stetiger Regler k) sind das hier **zwei Regeln plus eine abgeleitete exakte Größe**:

- **🙈 Blind**: ignoriert Zielhäfen, verteilt nach freiem Platz (Lastausgleich) – die Kontrast-Baseline.
- **🧭 Zielhafen-sortiert**: bestfit unter Stapeln, deren Sortierung (oben = nächstes Ziel) erhalten bleibt, sonst kleinste Verletzung – die operative Regel der Hauptansicht.
- **🎯 Exakter Mindestbedarf**: kleinstes W, für das die sortierte Regel über die ganze Route 0 Restows erreicht – kein eigener Löser, dieselbe Simulation nur wiederholt aufgerufen (W bis 30
  durchprobieren, gemessen deutlich unter 1 ms auch bei der größten Route).

Die Hauptansicht zeigt nur die sortierte Regel plus eine bedingte Meldung zum Mindestbedarf; der Vergleich zu blind lebt im Expander, wo die knappen Presets ihn zeigen (siehe „Warum dieses Problem").

**Kernlogik unverändert übernommen**: `mhs_scenario.py`, `mhs_rules.py` (Platzierungsregeln, Restow-Simulation) und `mhs_exact.py` (Patience-Sorting-Referenz, Mindestbedarfs-Suche) sind direkt aus
`seefracht-planung/messreihe_mehrhafenstau/mehrhafenstau.py` übernommen – bereits gegen Brute Force und Handinstanzen verifiziert (`check.py`: 300 Zufallsfolgen, 1 Handinstanz, 60-Instanzen-
Erhaltungssatz, 60-Instanzen-Monotonie-Check, 0 Abweichungen). `mhs_rules.simulate()` bekommt zusätzlich einen `record=True`-Zweig für die Route-Ansicht (Bucht-Zustand je Hafen-Schritt) – nach
demselben Muster wie `lcr_rolling.py` in `leercontainer-demo`: die Kernlogik/Reihenfolge der Operationen ist unangetastet, nur zusätzliche Schnappschüsse werden mitgeschrieben.

## Befunde (gemessen, keine Behauptungen)

Alle Zahlen mit `python -m pytest tests/` nachvollziehbar (`test_preset_stories.py`, `test_evaluation.py`, `test_exact.py`); Population = 40 Routen (Seeds 0–39), reproduziert
`seefracht-planung/messreihe_mehrhafenstau/sweep_data.json` **exakt** (nicht nur auf Marge), da die Kernlogik unverändert übernommen wurde.

| Frage | Befund | Test |
|---|---|---|
| Ist die sortierte Regel bei komfortabler Bucht schon fast perfekt? | Ja: 6 Häfen, 6 Stapel, Höhe 4 → 100,0 % Nullquote (blind 97,5 %) – ein reiner Regelvergleich wäre hier langweilig | `test_preset_stories.py` |
| Öffnet sich an der Kapazitätsgrenze eine echte Lücke? | Ja: 10 Häfen, 3 Stapel (sehr knapp) → sortiert 62,5 % Nullquote, blind 0,0 % (nie null) | `test_preset_stories.py` |
| Wie locker ist die Patience-Sorting-Faustregel? | Die echte dynamische Mindestzahl liegt im Mittel nur bei 60,2–63,9 % der statischen Grenze (6/8/10 Häfen, H = 6, Volumen 2; bei anderen Höhen und Volumen 55–82 %), nie darüber (0/60 Verletzungen) | `test_exact.py::test_dynamic_minimum_never_exceeds_the_static_patience_bound_over_60_random_routes` |
| Hilft mehr Höhe, oder sättigt sie schnell? | 8 Häfen: nötige Stapelzahl bei H=2 → 3,83, H=4 → 3,03, ab H=6 kein weiterer Gewinn mehr (2,93 = 2,93 = 2,93 bei H=6/10/20) | `test_evaluation.py::test_height_curve_matches_direct_search_per_height` |
| Stimmt die Patience-Sorting-Formel mit Brute Force überein? | Ja: 300 Zufallsfolgen, 0 Abweichungen | `test_exact.py::test_min_piles_patience_matches_brute_force_over_300_random_sequences` |
| Wird jeder geladene Container genau einmal am richtigen Hafen entladen (Erhaltungssatz)? | Ja: 0 Verletzungen über 20+30 Zufallsinstanzen (Handinstanzen zusätzlich als Regressionstest) | `test_rules.py` |

## Ehrliche Grenzen

- **Ladevolumen gleichverteilt** über die Restroute (jedes spätere Ziel gleich wahrscheinlich) – echte Fahrpläne haben eher abnehmende Nachfrage zu weit entfernten Zielen.
- **Nur eine Bucht**, keine Umverteilung zwischen mehreren Buchten.
- **Restow-Wiedereinlagerung** nutzt dieselbe Regel wie reguläres Laden, keine eigene „Restow-Zielregel".
- **Ladereihenfolge je Hafen** ist eine plausible, aber nicht die einzig mögliche Operator-Regel (absteigend nach Ziel).
- **Kein Gewicht, keine Stabilität, keine Kranreichweite** – das ist die Domäne der Hafen-Linie-Schiffsstauplanung (`stauplanung-demo`).
- Die **Mindestbedarfs-Suche ist eine lineare Aufzählung**, kein formaler Optimalitätsbeweis außerhalb des getesteten Bereichs – als „gemessen, nicht bewiesen" gekennzeichnet, wie bei anderen
  Demo-Faustregeln.
- Die **Patience-Sorting-Grenze ist nur eine Referenz**, nicht das bewiesene Minimum der dynamischen Suche.

## Befunde und Korrekturen gegenüber dem Plan

- **Zwei getrennte Abnahmefunktionen statt einer gemeinsamen.** Der Detailplan orientiert sich am Muster der Leercontainer-Demo (eine `criteria()`-Funktion für Population UND gezeigten Seed). Bei
  einem Kosten-Aufschlag in Prozent (leercontainer-demo) ist das sinnvoll – bei Restows (ganzzahlig je Route) nicht: eine Nullquote von „62,5 %" ist auf EINER Route nicht definiert, sie wäre immer
  0 % oder 100 %. `mhs_stories.py` hat deshalb `criteria()` (Population, Nullquote-basiert, direkt aus dem Plan) UND `shown_criteria()` (die eine gezeigte Route: zeigt sie den behaupteten Kontrast
  zwischen den Regeln, z. B. „mindestens 1 Restow bei sortiert, blind mindestens 2 mehr"?).
- **Preset-Seed-Suche um einen W-Regler-Grenzen-Filter ergänzt.** Ein Seed, der `shown_criteria()` erfüllt, kann trotzdem eine eigene, zu enge Patience-Grenze haben (die W-Regler-Obergrenze hängt
  von der ROUTE ab, nicht nur von Häfen/Höhe) – dann würde `limit_dependent_state()` das Preset-W beim Laden stillschweigend herunterklemmen. `tools/tune_presets.py` prüft jetzt zusätzlich
  `lo <= preset["w"] <= hi` für den gefundenen Seed (analog zur Vorlaufzeit-Typizitätsband-Korrektur der Leercontainer-Demo).
- **Kein einziger cherry-gepickter Kontrast.** Unter den Seeds, die `shown_criteria()` erfüllen, wählt `tools/tune_presets.py` NICHT den dramatischsten Unterschied, sondern den mit
  Restows(sortiert)/Restows(blind) am nächsten am Populations-Mittel – sonst würde ein Preset den bestmöglichen statt den typischen Fall zeigen.
- **AP-0-Rechenzeit-Behauptung des Plans bestätigt, nicht korrigiert.** Der Plan nennt „deutlich unter 50 ms" für die größte Route (12 Häfen, Höhe 10); nachgemessen liegt die Mindestbedarfs-Suche dort
  bei rund 0,2–0,3 ms – sogar deutlich schneller als der Plan angenommen hatte. Der App-Text nennt vorsichtshalber weiterhin „unter 1 ms" (nicht die volle Marge).

## Tests

`python -m pytest tests/ -v` – 197 Tests, rund 12 Sekunden. Zusammensetzung:

- **Szenario** (`test_scenario.py`): Determinismus, Struktur der Ladeliste, Zielhafen stets später als Ladehafen, Randfälle (2-Hafen-Route, Ladevolumen 0).
- **Regeln** (`test_rules.py`): Handinstanzen aus `messreihe_mehrhafenstau/check.py`, Erhaltungssatz (20+10 Zufallsinstanzen), Infeasible bei Kapazitätsmangel (auch für die blinde Regel – ein
  gezielter Regressionstest gegen stillschweigendes Überfüllen über H hinaus), `record=True` liefert dieselben Restow-Zahlen wie ohne Aufzeichnung.
- **Exakter Mindestbedarf** (`test_exact.py`): `min_piles_patience` gegen Brute Force (300 Zufallsfolgen, wie `check.py`), Monotonie-Hypothese (dynamisch ≤ statisch, 60 Zufallsrouten),
  `min_stacks_for_zero_restow` gegen Direktrechnung, Randfälle (W*=1, Suchraum zu klein).
- **Auswertung** (`test_evaluation.py`): Restow-über-W-Kurve und Höhe-Kurve gegen Direktrechnung, reproduziert das Messreihen-Beispiel exakt, gepaartes Urteil (inkl. exakter Schwellenwert-Test bei
  genau zwei Standardfehlern), Diagnose in allen vier Zuständen.
- **Figuren** (`test_visualization.py`): Restow-Kurve, Höhe-Kurve, Bucht-Ansicht (Zustand je Zeitschritt, Restow-/Lade-Hervorhebung) – alle Achsen fest (`fixedrange`).
- **Regler** (`test_presets.py`): berechnete W-Grenze (Patience-Grenze + Puffer), Permalink-Parsing/-Klemmen/-Runden, Presets innerhalb ihrer eigenen Grenzen, Seed-Knopf.
- **Presets** (`test_preset_stories.py`, `test_stories.py`): Geschichte im Mittel von 40 Routen UND an der gezeigten Route; exakte Reproduktion von `sweep_data.json`; jedes einzelne Kriterium an
  künstlichen Werten, die genau an seiner Schwelle kippen.
- **PDF** (`test_pdf_export.py`): Sonderzeichen-Bereinigung (fpdf2 stürzt bei „–", „€", Emoji ab), Inhalt für jede Diagnose-Art, Randfälle (infeasible, ohne optionale Abschnitte).
- **End-to-End** (`test_app.py`, AppTest): Skelett und Footer, jedes Preset, Permalink mit berechneter W-Grenze, alle Regler an Min und Max, die bedingte Meldung in allen vier Zuständen, Urteil in
  allen Zuständen, Vergleichstabelle, Exakt-Tab, PDF, Texte.

Zusätzlich ein Fehler-Einbau-Test (`tools/mutation_check.py`, 29 Mutanten über `mhs_rules`, `mhs_scenario`, `mhs_exact`, `mhs_evaluation`, `mhs_presets`, `mhs_stories`): **27 gefunden, 2 überlebt, 0
Fehler in der Mutantenliste.** Beide Überlebenden sind gleichwertig (kein sichtbarer Unterschied im Verhalten):

- `min_stacks_for_zero_restow`: `restows == 0` → `restows <= 0` überlebt, weil eine Restow-Zahl (Zählung von Ereignissen) nie negativ werden kann – beide Vergleiche sind identisch.
- `parse_setting`: die Rundung auf die Schrittweite (`round` → `int`) überlebt, weil **kein** Regler dieser Demo eine Schrittweite größer 1 hat (der Code-Zweig ist aktuell unerreichbar, aus dem
  Portfolio-Muster übernommen für den Fall eines künftigen gestuften Reglers).

## Dateistruktur

| Datei | Inhalt | Herkunft |
|---|---|---|
| `app.py` | Streamlit-Hauptablauf: Presets, Sidebar, Hauptansicht, Kernabschnitt, Bausteine im Vergleich, Texte | neu |
| `mhs_constants.py` | Regler-Grenzen, `PRESETS`, Bausteine, Farben, feste Modellparameter | neu |
| `mhs_presets.py` | `SETTING_SPECS`, Permalink (mit W-Begrenzung), Presets, Seed-Knopf | Muster `lcr_presets.py` |
| `mhs_scenario.py` | Route, Ladeliste je Hafen (`make_scenario`) | `messreihe_mehrhafenstau/mehrhafenstau.py`, unverändert |
| `mhs_rules.py` | Blind- und sortierte Platzierungsregel, Restow-Simulation | `messreihe_mehrhafenstau/mehrhafenstau.py`, um `record=True` erweitert |
| `mhs_exact.py` | Patience-Sorting-Referenz, Mindestbedarfs-Suche | `messreihe_mehrhafenstau/mehrhafenstau.py`, unverändert |
| `mhs_evaluation.py` | Stichprobe, Restow-über-W-Kurve, Höhe-Kurve, gepaartes Urteil, Diagnose | Muster `lcr_evaluation.py` |
| `mhs_visualization.py` | Bucht-Ansicht (Stapel-Säulen, Zeitschritt), Restow-Kurve, Höhe-Kurve (alle Achsen fest) | Muster `lcr_visualization.py`, `stk_visualization.py` |
| `mhs_ui_panel.py` | Kennzahlen (2×2), Bucht-Ansicht mit Zeitschrittregler, Baustein-Tabs | Muster `lcr_ui_panel.py` |
| `mhs_pdf_export.py` | PDF-Export (`fpdf2`, Sonderzeichen-Bereinigung) | Muster `lcr_pdf_export.py` |
| `mhs_stories.py` | Abnahmekriterien der Presets (Population UND gezeigte Route) | Muster `lcr_stories.py` |
| `tools/tune_presets.py`, `tools/PRESET_SWEEP.md` | Preset-Abstimmung und ihr Bericht | neu |
| `tools/mutation_check.py` | Fehler-Einbau-Test | neu |
| `tests/` | siehe oben | neu |

## Bewusst nicht umgesetzt (mögliche Erweiterungen)

- **Gewichtete/abnehmende Zielverteilung** statt gleichverteiltem Ladevolumen über die Restroute.
- **Mehrere Buchten** mit Umverteilungsmöglichkeit zwischen ihnen.
- **Dedizierte Restow-Zielregel** (z. B. bevorzugt in die eigene Ausgangsposition zurück) statt derselben Regel wie reguläres Laden.
- **Alternative Ladereihenfolgen je Hafen** (nur absteigend nach Ziel getestet).
- **Gewicht/Stabilität** – bewusst der Hafen-Linie-Schiffsstauplanung (`stauplanung-demo`) überlassen.

## Lokal ausführen

```bash
pip install -r requirements-dev.txt
streamlit run app.py
```

Tests: `python -m pytest tests/ -v`. Preset-Abstimmung: `python tools/tune_presets.py population|seeds`. Fehler-Einbau: `python tools/mutation_check.py`.

---

Gebaut mit Streamlit, Plotly und fpdf2.

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zum Thema: [Seefracht optimieren](https://sebastianhanisch.net/seefracht-optimierung.html).
