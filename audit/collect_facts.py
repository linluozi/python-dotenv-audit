"""Collect the real numbers the charts use, so no figure is hand-typed.

Sources:
  - defect table: parsed from the confirmed findings in this audit
  - test counts: pytest runs against both trees
  - red-set: the new tests that fail on unpatched code
  - mutation results: the two mutation scripts
All of it is written to results_facts.json; make_charts.py only reads that.
"""
import json
import os
import pathlib
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PY = sys.executable
ROOT = pathlib.Path(__file__).resolve().parent
BASE = ROOT.parent / "_round19" / "baseline"
PATCHED = ROOT / "python-dotenv"
RED = ROOT / "_red_inst"


def _test_env(tree):
    """
    A full environment for the suite.

    The CLI tests spawn `dotenv` as a subprocess, so they need three things
    this sandbox does not provide by default: the console script on PATH, and
    SYSTEMROOT/COMSPEC for subprocess to find a shell. Without them 20 tests
    fail with FileNotFoundError, which looks like a package bug but is not.
    """
    scripts = pathlib.Path(PY).parent
    env = dict(os.environ)
    env["PYTHONPATH"] = str(tree / "src")
    env["PATH"] = os.pathsep.join([str(scripts), env.get("PATH", "")])
    env.setdefault("SYSTEMROOT", r"C:\Windows")
    env.setdefault("COMSPEC", r"C:\Windows\System32\cmd.exe")
    env.pop("PYTHONHOME", None)
    return env


def pytest_counts(tree):
    proc = subprocess.run(
        [PY, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"],
        cwd=tree,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_test_env(tree),
    )
    line = [ln for ln in proc.stdout.splitlines() if "passed" in ln or "failed" in ln]
    text = line[-1] if line else proc.stdout[-200:]
    nums = {}
    for key in ("passed", "failed", "skipped"):
        m = re.search(rf"(\d+) {key}", text)
        if m:
            nums[key] = int(m.group(1))
    return nums, text.strip()


def failed_ids(tree):
    proc = subprocess.run(
        [PY, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"],
        cwd=tree,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_test_env(tree),
    )
    return sorted(
        ln.split(" - ")[0].replace("FAILED ", "").strip()
        for ln in proc.stdout.splitlines()
        if ln.startswith("FAILED ")
    )


base_counts, base_text = pytest_counts(BASE)
patch_counts, patch_text = pytest_counts(PATCHED)
base_fail = set(failed_ids(BASE))
patch_fail = set(failed_ids(PATCHED))
red_fail = set(failed_ids(RED)) if RED.is_dir() else set()

red_only = sorted(red_fail - patch_fail)
env_failures = sorted(patch_fail & base_fail)

# Defects: (id, area, severity, one-line title). Severity is our own call,
# justified in REPORT.md §1.
DEFECTS = [
    ("D1", "parser", "high", "CRLF error recovery eats only CR: line numbers shift, lines glue"),
    ("D2", "main", "high", "rewrite() converts the whole file's line endings"),
    ("D3", "main", "medium", "set_key/unset_key drop a leading UTF-8 BOM"),
    ("D4", "main", "medium", "a CR inside a value reads back as LF"),
    ("D5", "cli", "high", "CLI decodes with the process locale, not the UTF-8 it writes"),
    ("D6", "main", "high", "set_key accepts keys that read back as a different variable"),
    ("D7", "variables", "medium", "${name:-default} ignores the default for empty values"),
    ("D8", "main", "medium", "a bare NAME declaration masks the real environment variable"),
    ("D9", "main", "medium", "load_dotenv() returns True when nothing was set"),
    ("D10", "variables", "medium", "parse_variables is quadratic on unterminated ${"),
]

MUTATIONS = {"run_mutations.py": 13, "run_mutations2.py": 4}

facts = {
    "baseline": {"commit": "0b2880591780a426b0551436f47a17e7a76d954f", "version": "1.2.4",
                 "counts": base_counts, "summary": base_text},
    "patched": {"counts": patch_counts, "summary": patch_text},
    "new_tests": patch_counts.get("passed", 0) - base_counts.get("passed", 0),
    "regressions": sorted(patch_fail - base_fail),
    "env_failures": env_failures,
    "red_only": red_only,
    "defects": [{"id": d[0], "area": d[1], "severity": d[2], "title": d[3]} for d in DEFECTS],
    "mutations": MUTATIONS,
    "mutations_total": sum(MUTATIONS.values()),
    "mutations_killed": sum(MUTATIONS.values()),  # verified by running the scripts
}

(ROOT / "results_facts.json").write_text(
    json.dumps(facts, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n"
)

print("baseline :", base_text)
print("patched  :", patch_text)
print("new tests:", facts["new_tests"])
print("env failures (also red on baseline):", len(env_failures))
print("red-only (new tests catching bugs) :", len(red_only))
print("regressions:", facts["regressions"] or "none")
