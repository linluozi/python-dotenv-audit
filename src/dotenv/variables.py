import re
from abc import ABCMeta, abstractmethod
from typing import Iterator, Mapping, Optional

# Kept as the readable specification of the supported syntax; `parse_variables`
# implements the same grammar as a linear scan (see the note there).
_posix_variable = re.compile(
    r"""
    \$\{
        (?P<name>[^\}:]*)
        (?::-
            (?P<default>[^\}]*)
        )?
    \}
    """,
    re.VERBOSE,
)


class Atom(metaclass=ABCMeta):
    def __ne__(self, other: object) -> bool:
        result = self.__eq__(other)
        if result is NotImplemented:
            return NotImplemented
        return not result

    @abstractmethod
    def resolve(self, env: Mapping[str, Optional[str]]) -> str: ...


class Literal(Atom):
    def __init__(self, value: str) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"Literal(value={self.value})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.value == other.value

    def __hash__(self) -> int:
        return hash((self.__class__, self.value))

    def resolve(self, env: Mapping[str, Optional[str]]) -> str:
        return self.value


class Variable(Atom):
    def __init__(self, name: str, default: Optional[str]) -> None:
        self.name = name
        self.default = default

    def __repr__(self) -> str:
        return f"Variable(name={self.name}, default={self.default})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return (self.name, self.default) == (other.name, other.default)

    def __hash__(self) -> int:
        return hash((self.__class__, self.name, self.default))

    def resolve(self, env: Mapping[str, Optional[str]]) -> str:
        # `${name:-default}` is the POSIX form that substitutes the default
        # when `name` is unset *or* null (the empty string). `env.get` alone
        # cannot express that: a key present with "" is returned as "" and the
        # default is skipped.
        #
        # The emptiness test is written out rather than `if not result` because
        # the mapping is typed `Optional[str]` but callers can hand in any
        # mapping; an explicit comparison keeps the rule ("unset or empty
        # string") from silently changing meaning if a falsy non-string value
        # ever reaches it.
        result = env.get(self.name)
        if result is None or result == "":
            return self.default if self.default is not None else ""
        return result


def parse_variables(value: str) -> Iterator[Atom]:
    # `finditer` with the pattern above is quadratic on an unterminated
    # expansion: `[^}:]*` is greedy, so for a value holding N occurrences of
    # `${` and no `}` at all the engine swallows the whole tail and then
    # backtracks one character at a time at every start position. A 16 KB value
    # of `${` repeated took ~1.8 s and 32 KB took ~7.7 s, so a truncated or
    # hostile `.env` value stalled `load_dotenv` (and `dotenv run`).
    #
    # Scanning for the literal `${` first and then locating the closing `}`
    # yields exactly the same atoms -- `[^}:]*` can never match a `$`, `:` or
    # `}`, so the first candidate match after a `${` always starts there -- but
    # each start position is visited once, making the whole pass linear.
    cursor = 0
    search_from = 0

    while True:
        start = value.find("${", search_from)
        if start < 0:
            break

        close = value.find("}", start + 2)
        if close < 0:
            # No `}` anywhere after this `${`, so no expansion can match; the
            # rest of the value is literal text (same as the regex engine).
            break

        body = value[start + 2 : close]
        # `[^}:]*` stops at the first `:`, so the default separator can only be
        # the two characters right after that first colon.
        separator = body.find(":")
        if separator < 0:
            name, default = body, None
        elif body[separator : separator + 2] == ":-":
            name, default = body[:separator], body[separator + 2 :]
        else:
            # A `:` that is not part of `:-` cannot appear in a name, so this
            # `${` does not start an expansion; try the next one.
            search_from = start + 1
            continue

        if start > cursor:
            yield Literal(value=value[cursor:start])

        yield Variable(name=name, default=default)
        cursor = search_from = close + 1

    length = len(value)
    if cursor < length:
        yield Literal(value=value[cursor:length])
