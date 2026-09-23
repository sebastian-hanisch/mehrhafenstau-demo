"""Fehler-Einbau-Test: baut einzelne Fehler in die Module ein und prueft, ob die Tests (ohne AppTests,
die sind zu langsam fuer 20+ Mutanten) sie finden.

Aufruf (im Projektordner): ./venv/Scripts/python.exe tools/mutation_check.py [Teilstring des Dateinamens]
Jeder Mutant ersetzt genau eine Stelle; Ueberlebende sind entweder gleichwertig (kein sichtbarer
Unterschied) oder eine Luecke der Tests. Die Kopie liegt in einem temporaeren Ordner;
PYTHONDONTWRITEBYTECODE=1, damit veralteter Bytecode keine Ueberlebenden vortaeuscht; Quelltexte als
LF (Windows-Python schreibt sonst CRLF und die Zeichenketten unten finden nichts)."""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PY = sys.executable
TIMEOUT = 240

MUTANTS = [
    # mhs_rules.py
    ("mhs_rules.py", "if len(s) >= h:", "if len(s) > h:"),
    ("mhs_rules.py", "if not s or s[-1] >= dest:", "if not s or s[-1] > dest:"),
    ("mhs_rules.py", "forced.append((dest - s[-1], i))", "forced.append((s[-1] - dest, i))"),
    ("mhs_rules.py", "room = [(h - len(s), i) for i, s in enumerate(stacks) if len(s) < h]", "room = [(h - len(s), i) for i, s in enumerate(stacks) if len(s) <= h]"),
    ("mhs_rules.py", "room.sort(reverse=True)", "room.sort()"),
    ("mhs_rules.py", "if top == p:\n                    s.pop()\n                    n_unloaded += 1", "if top >= p:\n                    s.pop()\n                    n_unloaded += 1"),
    ("mhs_rules.py", "restow_events += 1", "restow_events += 0"),
    ("mhs_rules.py", "dests = sorted(loads[p], reverse=(load_order == \"desc\"))", "dests = sorted(loads[p], reverse=(load_order != \"desc\"))"),
    ("mhs_rules.py", "n_loaded += 1", "n_loaded += 0"),
    # mhs_scenario.py
    ("mhs_scenario.py", "aboard_list = [d for d in aboard_list if d != p]", "aboard_list = [d for d in aboard_list if d != p + 1]"),
    ("mhs_scenario.py", "d = p + 1 + rng.randrange(spread)", "d = p + rng.randrange(spread)"),
    ("mhs_scenario.py", "peak = max(peak, len(aboard_list))", "peak = min(peak, len(aboard_list))"),
    # mhs_exact.py
    ("mhs_exact.py", "idx = bisect.bisect_left(tops, v)", "idx = bisect.bisect_right(tops, v)"),
    ("mhs_exact.py", "seq.extend(sorted(port_loads, reverse=True))", "seq.extend(sorted(port_loads, reverse=False))"),
    ("mhs_exact.py", "for w in range(1, w_max + 1):", "for w in range(2, w_max + 1):"),
    ("mhs_exact.py", "if res[\"restows\"] == 0:\n            return w", "if res[\"restows\"] <= 0:\n            return w"),
    # mhs_evaluation.py
    ("mhs_evaluation.py", "return min(C.W_SPEC_MAX, static_bound(loads) + C.W_SLIDER_BUFFER)", "return min(C.W_SPEC_MAX, static_bound(loads))"),
    ("mhs_evaluation.py", "return sum(1 for v in vals if v == 0) / len(vals)", "return sum(1 for v in vals if v == 0) / len(results)"),
    ("mhs_evaluation.py", "kind = \"unclear\" if diff == 0 else (\"better\" if diff < 0 else \"worse\")", "kind = \"unclear\" if diff == 0 else (\"better\" if diff > 0 else \"worse\")"),
    ("mhs_evaluation.py", "kind = \"unclear\" if abs(diff) <= C.VERDICT_Z * se else (\"better\" if diff < 0 else \"worse\")", "kind = \"unclear\" if abs(diff) < C.VERDICT_Z * se else (\"better\" if diff < 0 else \"worse\")"),
    ("mhs_evaluation.py", "return statistics.stdev(d) / math.sqrt(len(d)) if len(d) > 1 else 0.0", "return statistics.stdev(d) / len(d) if len(d) > 1 else 0.0"),
    ("mhs_evaluation.py", "kind = \"too_narrow\" if gap < 0 else (\"at_limit\" if gap == 0 else \"comfortable\")", "kind = \"too_narrow\" if gap <= 0 else (\"at_limit\" if gap == 0 else \"comfortable\")"),
    # mhs_presets.py
    ("mhs_presets.py", "return max(lo, min(int(w), hi))", "return min(int(w), hi)"),
    ("mhs_presets.py", "return max(lo, hi - 1)", "return hi"),
    ("mhs_presets.py", "value = spec.lo + round((value - spec.lo) / spec.step) * spec.step", "value = spec.lo + int((value - spec.lo) / spec.step) * spec.step"),
    # mhs_stories.py
    ("mhs_stories.py", "(z_s is not None and z_s >= 0.95,", "(z_s is not None and z_s > 0.95,"),
    ("mhs_stories.py", "(z_b is not None and z_b <= 0.10,", "(z_b is not None and z_b < 0.10,"),
    ("mhs_stories.py", "(0.0 < share_infeasible <= 0.25,", "(0.0 <= share_infeasible <= 0.25,"),
    ("mhs_stories.py", "(rs is not None and rs >= 1,", "(rs is not None and rs > 1,"),
]


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else ""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="mhs_mut_"))
    for f in ROOT.glob("*.py"):
        shutil.copy(f, tmp / f.name)
    shutil.copytree(ROOT / "tests", tmp / "tests", ignore=shutil.ignore_patterns("__pycache__"))
    for f in tmp.glob("*.py"):
        f.write_bytes(f.read_bytes().replace(b"\r\n", b"\n"))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    survivors, errors, killed = [], [], 0
    for n, (name, old, new) in enumerate(MUTANTS, 1):
        if only and only not in name:
            continue
        path = tmp / name
        original = path.read_bytes().decode("utf-8")
        if original.count(old) != 1:
            errors.append((n, name, old[:60], original.count(old)))
            continue
        path.write_bytes(original.replace(old, new).encode("utf-8"))
        try:
            r = subprocess.run([PY, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", "tests", "--ignore=tests/test_app.py"], cwd=tmp, env=env, capture_output=True, text=True, timeout=TIMEOUT)
            survived = r.returncode == 0
        except subprocess.TimeoutExpired:
            survived = False                    # Endlosschleife gilt als gefunden
            print(f"[{n:3d}] Zeitueberschreitung (als gefunden gezaehlt)  {name}", flush=True)
        path.write_bytes(original.encode("utf-8"))
        if survived:
            survivors.append((n, name, old[:70], new[:70]))
            print(f"[{n:3d}] UEBERLEBT  {name}: {old[:60]!r} -> {new[:60]!r}", flush=True)
        else:
            killed += 1
            print(f"[{n:3d}] gefunden  {name}", flush=True)
    print(f"\n{killed} gefunden, {len(survivors)} ueberlebt, {len(errors)} Fehler in der Mutantenliste")
    for e in errors:
        print("  FEHLER (Stelle nicht eindeutig gefunden):", e)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
