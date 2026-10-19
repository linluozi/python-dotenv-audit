import os
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

py = sys.executable
tmp = tempfile.mkdtemp()
p = os.path.join(tmp, "cli.env")
open(p, "w", encoding="utf-8").write("")

env = dict(os.environ, PYTHONPATH="src", PYTHONUTF8="0", PYTHONIOENCODING="utf-8")

print("=== round trip under a GBK locale (PYTHONUTF8=0) ===")
for args in (["set", "GREETING", "你好"], ["get", "GREETING"], ["list"]):
    r = subprocess.run([py, "-m", "dotenv", "-f", p, *args],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    print(f"  $ dotenv {' '.join(args)} -> rc={r.returncode} out={r.stdout.strip()!r}")
    if r.returncode:
        print("     err:", (r.stderr.strip().splitlines() or [""])[-1])
print("  file bytes:", open(p, "rb").read())

print("\n=== undecodable bytes give a clean error, not a traceback ===")
bad = os.path.join(tmp, "bad.env")
open(bad, "wb").write(b"A=\xff\xfe\n")
r = subprocess.run([py, "-m", "dotenv", "-f", bad, "list"],
                   capture_output=True, text=True, encoding="utf-8",
                   errors="replace", env=env)
print(f"  rc={r.returncode} out={r.stdout.strip()!r}")
print(f"  err={r.stderr.strip()!r}")
print(f"  traceback present: {'Traceback' in r.stderr}")
