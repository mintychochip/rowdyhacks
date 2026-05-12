from textual.screen import ModalScreen
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, Button


class ConfirmDialog(ModalScreen[bool]):
    def __init__(self, message: str, danger: bool = False) -> None:
        self._message = message
        self._danger = danger
        super().__init__()

    def compose(self):
        with Vertical(id="dialog"):
            yield Static(self._message)
            with Horizontal():
                variant = "error" if self._danger else "primary"
                yield Button("Confirm", id="confirm", variant=variant)
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)
