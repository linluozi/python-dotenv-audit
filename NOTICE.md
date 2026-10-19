# NOTICE

This repository contains a modified copy of
[python-dotenv](https://github.com/theskumar/python-dotenv),
Copyright (c) 2014 Saurabh Kumar (python-dotenv), 2013 Ted Tieken
(django-dotenv-rw), 2013 Jacob Kaplan-Moss (django-dotenv), licensed under the
BSD 3-Clause License reproduced in `LICENSE`. The `LICENSE` file is unchanged.

## What was modified

Baseline: upstream commit `0b2880591780a426b0551436f47a17e7a76d954f` (v1.2.4).

Changed files, all under `src/dotenv/` and `tests/`:

- `src/dotenv/parser.py` — line-break alternation order in `_rest_of_line`
- `src/dotenv/main.py` — newline handling in `rewrite()` and `_get_stream()`,
  BOM preservation, line-terminator detection, key validation, environment
  mapping for expansion, `load_dotenv` return value
- `src/dotenv/variables.py` — `${name:-default}` empty-value semantics, linear
  `parse_variables`
- `src/dotenv/cli.py` — UTF-8 decoding of the `.env` file
- `tests/` — 71 tests added
- `CHANGELOG.md` — entries for the fixes

The complete diff is in `audit/dotenv-fixes.patch`. Every change is described in
`audit/REPORT.md`.

## What was moved or replaced

- The upstream `README.md` is preserved as `audit/UPSTREAM_README.md`. The
  `README.md` at the repository root is this audit's own document.
- `docs/index.md` mirrors the root `README.md` (upstream had it as a symlink to
  `../README.md`, which does not survive a Windows checkout).
- Upstream's `.github/` directory (workflows, Dependabot config) is preserved as
  `audit/upstream-github/` rather than left active, so that upstream's release
  and CI pipelines do not run against this fork.

No file outside `audit/` was changed for reasons other than the ten fixes listed
in the report.

## A note on line endings

Five files carry CRLF line endings in this repository — `.editorconfig`,
`.gitignore`, `LICENSE`, `Makefile` and `src/dotenv/py.typed` — because upstream
stores them that way. They are byte-identical to upstream and were deliberately
left alone rather than normalised, so that a diff against upstream shows only the
ten fixes. Everything added by this audit (sources, tests, docs, scripts) is LF.
`.gitattributes` sets `* text=auto eol=lf` for checkouts.
