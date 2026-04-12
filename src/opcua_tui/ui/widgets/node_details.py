from textual.widgets import Static


class NodeDetails(Static):
    DEFAULT_CSS = """
    NodeDetails {
        width: 2fr;
        height: 1fr;
        border: solid $accent;
        background: $surface;
        padding: 1 2;
    }
    """

    def render_from_state(self, inspector_state) -> None:
        if inspector_state.error:
            self.update(f"[bold red]Error[/]\n{inspector_state.error}")
            return
        if inspector_state.loading:
            self.update("[italic]Loading node details...[/]")
            return
        if not inspector_state.node_id:
            self.update("Select a node from the tree.")
            return

        attrs = inspector_state.attributes
        value = inspector_state.value
        lines = [f"[b]Node ID:[/] {inspector_state.node_id}"]
        if attrs:
            lines.extend(
                [
                    "",
                    "[b]Attributes[/]",
                    f"Display Name: {attrs.display_name}",
                    f"Browse Name: {attrs.browse_name}",
                    f"Class: {attrs.node_class}",
                    f"Description: {attrs.description or '-'}",
                    f"Data Type: {attrs.data_type or '-'}",
                    f"Access: {attrs.access_level or '-'}",
                ]
            )
        if value:
            lines.extend(
                [
                    "",
                    "[b]Value[/]",
                    f"Current Value: {value.value}",
                    f"Variant Type: {value.variant_type or '-'}",
                    f"Status Code: {value.status_code}",
                ]
            )
        self.update("\n".join(lines))
