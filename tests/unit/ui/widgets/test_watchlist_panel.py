from datetime import datetime

from opcua_tui.domain.models import SubscriptionItemState, SubscriptionsState
from opcua_tui.ui.widgets.watchlist_panel import WatchlistPanel


class CapturingWatchlistPanel(WatchlistPanel):
    def __init__(self) -> None:
        super().__init__()
        self.last_text = ""

    def update(self, renderable="") -> None:
        self.last_text = str(renderable)


def test_watchlist_panel_renders_empty_state() -> None:
    panel = CapturingWatchlistPanel()
    panel.render_from_state(SubscriptionsState())
    assert "No active subscriptions" in panel.last_text


def test_watchlist_panel_renders_items() -> None:
    panel = CapturingWatchlistPanel()
    state = SubscriptionsState()
    state.items_by_node_id["n1"] = SubscriptionItemState(
        node_id="n1",
        display_name="Temp",
        active=True,
        last_value="21.2",
        variant_type="Double",
        status_code="Good",
        source_timestamp=datetime(2026, 1, 1, 0, 0, 0),
        update_count=3,
    )

    panel.render_from_state(state)

    assert "Temp" in panel.last_text
    assert "Value: 21.2" in panel.last_text
    assert "Updates: 3" in panel.last_text
