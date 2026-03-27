from opcua_tui.domain.models import NodeRef
from opcua_tui.ui.widgets.address_tree import AddressTree


def test_address_tree_replace_and_find_node_by_id() -> None:
    tree = AddressTree()
    roots = [
        NodeRef(node_id="i=85", display_name="Objects", node_class="Object", has_children=True)
    ]
    children_by_parent = {
        "i=85": [
            NodeRef(
                node_id="ns=2;s=Machine",
                display_name="Machine",
                node_class="Object",
                has_children=False,
            ),
        ]
    }
    expanded = {"i=85"}

    tree.replace_with_state(roots=roots, children_by_parent=children_by_parent, expanded=expanded)

    root_node = tree.find_node_by_id("__root__")
    objects = tree.find_node_by_id("i=85")
    machine = tree.find_node_by_id("ns=2;s=Machine")
    placeholder = tree.find_node_by_id("__placeholder__")

    assert root_node is not None
    assert objects is not None
    assert machine is not None
    assert placeholder is None
