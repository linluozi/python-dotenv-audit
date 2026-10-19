"""Run both mutation scripts and record how many tests each mutation trips.

"Killed" alone is a binary. The number of independent tests that fail is the
real signal: a mutation caught by one test is fragile evidence, one caught by
ten is solid.
"""
import json
import pathlib
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parent
PY = sys.executable

rows = []
for script in ("evidence/run_mutations.py", "evidence/run_mutations2.py"):
    proc = subprocess.run(
        [PY, script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
    )
    for line in proc.stdout.splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            continue
        verdict, name, detail = parts[0], parts[1], parts[2]
        m = re.search(r"(\d+) failed", detail)
        rows.append(
            {
                "verdict": verdict,
                "name": name,
                "failed_tests": int(m.group(1)) if m else 0,
                "detail": detail,
                "script": script,
            }
        )

out = {
    "total": len(rows),
    "killed": sum(1 for r in rows if r["verdict"] == "KILLED"),
    "rows": sorted(rows, key=lambda r: (-r["failed_tests"], r["name"])),
}
(ROOT / "results_mutations.json").write_text(
    json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n"
)

for r in out["rows"]:
    print(f"{r['failed_tests']:2d} tests | {r['verdict']:8} | {r['name']}")
print(f"\n{out['killed']}/{out['total']} killed")
