import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "src")

import os
import tempfile

from dotenv.main import dotenv_values, set_key, unset_key

tmp = tempfile.mkdtemp()

cases = {
    "bad line before target (LF)": b"A=1\n=bad\nTARGET=2\nC=3\n",
    "bad line before target (CRLF)": b"A=1\r\n=bad\r\nTARGET=2\r\nC=3\r\n",
    "target after multiline": b'A="l1\nl2"\nTARGET=2\nC=3\n',
    "no trailing newline": b"A=1\nTARGET=2",
    "TARGET is last line": b"A=1\nTARGET=2\n",
    "TARGET first line": b"TARGET=2\nA=1\n",
    "only TARGET": b"TARGET=2\n",
}
for name, data in cases.items():
    for op in ("set", "unset"):
        p = os.path.join(tmp, "g.env")
        with open(p, "wb") as f:
            f.write(data)
        if op == "set":
            set_key(p, "TARGET", "NEW")
        else:
            unset_key(p, "TARGET")
        after = open(p, "rb").read()
        parsed = dict(dotenv_values(p, interpolate=False))
        ok = parsed.get("C") == "3" if b"C=3" in data else True
        print(f"{name:32} {op:5} -> {after!r}  parsed={parsed}  {'OK' if ok else 'BROKEN'}")
