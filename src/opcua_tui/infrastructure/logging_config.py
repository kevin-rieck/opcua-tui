from __future__ import annotations

import datetime as dt
import logging
import os
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Lock

from collections import deque

DEFAULT_LOG_LEVEL = "INFO"
LOG_FILE_NAME = "opcua-tui.log"
MAX_LOG_BYTES = 2_000_000
LOG_BACKUP_COUNT = 5
DEFAULT_LOG_BUFFER_SIZE = 2_000
MIN_LOG_BUFFER_SIZE = 100

_configured = False
_log_file_path: Path | None = None
_log_buffer: InMemoryLogBuffer | None = None
_managed_handlers: list[logging.Handler] = []


@dataclass(frozen=True)
class LogRecordView:
    sequence: int
    timestamp: str
    level: str
    logger_name: str
    message: str
    operation: str
    error_ref: str


class InMemoryLogBuffer:
    def __init__(self, *, max_entries: int) -> None:
        self._max_entries = max_entries
        self._entries: deque[LogRecordView] = deque(maxlen=max_entries)
        self._sequence = 0
        self._lock = Lock()

    def append(self, record: LogRecordView) -> None:
        with self._lock:
            self._entries.append(record)
            self._sequence = record.sequence

    def current_sequence(self) -> int:
        with self._lock:
            return self._sequence

    def snapshot(self) -> list[LogRecordView]:
        with self._lock:
            return list(self._entries)

    def entries_since(self, sequence: int) -> tuple[list[LogRecordView], int]:
        with self._lock:
            entries = [entry for entry in self._entries if entry.sequence > sequence]
            return entries, self._sequence


class InMemoryLogHandler(logging.Handler):
    def __init__(self, buffer: InMemoryLogBuffer) -> None:
        super().__init__()
        self._buffer = buffer
        self._sequence = 0
        self._lock = Lock()

    def emit(self, record: logging.LogRecord) -> None:
        with self._lock:
            self._sequence += 1
            sequence = self._sequence
        timestamp = (
            dt.datetime.fromtimestamp(record.created, dt.timezone.utc).astimezone().isoformat()
        )
        operation = getattr(record, "operation", "-")
        error_ref = getattr(record, "error_ref", "-")
        message = record.getMessage()
        view = LogRecordView(
            sequence=sequence,
            timestamp=timestamp,
            level=record.levelname,
            logger_name=record.name,
            message=message,
            operation=operation,
            error_ref=error_ref,
        )
        self._buffer.append(view)


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


def _resolve_int(value: str | None, *, default: int, minimum: int | None = None) -> int:
    try:
        resolved = int(value) if value is not None else default
    except ValueError:
        return default
    if minimum is not None and resolved < minimum:
        return default
    return resolved


def _resolve_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_log_dir() -> Path:
    override_dir = os.getenv("OPCUA_TUI_LOG_DIR")
    if override_dir:
        return Path(override_dir).expanduser()
    return Path.home() / ".opcua-tui" / "logs"


def setup_logging(*, force: bool = False) -> Path:
    global _configured, _log_file_path, _log_buffer

    if _configured and _log_file_path is not None and not force:
        return _log_file_path

    root_logger = logging.getLogger()
    for handler in _managed_handlers:
        root_logger.removeHandler(handler)
    _managed_handlers.clear()

    log_dir = _resolve_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = log_dir / LOG_FILE_NAME

    root_level = _resolve_log_level(os.getenv("OPCUA_TUI_LOG_LEVEL", DEFAULT_LOG_LEVEL))
    max_bytes = _resolve_int(
        os.getenv("OPCUA_TUI_LOG_FILE_MAX_BYTES"),
        default=MAX_LOG_BYTES,
        minimum=1,
    )
    backup_count = _resolve_int(
        os.getenv("OPCUA_TUI_LOG_FILE_BACKUP_COUNT"),
        default=LOG_BACKUP_COUNT,
        minimum=1,
    )
    buffer_size = _resolve_int(
        os.getenv("OPCUA_TUI_LOG_BUFFER_SIZE"),
        default=DEFAULT_LOG_BUFFER_SIZE,
        minimum=MIN_LOG_BUFFER_SIZE,
    )
    enable_textual_handler = _resolve_bool(
        os.getenv("OPCUA_TUI_LOG_TEXTUAL_HANDLER"),
        default=False,
    )
    textual_stderr = _resolve_bool(os.getenv("OPCUA_TUI_LOG_TEXTUAL_STDERR"), default=True)
    textual_stdout = _resolve_bool(os.getenv("OPCUA_TUI_LOG_TEXTUAL_STDOUT"), default=False)
    asyncua_level = (
        _resolve_log_level(os.getenv("OPCUA_TUI_LOG_LEVEL_ASYNCUA"))
        if os.getenv("OPCUA_TUI_LOG_LEVEL_ASYNCUA")
        else None
    )
    textual_level = (
        _resolve_log_level(os.getenv("OPCUA_TUI_LOG_LEVEL_TEXTUAL"))
        if os.getenv("OPCUA_TUI_LOG_LEVEL_TEXTUAL")
        else None
    )

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s op=%(operation)s ref=%(error_ref)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    file_handler = RotatingFileHandler(
        filename=log_file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(root_level)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(_DefaultRecordFieldsFilter())
    root_logger.addHandler(file_handler)
    _managed_handlers.append(file_handler)

    _log_buffer = InMemoryLogBuffer(max_entries=buffer_size)
    buffer_handler = InMemoryLogHandler(_log_buffer)
    buffer_handler.setLevel(root_level)
    buffer_handler.addFilter(_DefaultRecordFieldsFilter())
    root_logger.addHandler(buffer_handler)
    _managed_handlers.append(buffer_handler)

    if enable_textual_handler:
        try:
            from textual.logging import TextualHandler
        except Exception:
            pass
        else:
            textual_handler = TextualHandler(stderr=textual_stderr, stdout=textual_stdout)
            textual_handler.setLevel(root_level)
            textual_handler.setFormatter(
                logging.Formatter(
                    "%(levelname)s %(name)s op=%(operation)s ref=%(error_ref)s %(message)s"
                )
            )
            textual_handler.addFilter(_DefaultRecordFieldsFilter())
            root_logger.addHandler(textual_handler)
            _managed_handlers.append(textual_handler)

    root_logger.setLevel(root_level)

    if asyncua_level is not None:
        logging.getLogger("asyncua").setLevel(asyncua_level)
        logging.getLogger("opcua").setLevel(asyncua_level)
    if textual_level is not None:
        logging.getLogger("textual").setLevel(textual_level)

    logging.getLogger("opcua_tui").setLevel(root_level)
    logging.getLogger("opcua_tui").propagate = True

    _configured = True
    _log_file_path = log_file_path
    return log_file_path


def get_log_file_path() -> Path | None:
    return _log_file_path


def get_log_buffer() -> InMemoryLogBuffer | None:
    return _log_buffer
