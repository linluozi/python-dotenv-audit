import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "src")

from dotenv import load_dotenv

print("=== NUL in value: is the environment partially mutated before the crash? ===")
with open(os.devnull, "w") as _:
    pass
os.environ.pop("OK1", None)
os.environ.pop("OK2", None)
os.environ.pop("NULLY", None)
try:
    load_dotenv(stream=io.StringIO("OK1=a\nNULLY=x\x00y\nOK2=b\n"))
except Exception as exc:
    print(f"  raised {type(exc).__name__}: {exc}")
print("  OK1 set:", "OK1" in os.environ, "| OK2 set:", "OK2" in os.environ)
print("  -> partial application:", ("OK1" in os.environ) and ("OK2" not in os.environ))

print()
print("=== quadratic expansion reachable through load_dotenv? ===")
import time

os.environ.pop("HOSTILE", None)
payload = "HOSTILE=" + "${" * 4000 + "\n"
t0 = time.perf_counter()
load_dotenv(stream=io.StringIO(payload))
print(f"  8000-char hostile value took {time.perf_counter()-t0:.2f}s")

print()
print("=== CLI `run` already pins utf-8 but `list`/`get` do not ===")
import inspect

import dotenv.cli as c

src = inspect.getsource(c.stream_file)
print("  stream_file open():", [ln.strip() for ln in src.splitlines() if "open(" in ln])
