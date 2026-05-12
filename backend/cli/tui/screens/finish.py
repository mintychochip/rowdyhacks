from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Vertical
from cli.tui.docker_orchestrator import (
    start_all_services,
    build_frontend,
    health_check,
    env_path,
    repo_root,
)


class FinishScreen(Screen):
    def compose(self):
        yield Static("Launch OpenHack", id="title")
        yield Static("Ready to build and start the full stack.")
        yield Button("Build & Launch", id="launch", variant="primary")
        yield Static("", id="result")
        with Vertical():
            yield Button("Back", id="back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "launch":
            self.run_worker(self._launch())
        elif event.button.id == "back":
            self.app.pop_screen()

    async def _launch(self):
        result = self.query_one("#result", Static)
        result.update("[blue]Building frontend...[/blue]")

        ok, msg = await build_frontend()
        if not ok:
            result.update(f"[red]Frontend build failed:[/red] {msg}")
            return

        result.update("[blue]Starting all services...[/blue]")
        ok, msg = await start_all_services()
        if not ok:
            result.update(f"[red]Failed to start services:[/red] {msg}")
            return

        result.update("[blue]Waiting for backend health check...[/blue]")
        ok, msg = await health_check()
        if not ok:
            result.update(f"[yellow]Services started but health check failed:[/yellow] {msg}")
        else:
            result.update("[green]OpenHack is running![/green]")

        root = repo_root()
        env_file = env_path()
        lines = [
            "",
            "[bold]Your OpenHack instance is ready:[/bold]",
            "  Main Site (nginx):  http://localhost",
            "  Frontend direct:    http://localhost:3000",
            "  API Docs:           http://localhost:8000/docs",
            "  Health:             http://localhost:8000/api/monitoring/health",
            f"  .env file:          {env_file}",
            "",
            "To manage your instance:",
            f"  cd {root}",
            "  docker compose ps",
            "  docker compose logs -f backend",
            "",
            "To update later:",
            "  ./scripts/update.sh",
        ]
        result.update("\n".join(lines))
