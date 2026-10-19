"""Measure parse_variables on both arms, one process per (arm, size).

Rule: each (arm, workload) runs in its own process, interleaved across rounds,
and we report the median of per-round times plus the min/max spread.
"""
import json
import pathlib
import statistics
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PY = sys.executable
ROOT = pathlib.Path(__file__).resolve().parent
ARMS = {
    "baseline": ROOT.parent / "_round19" / "baseline",
    "patched": ROOT / "python-dotenv",
}
SIZES = [1000, 2000, 4000, 8000]  # -> 2 KB .. 16 KB of "${" repeated
ROUNDS = 3

CHILD = r"""
import sys, time, json
sys.path.insert(0, sys.argv[1])
from dotenv.variables import parse_variables
n = int(sys.argv[2])
text = "${" * n
# warm up once, then measure the median of 3 in-process repeats
list(parse_variables(text))
samples = []
for _ in range(3):
    t0 = time.perf_counter()
    list(parse_variables(text))
    samples.append(time.perf_counter() - t0)
print(json.dumps({"chars": len(text), "median_ms": sorted(samples)[1] * 1000}))
"""

raw = {arm: {n: [] for n in SIZES} for arm in ARMS}
for rnd in range(ROUNDS):
    for n in SIZES:
        # interleave arms within each size so drift hits both equally
        for arm, tree in ARMS.items():
            proc = subprocess.run(
                [PY, "-c", CHILD, str(tree / "src"), str(n)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            if proc.returncode != 0:
                print(f"FAIL {arm} n={n}: {proc.stderr[-300:]}")
                continue
            raw[arm][n].append(json.loads(proc.stdout)["median_ms"])
    print(f"round {rnd + 1}/{ROUNDS} done", flush=True)

out = {"sizes": SIZES, "chars": {}, "arms": {}}
for n in SIZES:
    out["chars"][n] = 2 * n
for arm, per_n in raw.items():
    out["arms"][arm] = {
        "median": [statistics.median(per_n[n]) for n in SIZES],
        "min": [min(per_n[n]) for n in SIZES],
        "max": [max(per_n[n]) for n in SIZES],
        "samples": [per_n[n] for n in SIZES],
    }

(ROOT / "results_perf.json").write_text(
    json.dumps(out, indent=2), encoding="utf-8", newline="\n"
)

print()
print(f"{'chars':>8} | {'baseline med':>13} | {'patched med':>12} | {'ratio':>7}")
for i, n in enumerate(SIZES):
    b = out["arms"]["baseline"]["median"][i]
    p = out["arms"]["patched"]["median"][i]
    print(f"{out['chars'][n]:>8} | {b:>11.1f} ms | {p:>10.3f} ms | {b / p:>6.0f}x")

# Growth factor: 4x input should cost ~16x if quadratic, ~4x if linear.
for arm in ARMS:
    med = out["arms"][arm]["median"]
    print(f"{arm:9} growth 2KB->8KB (4x input): {med[2] / med[0]:.1f}x")
