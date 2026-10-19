import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "src")

from dotenv import dotenv_values, load_dotenv

print("=== bare key must not mask the environment ===")
for text in ["MASKVAR\nB=${MASKVAR}\n", "MASKVAR\nB=${MASKVAR:-d}\n"]:
    for override in (True, False):
        env = {"MASKVAR": "fromenv"}
        old = os.environ.get("MASKVAR")
        os.environ["MASKVAR"] = "fromenv"
        try:
            if override:
                r = dict(dotenv_values(stream=io.StringIO(text)))
            else:
                os.environ.pop("B", None)
                load_dotenv(stream=io.StringIO(text), override=False)
                r = {"B": os.environ.get("B")}
        finally:
            if old is None:
                os.environ.pop("MASKVAR", None)
            else:
                os.environ["MASKVAR"] = old
            os.environ.pop("B", None)
        print(f"  {text!r:28} override={override!s:5} -> {r!r}")

print("\n=== ordinary precedence still holds ===")
cases = [
    ({}, "b=c\na=${b}\n"),
    ({}, "a=b\na=c\nd=${a}\n"),
    ({"b": "c"}, "b=d\na=${b}\n"),
    ({}, "a\nb=${a:-d}\n"),
]
for env, text in cases:
    saved = dict(os.environ)
    os.environ.update(env)
    try:
        print(f"  env={env!r:12} {text!r:22} -> {dict(dotenv_values(stream=io.StringIO(text)))!r}")
    finally:
        os.environ.clear()
        os.environ.update(saved)
