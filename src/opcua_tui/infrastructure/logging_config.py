from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

DEFAULT_LOG_LEVEL = "INFO"
LOG_FILE_NAME = "opcua-tui.log"
MAX_LOG_BYTES = 2_000_000
LOG_BACKUP_COUNT = 5

_configured = False
_log_file_path: Path | None = None


class _DefaultRecordFieldsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "operation"):
            record.operation = "-"
        if not hasattr(record, "error_ref"):
            record.error_ref = "-"
        return True


def _resolve_log_level(level_name: str | None) -> int:
    if not level_name:
        return logging.INFO
    candidate = getattr(logging, level_name.upper(), None)
    return candidate if isinstance(candidate, int) else logging.INFO


def _resolve_log_dir() -> Path:
    override_dir = os.getenv("OPCUA_TUI_LOG_DIR")
    if override_dir:
        return Path(override_dir).expanduser()
    return Path.home() / ".opcua-tui" / "logs"


def setup_logging(*, force: bool = False) -> Path:
    global _configured, _log_file_path

    logger = logging.getLogger("opcua_tui")
    if _configured and _log_file_path is not None and not force:
        return _log_file_path

    log_dir = _resolve_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = log_dir / LOG_FILE_NAME

    level_name = os.getenv("OPCUA_TUI_LOG_LEVEL", DEFAULT_LOG_LEVEL)
    level = _resolve_log_level(level_name)

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s op=%(operation)s ref=%(error_ref)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler = RotatingFileHandler(
        filename=log_file_path,
        maxBytes=MAX_LOG_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(formatter)
    handler.addFilter(_DefaultRecordFieldsFilter())

    logger.handlers.clear()
    logger.setLevel(level)
    logger.propagate = False
    logger.addHandler(handler)

    _configured = True
    _log_file_path = log_file_path
    return log_file_path
