from textual.app import App

from cli.tui.screens.welcome import WelcomeScreen
from cli.tui.screens.dashboard import DashboardScreen


class TuiApp(App):
    CSS_PATH = None
    SCREENS = {
        "welcome": WelcomeScreen,
        "dashboard": DashboardScreen,
    }

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+r", "refresh", "Refresh"),
        ("?", "help", "Help"),
    ]

    CSS = """
    Screen { align: center middle; }
    """

    def __init__(self, mode: str = "dashboard", **kwargs):
        super().__init__(**kwargs)
        self.mode = mode

    def on_mount(self):
        if self.mode == "setup":
            self.push_screen("welcome")
        else:
            self.push_screen("dashboard")

    async def action_refresh(self):
        screen = self.screen
        if hasattr(screen, "action_refresh"):
            await screen.action_refresh()

    async def action_help(self):
        self.notify("Ctrl+Q: Quit | Ctrl+R: Refresh | Tab: Next focus | Esc: Close modal")
