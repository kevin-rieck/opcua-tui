from opcua_tui.ui.widgets.status_bar import StatusBar


class CapturingStatusBar(StatusBar):
    def __init__(self) -> None:
        super().__init__()
        self.last_text = ""

    def update(self, renderable="") -> None:
        self.last_text = str(renderable)


def test_status_bar_render_status_updates_display_text() -> None:
    bar = CapturingStatusBar()
    bar.render_status("Connected")
    assert bar.last_text == "Connected"
