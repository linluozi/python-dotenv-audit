"""Differential: old vs new _posix_variable over a corpus, to bound the change."""
import random
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OLD = re.compile(r"\$\{(?P<name>[^\}:]*)(?::-(?P<default>[^\}]*))?\}", re.VERBOSE)
NEW = re.compile(r"\$\{(?P<name>[^\}:$]*)(?::-(?P<default>[^\}]*))?\}", re.VERBOSE)


def atoms(rx, value):
    out = []
    cursor = 0
    for m in rx.finditer(value):
        s, e = m.span()
        if s > cursor:
            out.append(("lit", value[cursor:s]))
        out.append(("var", m["name"], m["default"]))
        cursor = e
    if cursor < len(value):
        out.append(("lit", value[cursor:]))
    return out


CORPUS = [
    "", "a", "${a}", "${a:-b}", "${a}${b}", "a${b}c${d}e", "${}", "${:-x}",
    "${a:-}", "${a:b}", "${a${b}}", "${a$b}", "$a", "${a}", "${A}${B}",
    "x${a:-${b}}y", "${a}}", "{{${a}}}", "${a:-b:-c}", "${ a }", "${a b}",
    "${a\nb}", "${a}${", "${", "$${a}", "${a}$", "${中文}", "${é:-ü}",
    "${a:-x$y}", "${a:-${b}", "${a:--b}", "${a:-:-}",
]
ALPHABET = list("ab01 ${}:-$\\'\"\n\té中")
random.seed(7)
for _ in range(60000):
    CORPUS.append("".join(random.choice(ALPHABET) for _ in range(random.randint(0, 24))))

diffs = []
for text in CORPUS:
    o, n = atoms(OLD, text), atoms(NEW, text)
    if o != n:
        diffs.append((text, o, n))

print(f"corpus={len(CORPUS)} differing={len(diffs)}")
for text, o, n in diffs[:15]:
    print(f"  {text!r}\n     old={o}\n     new={n}")

dollar_in_name = [t for t, o, n in diffs if any(
    a[0] == "var" and "$" in a[1] for a in o
)]
print(f"\ndiffs where the OLD parse put a '$' inside a variable name: "
      f"{len(dollar_in_name)}/{len(diffs)}")
print("  samples:", [t for t in dollar_in_name[:8]])
