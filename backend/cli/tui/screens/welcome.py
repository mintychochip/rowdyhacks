from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Vertical


class WelcomeScreen(Screen):
    def compose(self):
        yield Static("Welcome to OpenHack", id="title")
        yield Static("Let's get your hackathon platform set up.")
        with Vertical():
            yield Button("Next", id="next", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "next":
            self.app.push_screen("database")
