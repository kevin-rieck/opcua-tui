from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from textual.widgets import Tree

from opcua_tui.domain.models import NodeRef


ROOT_NODE_ID = "__root__"
PLACEHOLDER_NODE_ID = "__placeholder__"


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
        self._node_index: dict[str, object] = {}

    def _init_root(self) -> None:
        root = self.root
        root.set_label("Address Space")
        root.data = TreeNodeData(node_id=ROOT_NODE_ID, has_children=True)
        root.expand()

    def replace_with_state(
        self,
        roots: Iterable[NodeRef],
        children_by_parent: dict[str, list[NodeRef]],
        expanded: set[str],
    ) -> None:
        self._init_root()
        self._sync_children(self.root, list(roots), children_by_parent, expanded)
        self._reindex_nodes()

    def _sync_children(
        self,
        parent_widget_node,
        target_children: list[NodeRef],
        children_by_parent: dict[str, list[NodeRef]],
        expanded: set[str],
    ) -> None:
        existing_by_id: dict[str, object] = {}
        for child in list(parent_widget_node.children):
            data = getattr(child, "data", None)
            node_id = getattr(data, "node_id", None)
            if isinstance(node_id, str):
                existing_by_id[node_id] = child

        target_ids = {node.node_id for node in target_children}
        for existing_id, existing_node in existing_by_id.items():
            if existing_id not in target_ids:
                existing_node.remove()

        for target in target_children:
            child_widget_node = existing_by_id.get(target.node_id)
            if child_widget_node is None:
                child_widget_node = parent_widget_node.add(
                    target.display_name,
                    data=TreeNodeData(node_id=target.node_id, has_children=target.has_children),
                    expand=False,
                    allow_expand=target.has_children,
                )
            else:
                child_widget_node.set_label(target.display_name)
                child_widget_node.data = TreeNodeData(
                    node_id=target.node_id, has_children=target.has_children
                )
                child_widget_node.allow_expand = target.has_children

            loaded_children = children_by_parent.get(target.node_id)
            if target.has_children and loaded_children is None:
                self._ensure_placeholder(child_widget_node)
            elif target.has_children:
                self._remove_placeholders(child_widget_node)
                self._sync_children(child_widget_node, loaded_children, children_by_parent, expanded)
            else:
                self._remove_all_children(child_widget_node)
                self._set_expanded_state(child_widget_node, expanded=False)

            self._set_expanded_state(
                child_widget_node,
                expanded=target.has_children and target.node_id in expanded,
            )

    def _ensure_placeholder(self, widget_node) -> None:
        for child in widget_node.children:
            child_data = getattr(child, "data", None)
            if getattr(child_data, "node_id", None) == PLACEHOLDER_NODE_ID:
                return
        widget_node.add(
            "loading...",
            data=TreeNodeData(node_id=PLACEHOLDER_NODE_ID, has_children=False),
            allow_expand=False,
        )

    def _remove_placeholders(self, widget_node) -> None:
        for child in list(widget_node.children):
            child_data = getattr(child, "data", None)
            if getattr(child_data, "node_id", None) == PLACEHOLDER_NODE_ID:
                child.remove()

    def _remove_all_children(self, widget_node) -> None:
        for child in list(widget_node.children):
            child.remove()

    def _set_expanded_state(self, widget_node, expanded: bool) -> None:
        current_state = getattr(widget_node, "is_expanded", None)
        if current_state is None:
            current_state = getattr(widget_node, "expanded", None)

        if current_state is expanded:
            return
        if expanded:
            widget_node.expand()
        else:
            widget_node.collapse()

    def _reindex_nodes(self) -> None:
        index: dict[str, object] = {}

        def walk(node) -> None:
            data = getattr(node, "data", None)
            node_id = getattr(data, "node_id", None)
            if isinstance(node_id, str):
                index[node_id] = node
            for child in node.children:
                walk(child)

        walk(self.root)
        self._node_index = index

    def find_node_by_id(self, target_id: str):
        if not self._node_index:
            self._reindex_nodes()
        return self._node_index.get(target_id)
