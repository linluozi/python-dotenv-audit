"""Differential: new linear parse_variables vs the old regex-based one."""
import random
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "src")

from dotenv.variables import Literal, Variable, parse_variables

OLD = re.compile(r"\$\{(?P<name>[^\}:]*)(?::-(?P<default>[^\}]*))?\}", re.VERBOSE)


def old_atoms(value):
    out = []
    cursor = 0
    for m in OLD.finditer(value):
        s, e = m.span()
        if s > cursor:
            out.append(Literal(value=value[cursor:s]))
        out.append(Variable(name=m["name"], default=m["default"]))
        cursor = e
    if cursor < len(value):
        out.append(Literal(value=value[cursor:]))
    return out


CORPUS = [
    "", "a", "${a}", "${a:-b}", "${a}${b}", "a${b}c${d}e", "${}", "${:-x}",
    "${a:-}", "${a:b}", "${a${b}}", "${a$b}", "$a", "${a}", "${A}${B}",
    "x${a:-${b}}y", "${a}}", "{{${a}}}", "${a:-b:-c}", "${ a }", "${a b}",
    "${a\nb}", "${a}${", "${", "$${a}", "${a}$", "${中文}", "${é:-ü}",
    "${a:-x$y}", "${a:-${b}", "${a:--b}", "${a:-:-}", "${a:-b}${c:-d}",
    "${a:}${b}", "${:}", "${::}", "${a::b}", "${a:--}", "${}${}", "${a}${b",
    "${" * 5, "}" * 3 + "${" * 4, "${a" * 5, "${a:-" * 4 + "}", "${a:-" * 3,
    "${${${a}}}", "${a:-${b:-${c}}}", "\n${a}\r\n", "${a}\x00", "${a\x00b}",
    "${a}" * 50, "${a:-" + "x" * 100 + "}",
]
ALPHABET = list("ab01 ${}:-$\\'\"\n\t\ré中\x00")
random.seed(11)
for _ in range(120000):
    CORPUS.append("".join(random.choice(ALPHABET) for _ in range(random.randint(0, 26))))
# Structured cases: runs of `${` with/without closers at varied offsets.
for n in range(1, 12):
    for m in range(0, 6):
        CORPUS.append("${" * n + "}" * m)
        CORPUS.append("${a" * n + "}" * m)
        CORPUS.append("x" * n + "${" * m)

diffs = []
for text in CORPUS:
    new = list(parse_variables(text))
    old = old_atoms(text)
    if new != old:
        diffs.append((text, old, new))

print(f"corpus={len(CORPUS)} differing={len(diffs)}")
for text, old, new in diffs[:20]:
    print(f"  {text!r}\n     old={old}\n     new={new}")
