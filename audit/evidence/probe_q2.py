import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "src")

from dotenv.variables import parse_variables


def t(text):
    t0 = time.perf_counter()
    list(parse_variables(text))
    return time.perf_counter() - t0


shapes = {
    "A: ${ xN, no brace at all": lambda n: "${" * n,
    "B: ${a xN then one }": lambda n: "${a" * n + "}",
    "C: ${ xN then one }": lambda n: "${" * n + "}",
    "D: ${a xN then :}": lambda n: "${a" * n + ":-}",
    "E: ${a: xN": lambda n: "${a:" * n,
    "F: ${a:- xN then }": lambda n: "${a:-" * n + "}",
}
for label, fn in shapes.items():
    print(label)
    prev = None
    for n in (1000, 2000, 4000, 8000):
        text = fn(n)
        if len(text) > 200000:
            break
        dt = t(text)
        r = f"{dt/prev:5.2f}x" if prev else "  -"
        prev = dt
        print(f"   n={n:5d} chars={len(text):7d} {dt*1000:9.2f} ms {r}")
