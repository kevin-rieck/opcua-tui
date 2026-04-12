from rich.spinner import Spinner

from opcua_tui.domain.models import OperationActivity
from opcua_tui.ui.widgets.status_bar import StatusBar


class CapturingStatusBar(StatusBar):
    def __init__(self) -> None:
        self.refresh_calls = 0
        super().__init__()

    def refresh(self, *args, **kwargs) -> None:
        self.refresh_calls += 1


def test_status_bar_render_status_updates_display_text() -> None:
    bar = CapturingStatusBar()
    bar.render_status("Connected")
    assert bar.render() == "Connected"


def test_status_bar_render_status_shows_spinner_when_loading() -> None:
    bar = CapturingStatusBar()
    bar.SPINNER_DELAY_SECONDS = 0.0
    activity = OperationActivity(
        op_id="op-1",
        kind="browse_children",
        label="Loading children for n1",
        scope="tree",
        started_at=1.0,
    )
    bar.render_status("ignored", activities=[activity, activity])
    renderable = bar.render()
    assert isinstance(renderable, Spinner)
    assert str(renderable.text) == "Loading children for n1 (+1)"


def test_status_bar_spinner_tick_advances_frame_while_loading() -> None:
    bar = CapturingStatusBar()
    bar.SPINNER_DELAY_SECONDS = 0.0
    activity = OperationActivity(
        op_id="op-1",
        kind="browse_root",
        label="Loading root nodes",
        scope="tree",
        started_at=1.0,
    )
    bar.render_status("ignored", activities=[activity])
    first_renderable = bar.render()
    initial_refreshes = bar.refresh_calls

    bar._on_spinner_tick()
    second_renderable = bar.render()

    assert isinstance(first_renderable, Spinner)
    assert second_renderable is first_renderable
    assert bar.refresh_calls == initial_refreshes + 1


def test_status_bar_render_status_resets_to_plain_text_when_not_loading() -> None:
    bar = CapturingStatusBar()
    bar.SPINNER_DELAY_SECONDS = 0.0
    bar.SPINNER_MIN_VISIBLE_SECONDS = 0.0
    activity = OperationActivity(
        op_id="op-1",
        kind="browse_root",
        label="Loading root nodes",
        scope="tree",
        started_at=1.0,
    )
    bar.render_status("Loading root nodes", activities=[activity])
    bar._on_spinner_tick()

    bar.render_status("Loaded 3 root nodes", activities=[])

    assert bar.render() == "Loaded 3 root nodes"
