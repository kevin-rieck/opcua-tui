from __future__ import annotations

from textual.widgets import Static


class SubscriptionPanel(Static):
    DEFAULT_CSS = """
    SubscriptionPanel {
        border: solid $success;
        background: $surface;
        padding: 1 2;
        height: auto;
    }

    SubscriptionPanel .sub-heading {
        text-style: bold;
    }

    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def compose(self):
        yield Static("Node Subscription", classes="sub-heading")
        yield Static("Target: -", id="sub-target")
        yield Static("Toggle: Ctrl+S", id="sub-hotkey")
        yield Static("", id="sub-feedback")

    def render_from_state(self, inspector_state, subscriptions_state) -> None:
        target = self.query_one("#sub-target", Static)
        hotkey = self.query_one("#sub-hotkey", Static)
        feedback = self.query_one("#sub-feedback", Static)

        node_id = inspector_state.node_id
        attrs = inspector_state.attributes
        if not node_id:
            target.update("Target: select a node")
            hotkey.update("Toggle: Ctrl+S")
            feedback.update("Select a Variable node in Address Space to toggle live updates.")
            return

        target.update(f"Target: {node_id}")
        hotkey.update("Toggle: Ctrl+S")
        is_variable = attrs is not None and attrs.node_class == "Variable"
        item = subscriptions_state.items_by_node_id.get(node_id)
        is_active = item.active if item is not None else False
        is_subscribing = node_id in subscriptions_state.subscribing
        is_unsubscribing = node_id in subscriptions_state.unsubscribing

        if not is_variable:
            feedback.update("Subscriptions are available for Variable nodes only.")
            return

        if is_subscribing:
            feedback.update("[italic]Subscribing...[/]")
        elif is_unsubscribing:
            feedback.update("[italic]Unsubscribing...[/]")
        elif item and item.error:
            feedback.update(f"[red]{item.error}[/]")
        elif is_active:
            feedback.update("[green]Live updates active.[/]")
        else:
            feedback.update("Press Ctrl+S to start live value updates.")
