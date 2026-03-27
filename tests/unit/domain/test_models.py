from dataclasses import FrozenInstanceError

import pytest

from opcua_tui.domain.models import (
    AppState,
    ConnectModalState,
    ConnectParams,
    DataValueView,
    NodeAttributes,
    NodeRef,
    ServerInfo,
    SessionInfo,
)


def test_frozen_model_construction_contracts() -> None:
    params = ConnectParams(endpoint="opc.tcp://localhost:4840")
    server = ServerInfo(application_name="Demo")
    session = SessionInfo(session_id="s1", endpoint=params.endpoint, server=server)
    node = NodeRef(node_id="n1", display_name="Node 1", node_class="Object", has_children=True)
    attrs = NodeAttributes(
        node_id="n1", display_name="Node 1", browse_name="Node1", node_class="Object"
    )
    value = DataValueView(node_id="n1", value={"x": 1}, variant_type="dict", status_code="Good")

    assert session.server.application_name == "Demo"
    assert node.has_children is True
    assert attrs.display_name == "Node 1"
    assert value.value == {"x": 1}
    assert params.security_mode.value == "none"
    assert params.security_policy.value == "none"
    assert params.authentication_mode.value == "anonymous"


def test_frozen_models_are_immutable() -> None:
    params = ConnectParams(endpoint="opc.tcp://localhost:4840")
    with pytest.raises(FrozenInstanceError):
        params.endpoint = "opc.tcp://other:4840"


def test_app_state_defaults_are_independent_per_instance() -> None:
    left = AppState()
    right = AppState()

    left.browser.roots.append(NodeRef(node_id="n1", display_name="Node 1", node_class="Object"))
    left.browser.loading.add("n1")
    left.browser.children_by_parent["n1"] = []

    assert right.browser.roots == []
    assert right.browser.loading == set()
    assert right.browser.children_by_parent == {}


def test_connect_modal_state_owns_its_default_params() -> None:
    left = ConnectModalState()
    right = ConnectModalState()

    left.params = ConnectParams(endpoint="opc.tcp://left:4840")

    assert right.params.endpoint == ""
