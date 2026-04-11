from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from opcua_tui.infrastructure.logging_config import (
    InMemoryLogHandler,
    get_log_buffer,
    setup_logging,
)


def test_setup_logging_creates_rotating_file_handler(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPCUA_TUI_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("OPCUA_TUI_LOG_LEVEL", "DEBUG")

    log_file = setup_logging(force=True)
    root_logger = logging.getLogger()

    rotating_handlers = [
        handler for handler in root_logger.handlers if isinstance(handler, RotatingFileHandler)
    ]
    assert len(rotating_handlers) == 1
    assert rotating_handlers[0].level == logging.DEBUG

    logger = logging.getLogger("opcua_tui")
    logger.info("test log entry", extra={"operation": "test", "error_ref": "abc12345"})
    rotating_handlers[0].flush()

    assert log_file.exists()
    assert "test log entry" in log_file.read_text(encoding="utf-8")


def test_setup_logging_invalid_level_defaults_to_info(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPCUA_TUI_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("OPCUA_TUI_LOG_LEVEL", "NOT_A_LEVEL")

    setup_logging(force=True)
    logger = logging.getLogger()

    assert logger.level == logging.INFO


def test_setup_logging_registers_in_memory_buffer_handler(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPCUA_TUI_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("OPCUA_TUI_LOG_BUFFER_SIZE", "100")

    setup_logging(force=True)
    root_logger = logging.getLogger()

    memory_handlers = [
        handler for handler in root_logger.handlers if isinstance(handler, InMemoryLogHandler)
    ]
    assert len(memory_handlers) == 1

    logger = logging.getLogger("opcua_tui.test")
    logger.info("buffered entry", extra={"operation": "test", "error_ref": "deadbeef"})

    buffer = get_log_buffer()
    assert buffer is not None
    entries = buffer.snapshot()
    assert any(entry.message == "buffered entry" for entry in entries)


def test_setup_logging_applies_namespace_level_overrides(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPCUA_TUI_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("OPCUA_TUI_LOG_LEVEL_ASYNCUA", "ERROR")
    monkeypatch.setenv("OPCUA_TUI_LOG_LEVEL_TEXTUAL", "WARNING")

    setup_logging(force=True)

    assert logging.getLogger("asyncua").level == logging.ERROR
    assert logging.getLogger("opcua").level == logging.ERROR
    assert logging.getLogger("textual").level == logging.WARNING


def test_setup_logging_enables_textual_handler_when_requested(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPCUA_TUI_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("OPCUA_TUI_LOG_TEXTUAL_HANDLER", "1")

    setup_logging(force=True)
    root_logger = logging.getLogger()

    assert any(handler.__class__.__name__ == "TextualHandler" for handler in root_logger.handlers)
