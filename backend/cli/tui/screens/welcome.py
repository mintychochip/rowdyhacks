from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Vertical
from cli.tui.docker_orchestrator import has_docker, db_is_running, start_db_container


class WelcomeScreen(Screen):
    def compose(self):
        yield Static("Welcome to OpenHack", id="title")
        if not has_docker():
            yield Static("[red]Docker is not installed.[/red] Please install Docker and Docker Compose first.")
            yield Static("https://docs.docker.com/get-docker/")
        else:
            yield Static("Docker detected.")
            yield Static("Let's get your hackathon platform set up.")
        with Vertical():
            if has_docker():
                yield Button("Start Setup", id="next", variant="primary")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "next":
            if not await db_is_running():
                result = self.query_one("#title", Static)
                result.update("Starting database container...")
                ok, msg = await start_db_container()
                if not ok:
                    result.update(f"[red]Failed to start DB: {msg}[/red]")
                    return
            self.app.push_screen("database")
