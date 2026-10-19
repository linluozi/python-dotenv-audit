import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "src")

from dotenv import load_dotenv

cases = [
    ("only bare keys", "A\nB\n", {}),
    ("bare + empty value", "A\nB=\n", {}),
    ("bare + real value", "A\nB=1\n", {}),
    ("empty file", "", {}),
    ("only comment", "# hi\n", {}),
    ("all skipped by no-override", "A=1\n", {"A": "existing"}),
]
for label, text, env in cases:
    saved = dict(os.environ)
    os.environ.clear()
    os.environ.update(env)
    try:
        r = load_dotenv(stream=io.StringIO(text), override=False)
        print(f"  {label:28} -> return={r!s:5} environ={dict(os.environ)!r}")
    finally:
        os.environ.clear()
        os.environ.update(saved)
