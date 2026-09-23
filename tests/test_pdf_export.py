"""PDF-Export (mhs_pdf_export): Sonderzeichen-Bereinigung (fpdf2 stuerzt bei "-", "EUR"-Zeichen, Emoji
ab), Inhalt fuer jede Diagnose-Art, Randfaelle."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import mhs_constants as C  # noqa: E402
import mhs_evaluation as E  # noqa: E402
from mhs_pdf_export import diagnosis_text, generate_mhs_pdf, pdf_text, verdict_text  # noqa: E402
from mhs_scenario import make_scenario  # noqa: E402


def test_pdf_text_replaces_characters_that_crash_fpdf2_core_fonts():
    assert "-" in pdf_text("Gedankenstrich – hier")
    assert "–" not in pdf_text("Gedankenstrich – hier")
    assert "EUR" in pdf_text("Preis: 5€")
    assert "€" not in pdf_text("Preis: 5€")
    assert pdf_text("Emoji 🚢🎯") == pdf_text(pdf_text("Emoji 🚢🎯"))  # idempotent, kein Crash


def test_pdf_text_is_latin1_safe_after_replacement():
    pdf_text("ä ö ü ß – € ≥ ≤ → ≈ ± · „" '"' "'" "⚠️ ✅ ℹ️ 🙈 🧭 🎯").encode("latin-1")


def test_diagnosis_text_covers_every_kind():
    for kind, exact_w, gap in [("infeasible", None, None), ("too_narrow", 3, -1), ("at_limit", 3, 0), ("comfortable", 3, 2), ("unknown", None, None)]:
        diag = E.Diagnosis(kind, gap, exact_w)
        text = diagnosis_text(diag)
        assert isinstance(text, str) and len(text) > 0
        pdf_text(text).encode("latin-1")


def test_verdict_text_covers_better_worse_unclear_and_empty():
    class _V:
        def __init__(self, kind, diff, se, n):
            self.kind, self.diff, self.se, self.n = kind, diff, se, n

    for v in (_V("better", -2.0, 0.5, 20), _V("worse", 2.0, 0.5, 20), _V("unclear", 0.1, 0.5, 20), _V("unclear", 0.0, 0.0, 0)):
        text = verdict_text(v)
        assert isinstance(text, str) and len(text) > 0


def test_generate_pdf_produces_nonempty_bytes_for_a_typical_route():
    loads, _ = make_scenario(8, 2, 0)
    static_bound_value = E.static_bound(loads)
    dyn_min = E.exact_min(loads, 4)
    diag = E.diagnose(5, dyn_min, 0)
    curve = E.restow_curve(loads, 4, 8)
    sample = E.sample(E.Params(8, 4, 2, 5), 5)
    v = E.verdict(sample)
    pdf_bytes = generate_mhs_pdf(8, 5, 4, 2, 0, 0, 3, diag, static_bound_value, dyn_min, curve=curve, sample_results=sample, verdict=v)
    assert isinstance(pdf_bytes, bytes) and len(pdf_bytes) > 500
    assert pdf_bytes[:4] == b"%PDF"


def test_generate_pdf_handles_infeasible_route_without_crashing():
    loads, _ = make_scenario(10, 4, 0)
    diag = E.Diagnosis("infeasible", None, None)
    pdf_bytes = generate_mhs_pdf(10, 1, 1, 4, 0, None, None, diag, static_bound_value=6, dyn_min=None)
    assert pdf_bytes[:4] == b"%PDF"


def test_generate_pdf_without_optional_curve_and_sample_sections():
    diag = E.Diagnosis("comfortable", 2, 3)
    pdf_bytes = generate_mhs_pdf(8, 5, 4, 2, 0, 0, 3, diag, static_bound_value=4, dyn_min=3)
    assert pdf_bytes[:4] == b"%PDF"
