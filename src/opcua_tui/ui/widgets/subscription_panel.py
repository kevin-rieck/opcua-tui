from __future__ import annotations

from textual.message import Message
from textual.widgets import Button, Static


class SubscriptionPanel(Static):
    DEFAULT_CSS = """
    SubscriptionPanel {
        border: solid $success;
        padding: 1 2;
        height: auto;
    }

    SubscriptionPanel .sub-heading {
        text-style: bold;
    }

    SubscriptionPanel Button {
        margin-top: 1;
    }
    """

    class SubscribeRequested(Message):
        def __init__(self, node_id: str, display_name: str) -> None:
            super().__init__()
            self.node_id = node_id
            self.display_name = display_name

    class UnsubscribeRequested(Message):
        def __init__(self, node_id: str) -> None:
            super().__init__()
            self.node_id = node_id

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._node_id: str | None = None
        self._display_name: str = ""
        self._is_active = False

    def compose(self):
        yield Static("Node Subscription", classes="sub-heading")
        yield Static("Target: -", id="sub-target")
        yield Button("Subscribe", variant="success", id="sub-toggle")
        yield Static("", id="sub-feedback")

    def render_from_state(self, inspector_state, subscriptions_state) -> None:
        target = self.query_one("#sub-target", Static)
        toggle = self.query_one("#sub-toggle", Button)
        feedback = self.query_one("#sub-feedback", Static)

        node_id = inspector_state.node_id
        attrs = inspector_state.attributes
        self._node_id = node_id
        self._display_name = attrs.display_name if attrs and attrs.display_name else (node_id or "")
        if not node_id:
            self._is_active = False
            target.update("Target: select a node")
            toggle.label = "Subscribe"
            toggle.disabled = True
            feedback.update("")
            return

        target.update(f"Target: {node_id}")
        is_variable = attrs is not None and attrs.node_class == "Variable"
        item = subscriptions_state.items_by_node_id.get(node_id)
        is_active = item.active if item is not None else False
        self._is_active = is_active
        is_subscribing = node_id in subscriptions_state.subscribing
        is_unsubscribing = node_id in subscriptions_state.unsubscribing

        if not is_variable:
            toggle.label = "Subscribe"
            toggle.disabled = True
            feedback.update("Subscriptions are available for Variable nodes only.")
            return

        toggle.label = "Unsubscribe" if is_active else "Subscribe"
        toggle.disabled = (
            inspector_state.loading or inspector_state.writing or is_subscribing or is_unsubscribing
        )

        if is_subscribing:
            feedback.update("[italic]Subscribing...[/]")
        elif is_unsubscribing:
            feedback.update("[italic]Unsubscribing...[/]")
        elif item and item.error:
            feedback.update(f"[red]{item.error}[/]")
        elif is_active:
            feedback.update("[green]Live updates active.[/]")
        else:
            feedback.update("Press Subscribe to start live value updates.")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "sub-toggle":
            return
        if not self._node_id:
            return
        if self._is_active:
            self.post_message(self.UnsubscribeRequested(node_id=self._node_id))
            return
        self.post_message(
            self.SubscribeRequested(node_id=self._node_id, display_name=self._display_name)
        )
