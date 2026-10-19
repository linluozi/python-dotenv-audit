import io
import logging
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "src")

import dotenv.main as m
from dotenv.parser import parse_stream

records = []


class H(logging.Handler):
    def emit(self, r):
        records.append(r.getMessage())


lg = logging.getLogger("dotenv.main")
lg.addHandler(H())
lg.setLevel(logging.WARNING)

BODY = ["A=1", "=bad1", "B=2", "a: bad2", "C=3"]
for label, nl in [("LF", "\n"), ("CRLF", "\r\n"), ("CR", "\r")]:
    text = nl.join(BODY) + nl
    records.clear()
    list(m.with_warn_for_invalid_lines(parse_stream(io.StringIO(text))))
    print(f"{label:5} warnings={records}   (expected lines 2 and 4)")
    for b in parse_stream(io.StringIO(text)):
        print(f"      line={b.original.line} err={b.error} orig={b.original.string!r}")
