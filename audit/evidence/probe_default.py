import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "src")

from dotenv import dotenv_values
from dotenv.variables import Variable

print("=== Variable.resolve matrix ===")
for env, default in [
    ({}, "d"), ({"b": ""}, "d"), ({"b": "c"}, "d"), ({"b": "0"}, "d"),
    ({"b": None}, "d"), ({"b": ""}, None), ({"b": "0"}, None), ({}, None),
]:
    print(f"  env={env!r:14} default={default!r:6} -> {Variable('b', default).resolve(env)!r}")

print("\n=== dotenv_values ===")
for text in [
    "b=\na=${b:-d}\n",
    "b\na=${b:-d}\n",
    "b=0\na=${b:-d}\n",
    "b=c\na=${b:-d}\n",
    "a=${b:-d}\n",
    "b=\na=${b}\n",
    "b= \na=${b:-d}\n",
]:
    print(f"  {text!r:26} -> {dict(dotenv_values(stream=io.StringIO(text)))!r}")
