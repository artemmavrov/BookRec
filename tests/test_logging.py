import logging

import pytest
import structlog

from bookrec.logging import HANDLER_NAME, configure_logging
from tests.conftest import read_logs


def test_json_log_has_required_fields(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO", json_logs=True)

    structlog.get_logger("bookrec.test").info("something_happened", answer=42)

    (entry,) = read_logs(capsys)
    assert entry["message"] == "something_happened"
    assert entry["level"] == "info"
    assert entry["logger"] == "bookrec.test"
    assert entry["answer"] == 42
    assert entry["timestamp"].endswith("Z")
    assert "event" not in entry


def test_bound_context_is_added_to_every_log(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO")
    structlog.contextvars.bind_contextvars(request_id="abc")

    structlog.get_logger("bookrec.test").info("first")
    structlog.get_logger("bookrec.other").info("second")

    entries = read_logs(capsys)
    assert [entry["request_id"] for entry in entries] == ["abc", "abc"]


def test_standard_library_logs_use_the_same_format(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO")

    logging.getLogger("uvicorn.error").info("Application startup complete.")

    (entry,) = read_logs(capsys)
    assert entry["message"] == "Application startup complete."
    assert entry["level"] == "info"
    assert entry["logger"] == "uvicorn.error"
    assert "timestamp" in entry


def test_exception_is_serialized_in_one_json_line(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO")

    try:
        raise ValueError("boom")
    except ValueError:
        structlog.get_logger("bookrec.test").exception("operation_failed")

    (entry,) = read_logs(capsys)
    assert entry["level"] == "error"
    assert "ValueError: boom" in entry["exception"]


def test_log_level_filters_messages(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("WARNING")
    log = structlog.get_logger("bookrec.test")

    log.info("hidden")
    log.warning("visible")

    entries = read_logs(capsys)
    assert [entry["message"] for entry in entries] == ["visible"]


def test_uvicorn_access_log_is_silenced(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO")

    logging.getLogger("uvicorn.access").info('127.0.0.1 - "GET / HTTP/1.1" 200')

    assert capsys.readouterr().out == ""


def test_console_format_is_not_json(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO", json_logs=False)

    structlog.get_logger("bookrec.test").info("readable", key="value")

    output = capsys.readouterr().out
    assert "readable" in output
    assert "key=value" in output
    assert not output.lstrip().startswith("{")


def test_configure_logging_is_idempotent() -> None:
    configure_logging("INFO")
    configure_logging("DEBUG")

    handlers = [h for h in logging.getLogger().handlers if h.get_name() == HANDLER_NAME]
    assert len(handlers) == 1
    assert logging.getLogger().level == logging.DEBUG
