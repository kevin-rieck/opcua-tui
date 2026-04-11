from opcua_tui.domain.models import DataValueView, InspectorState, NodeAttributes
from opcua_tui.ui.widgets.write_value_panel import WriteValuePanel


class FakeStatic:
    def __init__(self) -> None:
        self.value = ""

    def update(self, text: str) -> None:
        self.value = text


class FakeInput:
    def __init__(self) -> None:
        self.placeholder = ""
        self.disabled = False
        self.value = ""

    def focus(self) -> None:
        return None


class FakeButton:
    def __init__(self) -> None:
        self.disabled = False


class HarnessWriteValuePanel(WriteValuePanel):
    def __init__(self) -> None:
        super().__init__()
        self._target = FakeStatic()
        self._input = FakeInput()
        self._button = FakeButton()
        self._feedback = FakeStatic()

    def query_one(self, selector_or_type, _type=None):
        if selector_or_type == "#write-target":
            return self._target
        if selector_or_type == "#write-input":
            return self._input
        if selector_or_type == "#write-submit":
            return self._button
        if selector_or_type == "#write-feedback":
            return self._feedback
        return super().query_one(selector_or_type, _type)


def test_write_value_panel_message_carries_input_text() -> None:
    message = WriteValuePanel.SubmitRequested(value_text="21.5")
    assert message.value_text == "21.5"


def test_write_value_panel_render_disables_input_without_node() -> None:
    panel = HarnessWriteValuePanel()

    panel.render_from_state(InspectorState())

    assert panel._target.value == "Target: select a node"
    assert panel._input.disabled is True
    assert panel._button.disabled is True


def test_write_value_panel_render_shows_type_hint_and_write_error() -> None:
    panel = HarnessWriteValuePanel()
    state = InspectorState(
        node_id="n1",
        attributes=NodeAttributes(
            node_id="n1",
            display_name="N1",
            browse_name="N1",
            node_class="Variable",
            data_type="Int32",
        ),
        value=DataValueView(node_id="n1", value=1, variant_type="UInt16", status_code="Good"),
        write_error="bad write",
    )

    panel.render_from_state(state)

    assert panel._target.value == "Target: n1"
    assert "UInt16" in panel._input.placeholder
    assert "bad write" in panel._feedback.value


def test_write_value_panel_render_shows_writing_feedback() -> None:
    panel = HarnessWriteValuePanel()
    state = InspectorState(node_id="n1", writing=True)

    panel.render_from_state(state)

    assert panel._input.disabled is True
    assert "Writing value" in panel._feedback.value
