from textual.containers import Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static, Input, Button
import re


class ConfigFormWidget(Vertical):
    class Submitted(Message):
        def __init__(self, values: dict[str, str]) -> None:
            self.values = values
            super().__init__()

    values = reactive({})

    def __init__(self, fields=None, **kwargs):
        super().__init__(**kwargs)
        self._fields = fields or []
        self._inputs: dict[str, Input] = {}
        self._submitted_values: list[dict] = []

    def compose(self):
        for key, label, ftype, default, required in self._fields:
            yield Static(f"{label}{' *' if required else ''}")
            inp = Input(value=default or "", id=f"input-{key}", placeholder=label)
            yield inp
            self._inputs[key] = inp
        yield Button("Submit", id="submit", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit":
            values = self.get_values()
            self._submitted_values.append(values)
            self.post_message(self.Submitted(values))

    def get_values(self) -> dict[str, str]:
        return {k: v.value for k, v in self._inputs.items()}

    def set_value(self, key: str, value: str) -> None:
        if key in self._inputs:
            self._inputs[key].value = value

    def validate(self) -> list[str]:
        errors = []
        for key, label, ftype, default, required in self._fields:
            val = self._inputs[key].value
            if required and not val:
                errors.append(f"{label} is required")
                continue
            if ftype == "email" and val:
                if not re.match(r"^[^@]+@[^@]+\.[^@]+$", val):
                    errors.append(f"{label} must be a valid email")
            elif ftype == "color" and val:
                if not re.match(r"^#[0-9a-fA-F]{6}$", val):
                    errors.append(f"{label} must be a hex color (#RRGGBB)")
            elif ftype == "int" and val:
                try:
                    int(val)
                except ValueError:
                    errors.append(f"{label} must be an integer")
        return errors
