from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, DirectoryTree, Input, Static


class PathPickerScreen(ModalScreen[str | None]):
    file_name: reactive[str] = reactive("")
    current_dir: reactive[str] = reactive("")
    error_text: reactive[str] = reactive("")

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "submit", "Select"),
    ]

    CSS = """
    PathPickerScreen {
        align: center middle;
    }

    #path-picker-dialog {
        layout: vertical;
        width: 84;
        max-width: 90vw;
        height: 90vh;
        max-height: 95vh;
        background: $panel;
        border: round $primary;
    }

    #path-picker-body {
        layout: vertical;
        height: 1fr;
        padding: 1 2;
    }

    #path-picker-title {
        text-style: bold;
        margin-bottom: 1;
    }

    #path-picker-hint {
        color: $text-muted;
        margin-bottom: 1;
    }

    #path-picker-current-dir {
        color: $text-muted;
        margin: 1 0;
        height: auto;
    }

    #path-picker-tree {
        height: 1fr;
        min-height: 12;
        border: round $primary-darken-2;
        background: $surface;
    }

    #path-picker-filename {
        margin-top: 1;
    }

    #path-picker-error {
        color: $error;
        min-height: 1;
        margin-top: 1;
    }

    Horizontal#path-picker-actions {
        align-horizontal: right;
        height: auto;
        padding: 1 2;
        border-top: solid $primary-darken-2;
    }
    """

    def __init__(
        self,
        *,
        title: str,
        start_dir: str,
        extension_hints: tuple[str, ...] = (),
        initial_filename: str = "",
    ) -> None:
        super().__init__()
        self._title = title
        self._start_dir = self._coerce_start_dir(start_dir)
        self._extension_hints = extension_hints
        self._suppress_form_events = False
        self._initial_current_dir = str(self._start_dir)
        self._initial_filename = initial_filename.strip()

    def compose(self) -> ComposeResult:
        hint = (
            "Choose a directory and provide filename."
            if not self._extension_hints
            else f"Suggested extensions: {', '.join(self._extension_hints)}"
        )
        with Container(id="path-picker-dialog"):
            with Vertical(id="path-picker-body"):
                yield Static(self._title, id="path-picker-title")
                yield Static(hint, id="path-picker-hint")
                yield Static("", id="path-picker-current-dir")
                yield DirectoryTree(str(self._start_dir), id="path-picker-tree")
                yield Input(
                    value=self.file_name,
                    placeholder="Filename is required",
                    id="path-picker-filename",
                )
                yield Static("", id="path-picker-error")
            with Horizontal(id="path-picker-actions"):
                yield Button("Cancel", id="path-picker-cancel")
                yield Button("Select", id="path-picker-submit", variant="primary")

    def on_mount(self) -> None:
        self.current_dir = self._initial_current_dir
        self.file_name = self._initial_filename
        self._refresh_view()
        self.query_one("#path-picker-tree", DirectoryTree).focus()

    def watch_file_name(self, _file_name: str) -> None:
        if not self.is_mounted:
            return
        self._refresh_view()

    def watch_current_dir(self, _current_dir: str) -> None:
        if not self.is_mounted:
            return
        self._refresh_view()

    def watch_error_text(self, _error_text: str) -> None:
        if not self.is_mounted:
            return
        self._refresh_view()

    def _refresh_view(self) -> None:
        if not self.is_mounted:
            return
        dir_widget = self.query_one("#path-picker-current-dir", Static)
        filename_input = self.query_one("#path-picker-filename", Input)
        error_widget = self.query_one("#path-picker-error", Static)
        submit_button = self.query_one("#path-picker-submit", Button)
        valid = self._validate_filename(self.file_name.strip()) is None

        self._suppress_form_events = True
        try:
            if filename_input.value != self.file_name:
                filename_input.value = self.file_name
        finally:
            self._suppress_form_events = False

        dir_widget.update(f"Current directory: {self.current_dir}")
        error_widget.update(self.error_text)
        submit_button.disabled = not valid

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        self.current_dir = str(event.path.parent)
        self.file_name = event.path.name
        self.error_text = ""

    def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        self.current_dir = str(event.path)
        self.error_text = ""

    def on_input_changed(self, event: Input.Changed) -> None:
        if self._suppress_form_events:
            return
        if event.input.id != "path-picker-filename":
            return
        self.file_name = event.value

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "path-picker-cancel":
            self.dismiss(None)
            return
        if event.button.id == "path-picker-submit":
            await self._submit()

    def action_cancel(self) -> None:
        self.dismiss(None)

    async def action_submit(self) -> None:
        await self._submit()

    async def _submit(self) -> None:
        name = self.file_name.strip()
        validation_error = self._validate_filename(name)
        if validation_error is not None:
            self.error_text = validation_error
            return
        self.error_text = ""
        selected = str((Path(self.current_dir) / name).expanduser())
        self.dismiss(selected)

    def _validate_filename(self, name: str) -> str | None:
        name = name.strip()
        if not name:
            return "Filename is required"
        if name in {".", ".."}:
            return "Selection must resolve to a file path"
        if Path(name).name != name:
            return "Selection must resolve to a file path"
        return None

    def _coerce_start_dir(self, start_dir: str) -> Path:
        candidate = Path(start_dir).expanduser()
        if candidate.is_dir():
            return candidate
        if candidate.exists():
            return candidate.parent
        return Path.home()
