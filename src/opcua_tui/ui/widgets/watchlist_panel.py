from __future__ import annotations

from textual.widgets import Static


class WatchlistPanel(Static):
    DEFAULT_CSS = """
    WatchlistPanel {
        width: 1fr;
        border: solid $warning;
        background: $surface;
        padding: 1 2;
        min-width: 36;
    }
    """

    def render_from_state(self, subscriptions_state) -> None:
        items = list(subscriptions_state.items_by_node_id.values())
        if not items:
            self.update("Watchlist\n\nNo active subscriptions.")
            return

        items.sort(key=lambda item: item.display_name.lower())
        lines = ["[b]Watchlist[/]"]
        for item in items:
            ts = item.source_timestamp.isoformat() if item.source_timestamp else "-"
            value = item.last_value if item.last_value is not None else "-"
            variant = item.variant_type or "-"
            status = item.status_code or "-"
            lines.extend(
                [
                    "",
                    f"[b]{item.display_name}[/]",
                    f"Node: {item.node_id}",
                    f"Value: {value}",
                    f"Type: {variant}",
                    f"Status: {status}",
                    f"Ts: {ts}",
                    f"Updates: {item.update_count}",
                ]
            )
            if item.error:
                lines.append(f"[red]Error: {item.error}[/]")

        self.update("\n".join(lines))
