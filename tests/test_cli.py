import os
import subprocess
import sys
from pathlib import Path
from typing import Optional
from unittest import mock

import pytest

import dotenv
from dotenv.cli import cli as dotenv_cli
from dotenv.cli import stream_file
from dotenv.version import __version__
from tests.test_lib import check_process, run_dotenv


@pytest.mark.parametrize(
    "output_format,content,expected",
    (
        (None, "x='a b c'", """x=a b c\n"""),
        ("simple", "x='a b c'", """x=a b c\n"""),
        ("simple", """x='"a b c"'""", """x="a b c"\n"""),
        ("simple", '''x="'a b c'"''', """x='a b c'\n"""),
        ("json", "x='a b c'", """{\n  "x": "a b c"\n}\n"""),
        ("shell", "x='a b c'", "x='a b c'\n"),
        ("shell", """x='"a b c"'""", """x='"a b c"'\n"""),
        ("shell", '''x="'a b c'"''', """x=''"'"'a b c'"'"''\n"""),
        ("shell", "x='a\nb\nc'", "x='a\nb\nc'\n"),
        ("export", "x='a b c'", """export x='a b c'\n"""),
    ),
)
def test_list(
    cli, dotenv_path, output_format: Optional[str], content: str, expected: str
):
    dotenv_path.write_text(content + "\n")

    args = ["--file", dotenv_path, "list"]
    if format is not None:
        args.extend(["--format", output_format])

    result = cli.invoke(dotenv_cli, args)

    assert (result.exit_code, result.output) == (0, expected)


def test_list_non_existent_file(cli):
    result = cli.invoke(dotenv_cli, ["--file", "nx_file", "list"])

    assert result.exit_code == 2, result.output
    assert "Error opening env file" in result.output


def test_list_not_a_file(cli):
    result = cli.invoke(dotenv_cli, ["--file", ".", "list"])

    assert result.exit_code == 2, result.output
    assert "Error opening env file" in result.output


def test_list_no_file(cli):
    result = cli.invoke(dotenv.cli.list_values, [])

    assert (result.exit_code, result.output) == (1, "")


def test_get_existing_value(cli, dotenv_path):
    dotenv_path.write_text("a=b")

    result = cli.invoke(dotenv_cli, ["--file", dotenv_path, "get", "a"])

    assert (result.exit_code, result.output) == (0, "b\n")


def test_get_empty_string_value(cli, dotenv_path):
    """Empty string values must not be treated as missing (truthiness trap)."""
    dotenv_path.write_text("a=\n")

    result = cli.invoke(dotenv_cli, ["--file", dotenv_path, "get", "a"])

    assert (result.exit_code, result.output) == (0, "\n")


def test_get_value_without_equals(cli, dotenv_path):
    dotenv_path.write_text("a")

    result = cli.invoke(dotenv_cli, ["--file", dotenv_path, "get", "a"])

    assert (result.exit_code, result.output) == (1, "")


def test_get_non_existent_value(cli, dotenv_path):
    result = cli.invoke(dotenv_cli, ["--file", dotenv_path, "get", "a"])

    assert (result.exit_code, result.output) == (1, "")


def test_get_non_existent_file(cli):
    result = cli.invoke(dotenv_cli, ["--file", "nx_file", "get", "a"])

    assert result.exit_code == 2
    assert "Error opening env file" in result.output


def test_get_not_a_file(cli):
    result = cli.invoke(dotenv_cli, ["--file", ".", "get", "a"])

    assert result.exit_code == 2
    assert "Error opening env file" in result.output


def test_unset_existing_value(cli, dotenv_path):
    dotenv_path.write_text("a=b")

    result = cli.invoke(dotenv_cli, ["--file", dotenv_path, "unset", "a"])

    assert (result.exit_code, result.output) == (0, "Successfully removed a\n")
    assert dotenv_path.read_text() == ""


