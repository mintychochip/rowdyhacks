from textual.app import App

from cli.tui.screens.welcome import WelcomeScreen
from cli.tui.screens.dashboard import DashboardScreen


class TuiApp(App):
    CSS_PATH = None
    SCREENS = {
        "welcome": WelcomeScreen,
        "dashboard": DashboardScreen,
    }

    def __init__(self, mode: str = "dashboard", **kwargs):
        super().__init__(**kwargs)
        self.mode = mode

    def on_mount(self):
        if self.mode == "setup":
            self.push_screen("welcome")
        else:
            self.push_screen("dashboard")
