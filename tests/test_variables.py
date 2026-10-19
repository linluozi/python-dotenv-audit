import pytest

from dotenv.variables import Literal, Variable, parse_variables


@pytest.mark.parametrize(
    "value,expected",
    [
        ("", []),
        ("a", [Literal(value="a")]),
        ("${a}", [Variable(name="a", default=None)]),
        ("${a:-b}", [Variable(name="a", default="b")]),
        (
            "${a}${b}",
            [
                Variable(name="a", default=None),
                Variable(name="b", default=None),
            ],
        ),
        (
            "a${b}c${d}e",
            [
                Literal(value="a"),
                Variable(name="b", default=None),
                Literal(value="c"),
                Variable(name="d", default=None),
                Literal(value="e"),
            ],
        ),
    ],
)
def test_parse_variables(value, expected):
    result = parse_variables(value)

    assert list(result) == expected


@pytest.mark.parametrize(
    "env,default,expected",
    [
        # `${name:-default}` uses the default when the name is unset or null.
        ({}, "d", "d"),
        ({"b": ""}, "d", "d"),
        ({"b": None}, "d", "d"),
        ({"b": "c"}, "d", "c"),
        # "0" is a real value, not null (only the empty string is null for `:-`).
        ({"b": "0"}, "d", "0"),
        # `${name}` has no default, so those cases stay empty.
        ({}, None, ""),
        ({"b": ""}, None, ""),
        ({"b": "0"}, None, "0"),
    ],
)
def test_variable_resolve_default_semantics(env, default, expected):
    assert Variable(name="b", default=default).resolve(env) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        # A run of `${` with no closing brace must not be an expansion.
        ("${" * 4, [Literal(value="${" * 4)]),
        # `:-` only counts right after the first colon.
        ("${a:b}", [Literal(value="${a:b}")]),
        ("${a::b}", [Literal(value="${a::b}")]),
        # `[^}:]*` stops at the first colon, and a `:` that is not part of
        # `:-` makes the whole candidate invalid, so these stay literal.
        ("${:}", [Literal(value="${:}")]),
        ("${a:-}", [Variable(name="a", default="")]),
        # A `$` *is* allowed inside a name; only `:` and `}` end it. The
        # expected atoms below are the ones the original implementation
        # produces (measured, not assumed).
        (
            "${a${b}}",
            [Variable(name="a${b", default=None), Literal(value="}")],
        ),
        ("${a$b}", [Variable(name="a$b", default=None)]),
    ],
)
def test_parse_variables_edge_shapes(value, expected):
    assert list(parse_variables(value)) == expected


def test_parse_variables_is_linear_on_unterminated_expansions():
    """
    A value made of many `${` and no `}` at all used to be quadratic: the
    greedy name group swallowed the whole tail and then backtracked one
    character at a time at every start position. 16 KB took ~1.8 s and 32 KB
    ~7.7 s, so a truncated or hostile `.env` value could stall `load_dotenv`.

    The assertion is structural rather than a wall-clock threshold: a linear
    scan visits each `${` once and finds no closing brace in O(n).
    """
    import time

    small = "${" * 4000  # 8 KB
    large = "${" * 16000  # 32 KB

    start = time.perf_counter()
    assert list(parse_variables(small)) == [Literal(value=small)]
    small_elapsed = time.perf_counter() - start

    start = time.perf_counter()
    assert list(parse_variables(large)) == [Literal(value=large)]
    large_elapsed = time.perf_counter() - start

    # Quadratic behaviour made the 4x larger input ~16x slower; a linear scan
    # stays well under a 10x ratio even with timer noise.
    assert large_elapsed < small_elapsed * 10 + 0.05
    assert large_elapsed < 0.5
