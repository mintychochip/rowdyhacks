from textual.screen import Screen
from textual.widgets import TabbedContent, TabPane
from cli.tui.widgets.status_bar import StatusBar
from cli.tui.screens.overview import OverviewTab
from cli.tui.screens.hackathons_tab import HackathonsTab
from cli.tui.screens.users_tab import UsersTab


class DashboardScreen(Screen):
    def compose(self):
        with TabbedContent():
            with TabPane("Overview", id="overview"):
                yield OverviewTab()
            with TabPane("Hackathons", id="hackathons"):
                yield HackathonsTab()
            with TabPane("Users", id="users"):
                yield UsersTab()
            yield TabPane("Registrations", id="registrations")
            yield TabPane("Settings", id="settings")
        yield StatusBar(id="status-bar")

    def on_mount(self):
        self.query_one("#status-bar", StatusBar).set_connected(True)
