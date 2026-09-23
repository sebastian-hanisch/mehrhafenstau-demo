# Preset-Abstimmung

`python tools/tune_presets.py population` prueft die fuenf Presets gegen die Abnahmekriterien aus
`mhs_stories.py`, jeweils ueber `POPULATION_INSTANCES=40` Routen (Seeds 0-39) - dieselbe Stichprobengroesse
wie `seefracht-planung/messreihe_mehrhafenstau/sweep.py` (`range(40)`).

## Ergebnis (Population, Seeds 0-39)

| Preset | sortiert Nullquote | blind Nullquote | Kriterium |
|---|---|---|---|
| Komfortable Bucht | 100,0 % | 97,5 % | beide erfuellt (>= 95 % / >= 90 %) |
| Knappe Bucht | 95,0 % | 2,5 % | beide erfuellt (>= 90 % / <= 10 %) |
| Sehr knappe Bucht | 62,5 % | 0,0 % | beide erfuellt (40-80 % / <= 5 %) |
| Kurze Route, knapp | 82,5 % | 12,5 % | beide erfuellt (70-90 % / <= 20 %) |
| Niedrige Bucht | 94,6 % (unter den machbaren) | 40,5 % | beide erfuellt (>= 90 % / Anteil infeasible 7,5 % in (0, 25]) |

Diese Zahlen reproduzieren `messreihe_mehrhafenstau/sweep_data.json` **exakt** (nicht nur auf Marge) -
`mhs_scenario.py`, `mhs_rules.py` und `mhs_exact.py` sind unveraendert aus
`messreihe_mehrhafenstau/mehrhafenstau.py` uebernommen, siehe `test_preset_stories.py::
test_the_population_reproduces_the_pre_measurement_sweep_data_exactly`.

## Seed-Suche (gezeigte Route je Preset)

`python tools/tune_presets.py seeds` sucht ab Seed 40 (ausserhalb der Population) einen Seed, der

1. `mhs_stories.shown_criteria()` erfuellt (die gezeigte Route zeigt den behaupteten Kontrast zwischen
   den Regeln - siehe `mhs_stories.py`-Docstring: die Population-Nullquote ist auf EINER Route nicht
   definiert, deshalb eine eigene, count-basierte Kriterienfunktion fuer den gezeigten Fall), und
2. dessen eigene, live berechnete W-Regler-Obergrenze (`mhs_presets.w_bounds`, Patience-Grenze der
   ROUTE plus Puffer) das Preset-W ueberhaupt zulaesst - die Patience-Grenze haengt vom Seed ab, ein
   sonst passender Seed kann eine zu enge eigene Obergrenze haben.

Unter den Treffern wird NICHT der dramatischste Kontrast gewaehlt (Cherry-Picking des schoensten
Einzelfalls), sondern der Seed, dessen Restows(sortiert)/Restows(blind) am naechsten am Populations-
Mittel (`mean_restows`) liegen.

| Preset | Seed | Restows sortiert (gezeigt) | Restows blind (gezeigt) |
|---|---|---|---|
| Komfortable Bucht | 42 | 0 | 0 |
| Knappe Bucht | 41 | 0 | 3 |
| Sehr knappe Bucht | 47 | 1 | 5 |
| Kurze Route, knapp | 43 | 0 | 2 |
| Niedrige Bucht | 45 | 0 | 1 |

Alle fuenf Seeds bestehen weiterhin `mhs_stories.criteria()` (Population) UND `shown_criteria()`
(gezeigte Route), siehe `tests/test_preset_stories.py`.