def test_unset_non_existent_value(cli, dotenv_path):
    result = cli.invoke(dotenv_cli, ["--file", dotenv_path, "unset", "a"])

    assert (result.exit_code, result.output) == (1, "")
    assert dotenv_path.read_text() == ""


@pytest.mark.parametrize(
    "quote_mode,variable,value,expected",
    (
        ("always", "a", "x", "a='x'\n"),
        ("never", "a", "x", "a=x\n"),
        ("auto", "a", "x", "a=x\n"),
        ("auto", "a", "x y", "a='x y'\n"),
        ("auto", "a", "$", "a='$'\n"),
    ),
)
def test_set_quote_options(cli, dotenv_path, quote_mode, variable, value, expected):
    result = cli.invoke(
        dotenv_cli,
        [
            "--file",
            dotenv_path,
            "--export",
            "false",
            "--quote",
            quote_mode,
            "set",
            variable,
            value,
        ],
    )

    assert (result.exit_code, result.output) == (0, "{}={}\n".format(variable, value))
    assert dotenv_path.read_text() == expected


@pytest.mark.parametrize(
    "dotenv_path,export_mode,variable,value,expected",
    (
        (Path(".nx_file"), "true", "a", "x", "export a='x'\n"),
        (Path(".nx_file"), "false", "a", "x", "a='x'\n"),
    ),
)
def test_set_export(cli, dotenv_path, export_mode, variable, value, expected):
    result = cli.invoke(
        dotenv_cli,
        [
            "--file",
            dotenv_path,
            "--quote",
            "always",
            "--export",
            export_mode,
            "set",
            variable,
            value,
        ],
    )

    assert (result.exit_code, result.output) == (0, "{}={}\n".format(variable, value))
    assert dotenv_path.read_text() == expected


def test_set_non_existent_file(cli):
    result = cli.invoke(dotenv.cli.set_value, ["a", "b"])

    assert (result.exit_code, result.output) == (1, "")


def test_set_no_file(cli):
    result = cli.invoke(dotenv_cli, ["--file", "nx_file", "set"])

    assert result.exit_code == 2
    assert "Missing argument" in result.output


def test_set_missing_directory(cli, tmp_path):
    dotenv_path = tmp_path / "nx_dir" / ".env"

    result = cli.invoke(dotenv_cli, ["--file", dotenv_path, "set", "a", "b"])

    assert (result.exit_code, result.output) == (
        2,
        f"Error writing env file: [Errno 2] No such file or directory: {str(dotenv_path)!r}\n",
    )


@pytest.mark.skipif(
    sys.platform == "win32" or os.geteuid() == 0,
    reason="Directory permissions are not enforced on Windows or for root.",
)
def test_unset_read_only_directory(cli, tmp_path):
    directory = tmp_path / "ro"
    directory.mkdir()
    dotenv_path = directory / ".env"
    dotenv_path.write_text("a=b\n")
    directory.chmod(0o555)

    try:
        result = cli.invoke(dotenv_cli, ["--file", dotenv_path, "unset", "a"])
    finally:
        directory.chmod(0o755)

    assert (result.exit_code, result.output) == (
        2,
        f"Error writing env file: [Errno 13] Permission denied: {str(dotenv_path)!r}\n",
    )
    assert dotenv_path.read_text() == "a=b\n"


def test_get_default_path(tmp_path):
    (tmp_path / ".env").write_text("A=x")

    result = run_dotenv(["get", "A"], cwd=tmp_path)

    check_process(result, exit_code=0, stdout="x\n")


def test_run(tmp_path):
    (tmp_path / ".env").write_text("A=x")

    result = run_dotenv(["run", "printenv", "A"], cwd=tmp_path)

    check_process(result, exit_code=0, stdout="x\n")


def test_run_with_existing_variable(tmp_path):
    (tmp_path / ".env").write_text("A=x")
    env = dict(os.environ)
    env.update({"LANG": "en_US.UTF-8", "A": "y"})

    result = run_dotenv(["run", "printenv", "A"], cwd=tmp_path, env=env)

    check_process(result, exit_code=0, stdout="x\n")


