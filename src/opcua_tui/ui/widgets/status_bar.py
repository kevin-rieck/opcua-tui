from textual.widgets import Static


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

    def render_status(self, text: str) -> None:
        self.update(text)
