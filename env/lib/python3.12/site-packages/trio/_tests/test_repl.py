from __future__ import annotations

import subprocess
import sys
from typing import Protocol

import pytest

import trio._repl


class RawInput(Protocol):
    def __call__(self, prompt: str = "") -> str: ...


def build_raw_input(cmds: list[str]) -> RawInput:
    """
    Pass in a list of strings.
    Returns a callable that returns each string, each time its called
    When there are not more strings to return, raise EOFError
    """
    cmds_iter = iter(cmds)
    prompts = []

    def _raw_helper(prompt: str = "") -> str:
        prompts.append(prompt)
        try:
            return next(cmds_iter)
        except StopIteration:
            raise EOFError from None

    return _raw_helper


def test_build_raw_input() -> None:
    """Quick test of our helper function."""
    raw_input = build_raw_input(["cmd1"])
    assert raw_input() == "cmd1"
    with pytest.raises(EOFError):
        raw_input()


# In 3.10 or later, types.FunctionType (used internally) will automatically
# attach __builtins__ to the function objects. However we need to explicitly
# include it for 3.9 support
def build_locals() -> dict[str, object]:
    return {"__builtins__": __builtins__}


async def test_basic_interaction(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Run some basic commands through the interpreter while capturing stdout.
    Ensure that the interpreted prints the expected results.
    """
    console = trio._repl.TrioInteractiveConsole(repl_locals=build_locals())
    raw_input = build_raw_input(
        [
            # evaluate simple expression and recall the value
            "x = 1",
            "print(f'{x=}')",
            # Literal gets printed
            "'hello'",
            # define and call sync function
            "def func():",
            "  print(x + 1)",
            "",
            "func()",
            # define and call async function
            "async def afunc():",
            "  return 4",
            "",
            "await afunc()",
            # import works
            "import sys",
            "sys.stdout.write('hello stdout\\n')",
        ],
    )
    monkeypatch.setattr(console, "raw_input", raw_input)
    await trio._repl.run_repl(console)
    out, _err = capsys.readouterr()
    assert out.splitlines() == ["x=1", "'hello'", "2", "4", "hello stdout", "13"]


async def test_system_exits_quit_interpreter(monkeypatch: pytest.MonkeyPatch) -> None:
    console = trio._repl.TrioInteractiveConsole(repl_locals=build_locals())
    raw_input = build_raw_input(
        [
            "raise SystemExit",
        ],
    )
    monkeypatch.setattr(console, "raw_input", raw_input)
    with pytest.raises(SystemExit):
        await trio._repl.run_repl(console)


async def test_KI_interrupts(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = trio._repl.TrioInteractiveConsole(repl_locals=build_locals())
    raw_input = build_raw_input(
        [
            "import signal, trio, trio.lowlevel",
            "async def f():",
            "  trio.lowlevel.spawn_system_task("
            "    trio.to_thread.run_sync,"
            "    signal.raise_signal, signal.SIGINT,"
            "  )",  # just awaiting this kills the test runner?!
            "  await trio.sleep_forever()",
            "  print('should not see this')",
            "",
            "await f()",
            "print('AFTER KeyboardInterrupt')",
        ],
    )
    monkeypatch.setattr(console, "raw_input", raw_input)
    await trio._repl.run_repl(console)
    out, err = capsys.readouterr()
    assert "KeyboardInterrupt" in err
    assert "should" not in out
    assert "AFTER KeyboardInterrupt" in out


async def test_system_exits_in_exc_group(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = trio._repl.TrioInteractiveConsole(repl_locals=build_locals())
    raw_input = build_raw_input(
        [
            "import sys",
            "if sys.version_info < (3, 11):",
            "  from exceptiongroup import BaseExceptionGroup",
            "",
            "raise BaseExceptionGroup('', [RuntimeError(), SystemExit()])",
            "print('AFTER BaseExceptionGroup')",
        ],
    )
    monkeypatch.setattr(console, "raw_input", raw_input)
    await trio._repl.run_repl(console)
    out, _err = capsys.readouterr()
    # assert that raise SystemExit in an exception group
    # doesn't quit
    assert "AFTER BaseExceptionGroup" in out


async def test_system_exits_in_nested_exc_group(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = trio._repl.TrioInteractiveConsole(repl_locals=build_locals())
    raw_input = build_raw_input(
        [
            "import sys",
            "if sys.version_info < (3, 11):",
            "  from exceptiongroup import BaseExceptionGroup",
            "",
            "raise BaseExceptionGroup(",
            "  '', [BaseExceptionGroup('', [RuntimeError(), SystemExit()])])",
            "print('AFTER BaseExceptionGroup')",
        ],
    )
    monkeypatch.setattr(console, "raw_input", raw_input)
    await trio._repl.run_repl(console)
    out, _err = capsys.readouterr()
    # assert that raise SystemExit in an exception group
    # doesn't quit
    assert "AFTER BaseExceptionGroup" in out


async def test_base_exception_captured(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = trio._repl.TrioInteractiveConsole(repl_locals=build_locals())
    raw_input = build_raw_input(
        [
            # The statement after raise should still get executed
            "raise BaseException",
            "print('AFTER BaseException')",
        ],
    )
    monkeypatch.setattr(console, "raw_input", raw_input)
    await trio._repl.run_repl(console)
    out, err = capsys.readouterr()
    assert "_threads.py" not in err
    assert "_repl.py" not in err
    assert "AFTER BaseException" in out


async def test_exc_group_captured(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = trio._repl.TrioInteractiveConsole(repl_locals=build_locals())
    raw_input = build_raw_input(
        [
            # The statement after raise should still get executed
            "raise ExceptionGroup('', [KeyError()])",
            "print('AFTER ExceptionGroup')",
        ],
    )
    monkeypatch.setattr(console, "raw_input", raw_input)
    await trio._repl.run_repl(console)
    out, _err = capsys.readouterr()
    assert "AFTER ExceptionGroup" in out


async def test_base_exception_capture_from_coroutine(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = trio._repl.TrioInteractiveConsole(repl_locals=build_locals())
    raw_input = build_raw_input(
        [
            "async def async_func_raises_base_exception():",
            "  raise BaseException",
            "",
            # This will raise, but the statement after should still
            # be executed
            "await async_func_raises_base_exception()",
            "print('AFTER BaseException')",
        ],
    )
    monkeypatch.setattr(console, "raw_input", raw_input)
    await trio._repl.run_repl(console)
    out, err = capsys.readouterr()
    assert "_threads.py" not in err
    assert "_repl.py" not in err
    assert "AFTER BaseException" in out


def test_main_entrypoint() -> None:
    """
    Basic smoke test when running via the package __main__ entrypoint.
    """
    repl = subprocess.run([sys.executable, "-m", "trio"], input=b"exit()")
    assert repl.returncode == 0
