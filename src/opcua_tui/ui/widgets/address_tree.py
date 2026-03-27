from __future__ import annotations

from dataclasses import dataclass

from textual.widgets import Tree


@dataclass(slots=True)
class TreeNodeData:
    node_id: str
    has_children: bool


class AddressTree(Tree[TreeNodeData]):
    DEFAULT_CSS = """
    AddressTree {
        width: 1fr;
        border: solid $primary;
        min-width: 30;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__("Address Space", **kwargs)
        self.show_root = True

    def replace_with_state(self, roots, children_by_parent, expanded) -> None:
        self.clear()
        root = self.root
        root.set_label("Address Space")
        root.data = TreeNodeData(node_id="__root__", has_children=True)
        root.expand()

        def add_children(parent_widget_node, parent_id):
            for node in roots if parent_id is None else children_by_parent.get(parent_id, []):
                child = parent_widget_node.add(
                    node.display_name,
                    data=TreeNodeData(node_id=node.node_id, has_children=node.has_children),
                    expand=False,
                    allow_expand=node.has_children,
                )
                if node.has_children:
                    child.add(
                        "loading...",
                        data=TreeNodeData(node_id="__placeholder__", has_children=False),
                    )
                    if node.node_id in expanded:
                        child.expand()
                        add_children(child, node.node_id)

        add_children(root, None)

    def find_node_by_id(self, target_id: str):
        def walk(node):
            if node.data and getattr(node.data, "node_id", None) == target_id:
                return node
            for child in node.children:
                found = walk(child)
                if found:
                    return found
            return None

        return walk(self.root)
