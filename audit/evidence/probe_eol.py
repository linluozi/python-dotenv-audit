import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "src")

# Exact byte-level damage caused by universal-newline translation in rewrite().
import os
import tempfile

from dotenv.main import set_key, unset_key

tmp = tempfile.mkdtemp()
print("os.linesep =", repr(os.linesep))

cases = {
    "LF file": b"A=1\nB=2\nC=3\n",
    "CRLF file": b"A=1\r\nB=2\r\nC=3\r\n",
    "CR-only file": b"A=1\rB=2\rC=3\r",
    "CRLF multiline value": b'A="l1\r\nl2"\r\nB=2\r\n',
    "BOM + LF": b"\xef\xbb\xbfA=1\nB=2\n",
}
for name, data in cases.items():
    for op in ("set", "unset"):
        p = os.path.join(tmp, "x.env")
        with open(p, "wb") as f:
            f.write(data)
        if op == "set":
            set_key(p, "C", "9")
        else:
            unset_key(p, "A")
        after = open(p, "rb").read()
        print(f"\n{name} / {op}")
        print(f"  before={data!r}")
        print(f"  after ={after!r}")
        print(f"  LF->CRLF conversions: {data.count(b'\r\n')} -> {after.count(b'\r\n')}")
