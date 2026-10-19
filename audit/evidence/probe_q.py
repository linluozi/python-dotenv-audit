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
    "dollar-brace xN (no brace)": lambda n: "${" * n,
    "dollar-brace xN + braces xN": lambda n: "${" * n + "}" * n,
    "dollar-brace xN + text": lambda n: "".join(f"${{v{i}" for i in range(n)),
    "dollar-brace xN then one brace": lambda n: "${" * n + "}",
    "braces then dollars": lambda n: "}" * n + "${" * n,
    "colon-name xN no brace": lambda n: "${" + "a" * n + ":" + "b" * n,
}
for label, fn in shapes.items():
    print(label)
    prev = None
    for n in (1000, 2000, 4000, 8000):
        text = fn(n)
        if len(text) > 400000:
            break
        dt = t(text)
        r = f"{dt/prev:5.2f}x" if prev else "  -"
        prev = dt
        print(f"   n={n:5d} chars={len(text):7d} {dt*1000:9.2f} ms {r}")
