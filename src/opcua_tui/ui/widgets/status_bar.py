from __future__ import annotations

from time import monotonic

from rich.spinner import Spinner
from textual.widgets import Static

from opcua_tui.domain.models import OperationActivity


class StatusBar(Static):
    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        dock: bottom;
        background: $surface;
        color: $text;
        padding: 0 1;
    }
    """
    SPINNER_DELAY_SECONDS = 0.2
    SPINNER_MIN_VISIBLE_SECONDS = 0.4

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._status_text = ""
        self._activities: list[OperationActivity] = []
        self._spinner: Spinner | None = None
        self._active_since: float | None = None
        self._visible_since: float | None = None
        self._show_spinner = False

    def on_mount(self) -> None:
        self.set_interval(0.12, self._on_spinner_tick)

    def render_status(
        self,
        text: str,
        *,
        activities: list[OperationActivity] | None = None,
    ) -> None:
        self._status_text = text
        self._activities = activities or []
        self._refresh_text(force=True)

    def _on_spinner_tick(self) -> None:
        was_visible = self._show_spinner
        self._refresh_text(force=False)
        if self._show_spinner and self._spinner is not None:
            self.refresh()
        elif was_visible != self._show_spinner:
            self.refresh()

    def _refresh_text(self, *, force: bool) -> None:
        now = monotonic()
        primary = self._primary_activity()

        if primary is None:
            self._active_since = None
            if self._show_spinner and self._visible_since is not None:
                if now - self._visible_since < self.SPINNER_MIN_VISIBLE_SECONDS:
                    return
            self._show_spinner = False
            self._visible_since = None
            self._spinner = None
            if force:
                self.refresh()
            return

        if self._active_since is None:
            self._active_since = now

        if not self._show_spinner:
            if now - self._active_since < self.SPINNER_DELAY_SECONDS:
                if force:
                    self.refresh()
                return
            self._show_spinner = True
            self._visible_since = now

        spinner_text = primary.label
        if len(self._activities) > 1:
            spinner_text = f"{spinner_text} (+{len(self._activities) - 1})"
        if self._spinner is None or str(self._spinner.text) != spinner_text:
            self._spinner = Spinner("dots", text=spinner_text)
        if force:
            self.refresh()

    def _primary_activity(self) -> OperationActivity | None:
        if not self._activities:
            return None
        return max(self._activities, key=lambda activity: activity.started_at)

    def render(self):
        if self._spinner is not None and self._show_spinner:
            return self._spinner
        return self._status_text
