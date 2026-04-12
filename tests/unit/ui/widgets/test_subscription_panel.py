from opcua_tui.domain.models import (
    InspectorState,
    NodeAttributes,
    SubscriptionItemState,
    SubscriptionsState,
)
from opcua_tui.ui.widgets.subscription_panel import SubscriptionPanel


class FakeStatic:
    def __init__(self) -> None:
        self.value = ""

    def update(self, text: str) -> None:
        self.value = text


class HarnessSubscriptionPanel(SubscriptionPanel):
    def __init__(self) -> None:
        super().__init__()
        self._target = FakeStatic()
        self._hotkey = FakeStatic()
        self._feedback = FakeStatic()

    def query_one(self, selector_or_type, _type=None):
        if selector_or_type == "#sub-target":
            return self._target
        if selector_or_type == "#sub-hotkey":
            return self._hotkey
        if selector_or_type == "#sub-feedback":
            return self._feedback
        return super().query_one(selector_or_type, _type)


def test_subscription_panel_disables_without_selection() -> None:
    panel = HarnessSubscriptionPanel()
    panel.render_from_state(InspectorState(), SubscriptionsState())
    assert "select a node" in panel._target.value
    assert "Ctrl+S" in panel._hotkey.value
    assert "Select a Variable node" in panel._feedback.value


def test_subscription_panel_only_allows_variables() -> None:
    panel = HarnessSubscriptionPanel()
    state = InspectorState(
        node_id="n1",
        attributes=NodeAttributes(
            node_id="n1",
            display_name="N1",
            browse_name="N1",
            node_class="Object",
        ),
    )
    panel.render_from_state(state, SubscriptionsState())
    assert "Variable nodes only" in panel._feedback.value


def test_subscription_panel_shows_active_state_for_subscribed_node() -> None:
    panel = HarnessSubscriptionPanel()
    state = InspectorState(
        node_id="n1",
        attributes=NodeAttributes(
            node_id="n1",
            display_name="Temp",
            browse_name="Temp",
            node_class="Variable",
        ),
    )
    subscriptions = SubscriptionsState()
    subscriptions.items_by_node_id["n1"] = SubscriptionItemState(
        node_id="n1",
        display_name="Temp",
        active=True,
    )

    panel.render_from_state(state, subscriptions)

    assert "Live updates active." in panel._feedback.value
