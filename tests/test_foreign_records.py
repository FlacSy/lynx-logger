"""
Regression tests for foreign (stdlib `logging`) record handling.

A LynxLogger attaches a `structlog.stdlib.ProcessorFormatter` to a stdlib
handler; records emitted through the plain `logging` API (e.g.
`logging.getLogger("app.sub").warning("x %s", y)`) are *foreign* to structlog
and are rendered via the formatter's ``foreign_pre_chain``. That chain must not
contain ``wrap_for_formatter`` — doing so made ``remove_processors_meta`` raise
``TypeError: 'tuple' object does not support item deletion`` and silently
dropped every stdlib log line. These tests pin that behaviour.
"""

import logging

import pytest

from lynx_logger import setup_logger


@pytest.fixture(autouse=True)
def _clean():
    for name in ("reg_foreign", "reg_foreign_json"):
        lg = logging.getLogger(name)
        for h in lg.handlers[:]:
            lg.removeHandler(h)
            h.close()
    yield


def test_stdlib_foreign_record_console_formats_without_error(capsys):
    setup_logger("reg_foreign", level="INFO", format="console")
    logging.getLogger("reg_foreign").propagate = False

    logging.getLogger("reg_foreign.child").warning("value is %s", "forty-two")

    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "value is forty-two" in combined          # positional args resolved
    assert "Logging error" not in combined            # no stdlib emit() failure
    assert "remove_processors_meta" not in combined   # the specific bug


def test_stdlib_foreign_record_json_formats_without_error(capsys):
    setup_logger("reg_foreign_json", level="INFO", format="json")
    logging.getLogger("reg_foreign_json").propagate = False

    logging.getLogger("reg_foreign_json.child").error("boom %d", 7)

    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "boom 7" in combined
    assert "Logging error" not in combined


def test_stdlib_foreign_record_exception_renders_traceback(capsys):
    setup_logger("reg_foreign", level="INFO", format="console")
    logging.getLogger("reg_foreign").propagate = False

    try:
        raise RuntimeError("kaboom")
    except RuntimeError:
        logging.getLogger("reg_foreign.child").exception("handler failed")

    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "handler failed" in combined
    assert "RuntimeError" in combined and "kaboom" in combined
    assert "Logging error" not in combined
