from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from opcua_tui.infrastructure.logging_config import LogRecordView
from opcua_tui.ui.screens.log_viewer_screen import LogViewerScreen


class FakeLogWidget:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.auto_scroll = True

    def write_line(self, line: str) -> None:
        self.lines.append(line)

    def clear(self) -> None:
        self.lines.clear()


class FakeInputWidget:
    def __init__(self) -> None:
        self.focused = False

    def focus(self) -> None:
        self.focused = True


class FakeStaticWidget:
    def __init__(self) -> None:
        self.text = ""

    def update(self, text: str) -> None:
        self.text = text


class FakeBuffer:
    def __init__(self, entries: list[LogRecordView]) -> None:
        self.entries = entries

    def current_sequence(self) -> int:
        if not self.entries:
            return 0
        return self.entries[-1].sequence

    def snapshot(self) -> list[LogRecordView]:
        return list(self.entries)

    def entries_since(self, sequence: int) -> tuple[list[LogRecordView], int]:
        new_entries = [entry for entry in self.entries if entry.sequence > sequence]
        return new_entries, self.current_sequence()


def _entry(sequence: int, *, level: str, logger_name: str, message: str) -> LogRecordView:
    return LogRecordView(
        sequence=sequence,
        timestamp=f"2026-04-11T10:00:0{sequence}+02:00",
        level=level,
        logger_name=logger_name,
        message=message,
        operation="-",
        error_ref="-",
    )


def test_log_viewer_rebuild_applies_level_and_text_filter(monkeypatch) -> None:
    entries = [
        _entry(1, level="INFO", logger_name="opcua_tui.main", message="startup"),
        _entry(2, level="ERROR", logger_name="asyncua.client", message="connect failed"),
    ]
    buffer = FakeBuffer(entries)
    screen = LogViewerScreen()
    log_widget = FakeLogWidget()
    filter_widget = FakeInputWidget()
    meta_widget = FakeStaticWidget()

    def fake_query_one(selector, _type=None):
        if selector == "#log-output":
            return log_widget
        if selector == "#log-filter":
            return filter_widget
        return meta_widget

    monkeypatch.setattr(screen, "query_one", fake_query_one)
    monkeypatch.setattr("opcua_tui.ui.screens.log_viewer_screen.get_log_buffer", lambda: buffer)
    monkeypatch.setattr(
        "opcua_tui.ui.screens.log_viewer_screen.get_log_file_path", lambda: Path("app.log")
    )

    screen._min_level = 40
    screen._rebuild_view()
    assert len(log_widget.lines) == 1
    assert "connect failed" in log_widget.lines[0]

    screen.on_input_changed(SimpleNamespace(input=SimpleNamespace(id="log-filter"), value="failed"))
    assert len(log_widget.lines) == 1
    assert "connect failed" in log_widget.lines[0]


def test_log_viewer_poll_logs_appends_new_entries(monkeypatch) -> None:
    entries = [_entry(1, level="INFO", logger_name="opcua_tui.main", message="first")]
    buffer = FakeBuffer(entries)
    screen = LogViewerScreen()
    log_widget = FakeLogWidget()
    filter_widget = FakeInputWidget()
    meta_widget = FakeStaticWidget()

    def fake_query_one(selector, _type=None):
        if selector == "#log-output":
            return log_widget
        if selector == "#log-filter":
            return filter_widget
        return meta_widget

    monkeypatch.setattr(screen, "query_one", fake_query_one)
    monkeypatch.setattr("opcua_tui.ui.screens.log_viewer_screen.get_log_buffer", lambda: buffer)
    monkeypatch.setattr(
        "opcua_tui.ui.screens.log_viewer_screen.get_log_file_path", lambda: Path("app.log")
    )

    screen._rebuild_view()
    assert len(log_widget.lines) == 1

    buffer.entries.append(
        _entry(2, level="WARNING", logger_name="textual.app", message="slow render")
    )
    screen._poll_logs()
    assert len(log_widget.lines) == 2
    assert "slow render" in log_widget.lines[1]