def test_run_with_existing_variable_not_overridden(tmp_path):
    (tmp_path / ".env").write_text("A=x")
    env = dict(os.environ)
    env.update({"LANG": "en_US.UTF-8", "A": "C"})

    result = run_dotenv(
        ["run", "--no-override", "printenv", "A"], cwd=tmp_path, env=env
    )

    check_process(result, exit_code=0, stdout="C\n")


@pytest.mark.parametrize(
    "option,existing_value,expected",
    [
        ("--override", "environment", "file\nfile/suffix\n"),
        ("--no-override", "environment", "environment\nenvironment/suffix\n"),
        ("--no-override", "", "\n/suffix\n"),
    ],
)
def test_run_interpolation_respects_override(
    tmp_path, option, existing_value, expected
):
    (tmp_path / ".env").write_text(
        "DOTENV_TEST_BASE=file\nDOTENV_TEST_DERIVED=${DOTENV_TEST_BASE}/suffix\n"
    )
    env = dict(os.environ)
    env.pop("DOTENV_TEST_DERIVED", None)
    env["DOTENV_TEST_BASE"] = existing_value

    result = run_dotenv(
        [
            "run",
            option,
            sys.executable,
            "-c",
            "import os; print(os.environ['DOTENV_TEST_BASE']); "
            "print(os.environ['DOTENV_TEST_DERIVED'])",
        ],
        cwd=tmp_path,
        env=env,
    )

    check_process(result, exit_code=0, stdout=expected)


def test_run_with_none_value(tmp_path):
    (tmp_path / ".env").write_text("A=x\nc")

    result = run_dotenv(["run", "printenv", "A"], cwd=tmp_path)

    check_process(result, exit_code=0, stdout="x\n")


def test_run_with_other_env(dotenv_path, tmp_path):
    dotenv_path.write_text("A=x")

    result = run_dotenv(
        ["--file", str(dotenv_path), "run", "printenv", "A"],
        cwd=tmp_path,
    )

    check_process(result, exit_code=0, stdout="x\n")


@pytest.mark.parametrize(
    "args,expected_stdout,expected_content",
    [
        (["list"], "a=x\n", "a=x\n"),
        (["get", "a"], "x\n", "a=x\n"),
        (["set", "b", "y"], "b=y\n", "a=x\nb='y'\n"),
        (["unset", "a"], "Successfully removed a\n", ""),
        (
            ["run", sys.executable, "-c", "import os; print(os.environ['a'])"],
            "x\n",
            "a=x\n",
        ),
    ],
    ids=["list", "get", "set", "unset", "run"],
)
def test_file_option_expands_user(tmp_path, args, expected_stdout, expected_content):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".env").write_text("a=x\n")
    env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}

    result = run_dotenv(["--file", "~/.env", *args], cwd=tmp_path, env=env)

    check_process(result, exit_code=0, stdout=expected_stdout)
    assert (home / ".env").read_text() == expected_content
    assert sorted(tmp_path.iterdir()) == [home]


def test_run_without_cmd(tmp_path):
    result = run_dotenv(["run"], cwd=tmp_path)

    check_process(result, exit_code=2)
    assert "Invalid value for '-f'" in result.stderr


def test_run_with_invalid_cmd(dotenv_path, tmp_path):
    result = run_dotenv(
        ["--file", str(dotenv_path), "run", "i_do_not_exist"],
        cwd=tmp_path,
    )

    check_process(result, exit_code=1)
    assert "Command not found: i_do_not_exist" in result.stderr


def test_run_with_env_missing_and_invalid_cmd(tmp_path):
    """
    Check that an .env file missing takes precedence over a command not found error.
    """

    result = run_dotenv(["run", "i_do_not_exist"], cwd=tmp_path)

    check_process(result, exit_code=2)
    assert "Invalid value for '-f'" in result.stderr


