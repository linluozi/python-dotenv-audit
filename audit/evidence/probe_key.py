import os
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "src")

from dotenv.main import dotenv_values, set_key

tmp = tempfile.mkdtemp()
keys = ["GOOD", "A B", "A=B", "A#B", "'A'", "A'", "A\nB", " A", "A\tB", "", "中文键", "A-B", "A.B", "1"]
for key in keys:
    p = os.path.join(tmp, "k.env")
    open(p, "w", encoding="utf-8", newline="").write("BASE=1\n")
    try:
        set_key(p, key, "v")
    except ValueError as exc:
        print(f"  key={key!r:9} REJECTED: {exc}")
        continue
    raw = open(p, "rb").read()
    back = dict(dotenv_values(p, interpolate=False))
    ok = back.get(key) == "v"
    print(f"  key={key!r:9} file={raw!r:24} read_back={back!r} {'OK' if ok else 'LOST'}")
