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


class FakeButton:
    def __init__(self) -> None:
        self.label = ""
        self.disabled = False


class HarnessSubscriptionPanel(SubscriptionPanel):
    def __init__(self) -> None:
        super().__init__()
        self._target = FakeStatic()
        self._button = FakeButton()
        self._feedback = FakeStatic()

    def query_one(self, selector_or_type, _type=None):
        if selector_or_type == "#sub-target":
            return self._target
        if selector_or_type == "#sub-toggle":
            return self._button
        if selector_or_type == "#sub-feedback":
            return self._feedback
        return super().query_one(selector_or_type, _type)


def test_subscription_panel_disables_without_selection() -> None:
    panel = HarnessSubscriptionPanel()
    panel.render_from_state(InspectorState(), SubscriptionsState())
    assert panel._button.disabled is True
    assert "select a node" in panel._target.value


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
    assert panel._button.disabled is True
    assert "Variable nodes only" in panel._feedback.value


def test_subscription_panel_shows_unsubscribe_for_active_node() -> None:
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

    assert panel._button.disabled is False
    assert panel._button.label == "Unsubscribe"
