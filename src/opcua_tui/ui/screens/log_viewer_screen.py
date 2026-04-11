from __future__ import annotations

import logging

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, Log, Static

from opcua_tui.infrastructure.logging_config import LogRecordView, get_log_buffer, get_log_file_path


class LogViewerScreen(Screen[None]):
    BINDINGS = [
        Binding("escape", "close", "Back"),
        Binding("q", "close", "Back", priority=True),
        Binding("f", "toggle_follow", "Follow"),
        Binding("c", "clear_view", "Clear View"),
        Binding("/", "focus_filter", "Filter"),
        Binding("l", "cycle_level", "Level"),
    ]

    LEVELS = [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR]

    CSS = """
    LogViewerScreen {
        layout: vertical;
    }

    #log-meta {
        height: auto;
        padding: 0 1;
        color: $text-muted;
    }

    #log-filter {
        margin: 0 1;
        height: auto;
    }

    #log-output {
        height: 1fr;
        margin: 0 1 1 1;
        border: round $panel;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._sequence = 0
        self._follow = True
        self._min_level = logging.INFO
        self._filter_text = ""

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("", id="log-meta")
            yield Input(placeholder="Filter log lines...", id="log-filter")
            yield Log(id="log-output", auto_scroll=True)
        yield Footer()

    def on_mount(self) -> None:
        self._rebuild_view()
        self.set_interval(0.25, self._poll_logs)
        self.query_one("#log-output", Log).focus()

    def action_close(self) -> None:
        self.app.pop_screen()

    def action_toggle_follow(self) -> None:
        self._follow = not self._follow
        self.query_one("#log-output", Log).auto_scroll = self._follow
        self._refresh_meta()

    def action_clear_view(self) -> None:
        log_widget = self.query_one("#log-output", Log)
        log_widget.clear()
        buffer = get_log_buffer()
        if buffer is not None:
            self._sequence = buffer.current_sequence()
        self._refresh_meta()

    def action_focus_filter(self) -> None:
        self.query_one("#log-filter", Input).focus()

    def action_cycle_level(self) -> None:
        index = self.LEVELS.index(self._min_level)
        self._min_level = self.LEVELS[(index + 1) % len(self.LEVELS)]
        self._rebuild_view()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "log-filter":
            return
        self._filter_text = event.value.strip().lower()
        self._rebuild_view()

    def _poll_logs(self) -> None:
        buffer = get_log_buffer()
        if buffer is None:
            return
        entries, sequence = buffer.entries_since(self._sequence)
        self._sequence = sequence
        if not entries:
            return
        log_widget = self.query_one("#log-output", Log)
        for entry in entries:
            if self._include_entry(entry):
                log_widget.write_line(self._format_entry(entry))

    def _rebuild_view(self) -> None:
        log_widget = self.query_one("#log-output", Log)
        log_widget.clear()
        buffer = get_log_buffer()
        if buffer is None:
            self._sequence = 0
            self._refresh_meta()
            return
        entries = buffer.snapshot()
        self._sequence = buffer.current_sequence()
        for entry in entries:
            if self._include_entry(entry):
                log_widget.write_line(self._format_entry(entry))
        self._refresh_meta()

    def _include_entry(self, entry: LogRecordView) -> bool:
        level = getattr(logging, entry.level.upper(), logging.INFO)
        if level < self._min_level:
            return False
        if self._filter_text and self._filter_text not in self._format_entry(entry).lower():
            return False
        return True

    def _refresh_meta(self) -> None:
        meta = self.query_one("#log-meta", Static)
        level = logging.getLevelName(self._min_level)
        follow = "on" if self._follow else "off"
        filter_text = self._filter_text or "-"
        log_path = str(get_log_file_path() or "-")
        meta.update(f"level>={level} | follow={follow} | filter={filter_text} | file={log_path}")

    def _format_entry(self, entry: LogRecordView) -> str:
        return (
            f"{entry.timestamp} {entry.level:<7} {entry.logger_name} "
            f"op={entry.operation} ref={entry.error_ref} {entry.message}"
        )
