from __future__ import annotations

from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Button, Input, Static


class WriteValuePanel(Static):
    DEFAULT_CSS = """
    WriteValuePanel {
        border: solid $secondary;
        padding: 1 2;
        height: auto;
    }

    WriteValuePanel .write-heading {
        text-style: bold;
    }

    WriteValuePanel .write-input-row {
        height: auto;
    }

    WriteValuePanel Button {
        margin-top: 1;
    }
    """

    class SubmitRequested(Message):
        def __init__(self, value_text: str) -> None:
            super().__init__()
            self.value_text = value_text

    def compose(self):
        yield Static("Write Node Value", classes="write-heading")
        yield Static("Target: -", id="write-target")
        with Vertical(classes="write-input-row"):
            yield Input(placeholder="Enter value", id="write-input")
            yield Button("Write", variant="primary", id="write-submit")
        yield Static("", id="write-feedback")

    def render_from_state(self, inspector_state) -> None:
        target = self.query_one("#write-target", Static)
        input_widget = self.query_one("#write-input", Input)
        submit = self.query_one("#write-submit", Button)
        feedback = self.query_one("#write-feedback", Static)

        node_id = inspector_state.node_id
        variant_hint = None
        if inspector_state.value and inspector_state.value.variant_type:
            variant_hint = inspector_state.value.variant_type
        elif inspector_state.attributes and inspector_state.attributes.data_type:
            variant_hint = inspector_state.attributes.data_type

        if node_id:
            target.update(f"Target: {node_id}")
            input_widget.placeholder = (
                f"Enter value ({variant_hint})" if variant_hint else "Enter value"
            )
            locked = inspector_state.loading or inspector_state.writing
            input_widget.disabled = locked
            submit.disabled = locked
        else:
            target.update("Target: select a node")
            input_widget.placeholder = "Select a node to enable writing"
            input_widget.disabled = True
            submit.disabled = True

        if inspector_state.write_error:
            feedback.update(f"[red]{inspector_state.write_error}[/]")
        elif inspector_state.writing:
            feedback.update("[italic]Writing value...[/]")
        elif node_id:
            helper = "Enter a new value and press [b]Enter[/] or [b]Write[/]."
            if variant_hint:
                helper += f" Type hint: {variant_hint}."
            feedback.update(helper)
        else:
            feedback.update("")

    def focus_input(self) -> None:
        self.query_one("#write-input", Input).focus()

    def clear_input(self) -> None:
        self.query_one("#write-input", Input).value = ""

    def _submit(self) -> None:
        input_widget = self.query_one("#write-input", Input)
        self.post_message(self.SubmitRequested(value_text=input_widget.value))

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "write-submit":
            return
        self._submit()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "write-input":
            return
        self._submit()
