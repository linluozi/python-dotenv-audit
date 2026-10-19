"""Mutation run #2: the line-terminator heuristic and remaining fixes."""
import os
import pathlib
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = pathlib.Path(__file__).resolve().parent


def _project_root() -> pathlib.Path:
    """Find the project root (sibling or nested `python-dotenv/`)."""
    for cand in (HERE, HERE.parent, HERE.parent.parent):
        for base in (cand, cand / "python-dotenv"):
            if (base / "src" / "dotenv" / "__init__.py").is_file():
                return base
    raise SystemExit(f"cannot locate the project root from {HERE}")


ROOT = _project_root()
sys.path.insert(0, str(ROOT / "src"))
SRC, MUT = ROOT, ROOT.parent / "mut_run"
PY = sys.executable

ANCHOR = '    if text.endswith("\\r\\n"):\n'

MUTATIONS = [
    ("new line always LF", ANCHOR, '    return "\\n"\n' + ANCHOR),
    ("new line always CRLF", ANCHOR, '    return "\\r\\n"\n' + ANCHOR),
    ("new line uses os.linesep", ANCHOR, "    return os.linesep\n" + ANCHOR),
    (
        "line terminator detection removed (fallback only)",
        ANCHOR,
        '    if text.endswith("\\n"):\n'
        '        return "\\n"\n'
        '    if text.endswith("\\r"):\n'
        '        return "\\r"\n',
    ),
]

SELECTOR = "terminator or line_endings or bom or carriage_returns"

for label, old, new in MUTATIONS:
    if MUT.exists():
        shutil.rmtree(MUT)
    shutil.copytree(SRC, MUT, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    target = MUT / "src/dotenv/main.py"
    text = target.read_text(encoding="utf-8")
    if old not in text:
        print(f"NOT FOUND | {label}")
        continue
    target.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
    proc = subprocess.run(
        [PY, "-m", "pytest", "tests", "-q", "-k", SELECTOR, "-p", "no:cacheprovider"],
        cwd=MUT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONPATH": str(MUT / "src")},
    )
    tail = [ln for ln in proc.stdout.splitlines() if "passed" in ln or "failed" in ln]
    print(
        f"{'KILLED' if proc.returncode else 'SURVIVED':9} | {label:44} | "
        f"{tail[-1] if tail else ''}"
    )

if MUT.exists():
    shutil.rmtree(MUT)
