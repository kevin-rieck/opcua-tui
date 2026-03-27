from opcua_tui.domain.models import DataValueView, InspectorState, NodeAttributes
from opcua_tui.ui.widgets.node_details import NodeDetails


class CapturingNodeDetails(NodeDetails):
    def __init__(self) -> None:
        super().__init__()
        self.last_text = ""

    def update(self, renderable="") -> None:
        self.last_text = str(renderable)


def test_node_details_renders_error_state() -> None:
    widget = CapturingNodeDetails()
    widget.render_from_state(InspectorState(error="boom"))
    assert "Error" in widget.last_text
    assert "boom" in widget.last_text


def test_node_details_renders_loading_state() -> None:
    widget = CapturingNodeDetails()
    widget.render_from_state(InspectorState(loading=True))
    assert "Loading node details" in widget.last_text


def test_node_details_renders_empty_state() -> None:
    widget = CapturingNodeDetails()
    widget.render_from_state(InspectorState())
    assert "Select a node from the tree." in widget.last_text


def test_node_details_renders_attributes_and_value() -> None:
    widget = CapturingNodeDetails()
    attrs = NodeAttributes(
        node_id="n1",
        display_name="Temperature",
        browse_name="Temperature",
        node_class="Variable",
        description="Room temp",
        data_type="Double",
        access_level="CurrentRead",
    )
    value = DataValueView(node_id="n1", value=21.5, variant_type="float", status_code="Good")
    state = InspectorState(node_id="n1", attributes=attrs, value=value)

    widget.render_from_state(state)

    assert "Node ID" in widget.last_text
    assert "Temperature" in widget.last_text
    assert "Current Value: 21.5" in widget.last_text
