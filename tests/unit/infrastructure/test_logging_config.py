from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from opcua_tui.infrastructure.logging_config import setup_logging


def test_setup_logging_creates_rotating_file_handler(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPCUA_TUI_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("OPCUA_TUI_LOG_LEVEL", "DEBUG")

    log_file = setup_logging(force=True)
    logger = logging.getLogger("opcua_tui")

    rotating_handlers = [
        handler for handler in logger.handlers if isinstance(handler, RotatingFileHandler)
    ]
    assert len(rotating_handlers) == 1
    assert rotating_handlers[0].level == logging.DEBUG

    logger.info("test log entry", extra={"operation": "test", "error_ref": "abc12345"})
    rotating_handlers[0].flush()

    assert log_file.exists()
    assert "test log entry" in log_file.read_text(encoding="utf-8")


def test_setup_logging_invalid_level_defaults_to_info(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPCUA_TUI_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("OPCUA_TUI_LOG_LEVEL", "NOT_A_LEVEL")

    setup_logging(force=True)
    logger = logging.getLogger("opcua_tui")

    assert logger.level == logging.INFO
