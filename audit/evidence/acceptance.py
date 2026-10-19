"""End-to-end acceptance: real objects, both directions, before vs after."""
import io
import os
import pathlib
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PY = sys.executable
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
WORK = ROOT
BASE = ROOT.parent / "baseline"
if not (BASE / "src" / "dotenv" / "__init__.py").is_file():
    BASE = None  # no pristine copy shipped; the patched column is still produced


def run(tree, code):
    proc = subprocess.run(
        [PY, "-c", code],
        cwd=tree,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONPATH": str(tree / "src"), "PYTHONIOENCODING": "utf-8"},
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


CASES = {
    "CRLF file, set_key keeps CRLF": r'''
import tempfile, os
from dotenv import set_key
p = os.path.join(tempfile.mkdtemp(), ".env")
open(p, "wb").write(b"A=1\r\nB=2\r\n")
set_key(p, "C", "9")
print(repr(open(p, "rb").read()))
''',
    "BOM kept through set_key": r'''
import tempfile, os
from dotenv import set_key
p = os.path.join(tempfile.mkdtemp(), ".env")
open(p, "wb").write(b"\xef\xbb\xbfA=1\n")
set_key(p, "B", "2")
print(repr(open(p, "rb").read()))
''',
    "CR in value survives round-trip": r'''
import tempfile, os
from dotenv import set_key, get_key
p = os.path.join(tempfile.mkdtemp(), ".env")
set_key(p, "K", "a\rb")
print(repr(get_key(p, "K")))
''',
    "invalid statement on CRLF keeps line numbers": r'''
import io, logging, sys
from dotenv.parser import parse_stream
from dotenv.main import with_warn_for_invalid_lines
seen = []
class H(logging.Handler):
    def emit(self, r): seen.append(r.getMessage())
lg = logging.getLogger("dotenv.main"); lg.addHandler(H()); lg.setLevel(logging.WARNING)
text = "a=1\r\n=bad\r\nb=2\r\na: bad\r\nc=3\r\n"
list(with_warn_for_invalid_lines(parse_stream(io.StringIO(text))))
sys.stdout.write(str(seen))
''',
    "empty value uses ${x:-d} default": r'''
import io
from dotenv import dotenv_values
print(dict(dotenv_values(stream=io.StringIO("b=\na=${b:-d}\n"))))
''',
    "bare key does not mask environment": r'''
import io, os
from dotenv import dotenv_values
os.environ["MASKVAR"] = "fromenv"
print(dict(dotenv_values(stream=io.StringIO("MASKVAR\nB=${MASKVAR}\n"))))
''',
    "load_dotenv return for valueless-only": r'''
import io
from dotenv import load_dotenv
print(load_dotenv(stream=io.StringIO("A\nB\n")))
''',
    "set_key rejects 'a=b' key": r'''
import tempfile, os
from dotenv import set_key
p = os.path.join(tempfile.mkdtemp(), ".env")
try:
    set_key(p, "a=b", "x")
    print("accepted ->", repr(open(p, encoding="utf-8").read()))
except ValueError as e:
    print("ValueError:", e)
''',
    "16KB hostile value parse time": r'''
import sys, time
sys.path.insert(0, "src")
from dotenv.variables import parse_variables
s = "${" * 8000
t0 = time.perf_counter(); list(parse_variables(s)); dt = time.perf_counter() - t0
print(f"{dt*1000:.1f} ms")
''',
}

if BASE is None:
    print(f"{'case':46} | patched")
    print("-" * 110)
    for label, code in CASES.items():
        rc_w, out_w, err_w = run(WORK, code)
        w = out_w if rc_w == 0 else f"rc={rc_w} {(err_w.splitlines() or [''])[-1][:40]}"
        print(f"{label:46} | {w[:60]}")
else:
    print(f"{'case':46} | {'baseline':34} | patched")
    print("-" * 120)
    for label, code in CASES.items():
        rc_b, out_b, err_b = run(BASE, code)
        rc_w, out_w, err_w = run(WORK, code)
        b = out_b if rc_b == 0 else f"rc={rc_b} {(err_b.splitlines() or [''])[-1][:40]}"
        w = out_w if rc_w == 0 else f"rc={rc_w} {(err_w.splitlines() or [''])[-1][:40]}"
        print(f"{label:46} | {b[:52]:52} | {w[:60]}")
