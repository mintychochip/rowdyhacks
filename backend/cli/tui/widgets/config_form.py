"""Config form widget for TUI screens."""

from textual.widget import Widget
from textual.widgets import Static, Input, Select
from textual.containers import Vertical


class ConfigFormWidget(Widget):
    def __init__(self, fields, id=None):
        super().__init__(id=id)
        self.fields = fields
        self._values = {}
        self._inputs = {}

    def compose(self):
        with Vertical():
            for key, label, field_type, default, required in self.fields:
                yield Static(f"{label}:")
                if field_type == "select":
                    options = [
                        ("organizer", "organizer"),
                        ("participant", "participant"),
                        ("judge", "judge"),
                        ("volunteer", "volunteer"),
                    ]
                    widget = Select(options, value=default or "organizer", id=f"field-{key}")
                else:
                    widget = Input(value=default or "", id=f"field-{key}")
                self._inputs[key] = widget
                yield widget

    def validate(self):
        errors = []
        for key, label, field_type, default, required in self.fields:
            widget = self._inputs.get(key)
            if widget is None:
                continue
            value = widget.value
            if required and (value is None or str(value).strip() == ""):
                errors.append(f"{label} is required")
        return errors

    def get_values(self):
        values = {}
        for key, label, field_type, default, required in self.fields:
            widget = self._inputs.get(key)
            if widget is not None:
                values[key] = widget.value
        return values