def test_run_with_version(tmp_path):
    result = run_dotenv(["--version"], cwd=tmp_path)

    check_process(result, exit_code=0)
    assert result.stdout.strip().endswith(__version__)


def test_run_with_command_flags(dotenv_path, tmp_path):
    """
    Check that command flags passed after `dotenv run` are not interpreted.

    Here, we want the command to receive `--help`, not `dotenv run --help`.
    `sys.executable` is used instead of a system tool for portability.
    """

    result = run_dotenv(
        [
            "--file",
            str(dotenv_path),
            "run",
            sys.executable,
            "-c",
            "import sys; print(sys.argv[1:])",
            "--help",
        ],
        cwd=tmp_path,
    )

    check_process(result, exit_code=0, stdout="['--help']\n")


def test_run_with_dotenv_and_command_flags(dotenv_path, tmp_path):
    """
    Check that dotenv flags supersede command flags.
    """

    result = run_dotenv(
        ["--version", "--file", str(dotenv_path), "run", "printenv", "--version"],
        cwd=tmp_path,
    )

    check_process(result, exit_code=0)
    assert result.stdout.strip().startswith("dotenv, version")


def test_stream_file_decodes_as_utf8(cli, dotenv_path):
    """
    `dotenv set` writes UTF-8 (`set_key`'s default encoding), so `list`/`get`
    must read UTF-8 too. `stream_file` used `open(path)` with no encoding,
    which follows the process locale -- GBK on Chinese Windows -- so a file the
    same tool had just written came back as mojibake, or raised
    UnicodeDecodeError for characters the locale could not represent.

    This asserts the encoding structurally because `open()` resolves the
    locale in C: monkeypatching `locale.getpreferredencoding` does not affect
    it, so a behavioural test passes on a UTF-8 CI machine either way.
    """
    dotenv_path.write_bytes("A=1\n".encode())
    seen = []
    real_open = open

    def tracking_open(*args, **kwargs):
        seen.append(kwargs.get("encoding"))
        return real_open(*args, **kwargs)

    with mock.patch("builtins.open", tracking_open):
        with stream_file(dotenv_path) as stream:
            stream.read()

    assert seen == ["utf-8"]


@pytest.mark.skipif(
    sys.platform != "win32", reason="needs a non-UTF-8 process locale (cp936)"
)
def test_cli_round_trips_non_ascii_under_a_gbk_process_locale(tmp_path):
    """
    End-to-end: `dotenv set` then `dotenv get` in a real subprocess whose
    locale is GBK, which is what a Chinese Windows console uses.
    """
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_bytes(b"")
    env = {
        **os.environ,
        "PYTHONUTF8": "0",
        "PYTHONIOENCODING": "utf-8",
    }
    env.pop("LC_ALL", None)
    env.pop("LANG", None)

    def run(*args):
        return subprocess.run(
            [sys.executable, "-m", "dotenv", "--file", str(dotenv_path), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )

    set_result = run("set", "GREETING", "你好")
    assert set_result.returncode == 0, set_result.stderr
    assert dotenv_path.read_bytes() == "GREETING='你好'\n".encode()

    get_result = run("get", "GREETING")
    assert get_result.returncode == 0, get_result.stderr
    assert get_result.stdout == "你好\n"


def test_list_reports_undecodable_file_without_a_traceback(cli, dotenv_path):
    dotenv_path.write_bytes(b"A=\xff\xfe\n")

    result = cli.invoke(dotenv_cli, ["--file", dotenv_path, "list"])

    assert result.exit_code == 2
    assert "Error decoding env file" in result.output
    assert "Traceback" not in result.output


def test_set_rejects_key_the_parser_cannot_read_back(cli, dotenv_path):
    """
    `dotenv set` must not report success for a key that would be stored as a
    different variable.
    """
    dotenv_path.write_bytes(b"BASE=1\n")

    result = cli.invoke(dotenv_cli, ["--file", dotenv_path, "set", "A B", "v"])

    assert result.exit_code != 0
    assert dotenv_path.read_bytes() == b"BASE=1\n"
