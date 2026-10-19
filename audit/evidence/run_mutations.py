"""Run one mutation at a time against the patched tree and report survivors."""
import os
import pathlib
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = pathlib.Path(__file__).resolve().parent


def _project_root() -> pathlib.Path:
    """Find the project root (sibling or nested `python-dotenv/`)."""
    for cand in (HERE, HERE.parent, HERE.parent.parent):
        for base in (cand, cand / "python-dotenv"):
            if (base / "src" / "dotenv" / "__init__.py").is_file():
                return base
    raise SystemExit(f"cannot locate the project root from {HERE}")


ROOT = _project_root()
SRC = ROOT
MUT = ROOT.parent / "mut_run"
PY = sys.executable

# (label, file, old_snippet, new_snippet, test selector)
MUTATIONS = [
    (
        "BOM not re-emitted",
        "src/dotenv/main.py",
        '        first = source.read(1)\n'
        '        if first == "\\ufeff":\n'
        "            dest.write(first)\n"
        "        else:\n"
        "            source.seek(0)\n",
        "",
        "bom",
    ),
    (
        "rewrite reads with universal newlines",
        "src/dotenv/main.py",
        'source: IO[str] = open(path, encoding=encoding, newline="")',
        "source: IO[str] = open(path, encoding=encoding)",
        "line_endings or carriage_returns",
    ),
    (
        "rewrite writes with universal newlines",
        "src/dotenv/main.py",
        '            encoding=encoding,\n            newline="",\n            delete=False,',
        "            encoding=encoding,\n            delete=False,",
        "line_endings or carriage_returns",
    ),
    (
        # The line-terminator variants live in run_mutations2.py.
        "append to a file without a trailing newline glues the lines",
        "src/dotenv/main.py",
        "            if missing_newline:\n                dest.write(newline)\n",
        "",
        "terminator or line_endings",
    ),
    (
        "_get_stream reads with universal newlines",
        "src/dotenv/main.py",
        'with open(self.dotenv_path, encoding=self.encoding, newline="") as stream:',
        "with open(self.dotenv_path, encoding=self.encoding) as stream:",
        "carriage_returns",
    ),
    (
        "bare declarations mask the environment",
        "src/dotenv/main.py",
        "            defined = {k: v for k, v in new_values.items() if v is not None}",
        "            defined = dict(new_values)",
        "mask",
    ),
    (
        "load_dotenv returns True for valueless-only content",
        "src/dotenv/main.py",
        "        if not any(value is not None for value in self.dict().values()):",
        "        if not self.dict():",
        "return_value_means",
    ),
    (
        "key validation removed",
        "src/dotenv/main.py",
        "    _check_key_is_writable(key_to_set)",
        "    pass",
        "unwritable_key or rejects_key",
    ),
    (
        "empty value does not use the default",
        "src/dotenv/variables.py",
        '        if result is None or result == "":',
        "        if result is None:",
        "resolve_default or uses_default_for_empty",
    ),
    (
        # NOTE: `if not result` is *equivalent* to the emptiness test for
        # `str | None` inputs (only "" and None are falsy), so it is not a
        # mutation. This variant instead drops the default entirely, which the
        # empty-value cases must catch.
        "default never applied",
        "src/dotenv/variables.py",
        '            return self.default if self.default is not None else ""',
        '            return ""',
        "resolve_default or uses_default_for_empty",
    ),
    (
        "parse_variables back to the quadratic regex",
        "src/dotenv/variables.py",
        '    cursor = 0\n    search_from = 0\n',
        "    cursor = 0\n"
        "    for _m in _posix_variable.finditer(value):\n"
        "        _s, _e = _m.span()\n"
        "        if _s > cursor:\n"
        "            yield Literal(value=value[cursor:_s])\n"
        "        yield Variable(name=_m['name'], default=_m['default'])\n"
        "        cursor = _e\n"
        "    if cursor < len(value):\n"
        "        yield Literal(value=value[cursor:])\n"
        "    return\n"
        "    search_from = 0\n",
        "is_linear or parse_variables",
    ),
    (
        "CLI reads with the process locale",
        "src/dotenv/cli.py",
        'with open(path, encoding="utf-8") as stream:',
        "with open(path) as stream:",
        "stream_file_decodes or gbk or undecodable",
    ),
    (
        "parser recovery consumes only CR",
        "src/dotenv/parser.py",
        '_rest_of_line = make_regex(r"[^\\r\\n]*(?:\\r\\n|\\r|\\n)?")',
        '_rest_of_line = make_regex(r"[^\\r\\n]*(?:\\r|\\n|\\r\\n)?")',
        "recovers_whole_line or crlf_is_a_single",
    ),
]


def run(label, relpath, old, new, selector):
    if MUT.exists():
        shutil.rmtree(MUT)
    shutil.copytree(SRC, MUT, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    target = MUT / relpath
    text = target.read_text(encoding="utf-8")
    if old not in text:
        return label, "SNIPPET NOT FOUND", ""
    target.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
    proc = subprocess.run(
        [PY, "-m", "pytest", "tests", "-q", "-k", selector, "-p", "no:cacheprovider"],
        cwd=MUT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONPATH": str(MUT / "src")},
    )
    tail = [ln for ln in proc.stdout.splitlines() if "passed" in ln or "failed" in ln]
    verdict = "KILLED" if proc.returncode != 0 else "SURVIVED"
    return label, verdict, tail[-1] if tail else ""


for label, relpath, old, new, selector in MUTATIONS:
    name, verdict, detail = run(label, relpath, old, new, selector)
    print(f"{verdict:9} | {name:46} | {detail}")

if MUT.exists():
    shutil.rmtree(MUT)
