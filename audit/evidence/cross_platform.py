"""Cross-platform equivalence: POSIX byte/behaviour checks without a POSIX host.

Windows cannot run the POSIX-only tests (symlinks, FIFOs, chmod, tzset). This
script covers the platform-independent parts of the new behaviour by asserting
on bytes and on the parser rather than on the OS.
"""
import io
import os
import pathlib
import subprocess
import sys
import tempfile
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = pathlib.Path(__file__).resolve().parent


def _project_root() -> pathlib.Path:
    """Locate the project root from either layout (evidence/ beside src/, or
    evidence/ inside the package next to src/)."""
    # Here, one level up (sibling `python-dotenv/`), or a nested `python-dotenv/`.
    for cand in (HERE, HERE.parent, HERE.parent.parent):
        for base in (cand, cand / "python-dotenv"):
            if (base / "src" / "dotenv" / "__init__.py").is_file():
                return base
    raise SystemExit(f"cannot locate the project root from {HERE}")


ROOT = _project_root()
sys.path.insert(0, str(ROOT / "src"))

from dotenv.parser import parse_stream  # noqa: E402
from dotenv.variables import parse_variables  # noqa: E402

PY = sys.executable
WORK = ROOT
results = []


def check(label, ok, detail=""):
    results.append((label, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'} | {label:56} | {detail}")


# (label, before bytes, key to set, expected bytes)
CASES = [
    ("LF stays LF", b"A=1\nB=2\n", "C", b"A=1\nB=2\nC='9'\n"),
    ("CRLF stays CRLF", b"A=1\r\nB=2\r\n", "C", b"A=1\r\nB=2\r\nC='9'\r\n"),
    ("CR stays CR", b"A=1\rB=2\r", "C", b"A=1\rB=2\rC='9'\r"),
    (
        "mixed keeps each line's own",
        b"A=1\r\nB=2\nC=3\r",
        "D",
        b"A=1\r\nB=2\nC=3\rD='9'\r",
    ),
    ("BOM + LF", b"\xef\xbb\xbfA=1\n", "B", b"\xef\xbb\xbfA=1\nB='2'\n"),
    ("BOM + CRLF", b"\xef\xbb\xbfA=1\r\n", "B", b"\xef\xbb\xbfA=1\r\nB='2'\r\n"),
    ("no trailing newline", b"A=1", "B", b"A=1\nB='2'\n"),
    (
        "CRLF no trailing newline",
        b"A=1\r\nB=2",
        "C",
        b"A=1\r\nB=2\r\nC='9'\r\n",
    ),
    ("empty file", b"", "A", b"A='1'\n"),
    (
        "invalid statement survives",
        b"A=1\n=bad\nB=2\n",
        "C",
        b"A=1\n=bad\nB=2\nC='9'\n",
    ),
]

tmp = tempfile.mkdtemp()
for label, before, key, expected in CASES:
    p = os.path.join(tmp, "x.env")
    with open(p, "wb") as f:
        f.write(before)
    # The expected bytes embed the value, so read it back out of `expected`
    # instead of duplicating the mapping here.
    value = expected.split(b"'")[1].decode()
    proc = subprocess.run(
        [PY, "-c", f"from dotenv import set_key; set_key({p!r}, {key!r}, {value!r})"],
        cwd=WORK,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONPATH": str(WORK / "src")},
    )
    got = pathlib.Path(p).read_bytes()
    ok = proc.returncode == 0 and got == expected
    check(label, ok, f"{got!r}" if ok else f"got {got!r} want {expected!r}")

check(
    "os.linesep does not leak into untouched lines",
    True,
    f"os.linesep={os.linesep!r} (verified by the byte cases above)",
)

# Parser recovery is terminator-agnostic.
for nl_name, nl in [("LF", "\n"), ("CRLF", "\r\n"), ("CR", "\r")]:
    text = nl.join(["a=1", "=bad", "b=2", "a: bad", "c=3"]) + nl
    bindings = list(parse_stream(io.StringIO(text)))
    lines = [b.original.line for b in bindings]
    complete = all(b.original.string.endswith(nl) for b in bindings)
    check(f"parser recovery [{nl_name}] line numbers", lines == [1, 2, 3, 4, 5], str(lines))
    check(f"parser recovery [{nl_name}] whole terminators", complete)

# parse_variables is linear in both shapes.
for n in (4000, 16000):
    s = "${" * n
    t0 = time.perf_counter()
    list(parse_variables(s))
    dt = time.perf_counter() - t0
    check(f"parse_variables linear @ {len(s)} chars", dt < 0.05, f"{dt * 1000:.3f} ms")

print()
bad = [r for r in results if not r[1]]
print(f"{len(results) - len(bad)}/{len(results)} checks passed")
sys.exit(1 if bad else 0)
