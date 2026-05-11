use crossterm::event::{self, Event, KeyCode, KeyEventKind};
use ratatui::{backend::Backend, Terminal};
use std::time::Duration;

use crate::docker::{check_docker, check_compose, check_ports, ComposeRunner};
use crate::ui::draw;
use crate::wizard::Wizard;

pub enum CurrentScreen {
    Splash,
    Wizard,
    Progress,
    Done,
    Error,
}

pub struct App {
    pub screen: CurrentScreen,
    pub wizard: Wizard,
    pub docker_logs: Vec<String>,
    pub error_message: Option<String>,
    pub should_quit: bool,
}

impl App {
    pub fn new() -> Self {
        Self {
            screen: CurrentScreen::Splash,
            wizard: Wizard::new(),
            docker_logs: vec![],
            error_message: None,
            should_quit: false,
        }
    }

    pub async fn run<B: Backend>(&mut self, terminal: &mut Terminal<B>) -> color_eyre::Result<()> {
        let mut last_tick = tokio::time::Instant::now();
        let tick_rate = Duration::from_millis(100);

        while !self.should_quit {
            terminal.draw(|f| draw(f, self))?;

            let timeout = tick_rate
                .checked_sub(last_tick.elapsed())
                .unwrap_or_else(|| Duration::from_secs(0));

            if crossterm::event::poll(timeout)? {
                if let Event::Key(key) = event::read()? {
                    if key.kind == KeyEventKind::Press {
                        self.handle_key(key.code).await;
                    }
                }
            }

            if last_tick.elapsed() >= tick_rate {
                self.on_tick().await;
                last_tick = tokio::time::Instant::now();
            }
        }
        Ok(())
    }

    async fn handle_key(&mut self, code: KeyCode) {
        match self.screen {
            CurrentScreen::Splash => {
                if code == KeyCode::Enter {
                    self.screen = CurrentScreen::Wizard;
                }
            }
            CurrentScreen::Wizard => {
                match code {
                    KeyCode::Enter => {
                        if self.wizard.step == crate::wizard::WizardStep::Review {
                            self.start_deployment().await;
                        } else {
                            if self.wizard.commit_step() {
                                self.wizard.advance();
                            }
                        }
                    }
                    KeyCode::Backspace => {
                        if self.wizard.step == crate::wizard::WizardStep::Review {
                            self.wizard.retreat();
                        } else {
                            self.wizard.input.pop();
                        }
                    }
                    KeyCode::Left => {
                        if self.wizard.step == crate::wizard::WizardStep::Color {
                            if self.wizard.selected_preset > 0 {
                                self.wizard.selected_preset -= 1;
                            }
                        }
                    }
                    KeyCode::Right => {
                        if self.wizard.step == crate::wizard::WizardStep::Color {
                            let max = crate::wizard::WizardStep::presets().len() - 1;
                            if self.wizard.selected_preset < max {
                                self.wizard.selected_preset += 1;
                            }
                        }
                    }
                    KeyCode::Char(c) => {
                        self.wizard.input.push(c);
                    }
                    KeyCode::Esc => self.should_quit = true,
                    _ => {}
                }
            }
            CurrentScreen::Progress => {}
            CurrentScreen::Done => {
                if code == KeyCode::Enter {
                    self.should_quit = true;
                }
            }
            CurrentScreen::Error => {
                if code == KeyCode::Enter {
                    self.should_quit = true;
                }
            }
        }
    }

    async fn on_tick(&mut self) {
        // Nothing needed on tick for now
    }

    async fn start_deployment(&mut self) {
        self.screen = CurrentScreen::Progress;
        self.docker_logs.clear();

        if let Err(e) = check_docker().await {
            self.error_message = Some(format!("Docker check failed: {}", e));
            self.screen = CurrentScreen::Error;
            return;
        }

        let compose_cmd = match check_compose().await {
            Ok(cmd) => cmd,
            Err(e) => {
                self.error_message = Some(format!("Compose check failed: {}", e));
                self.screen = CurrentScreen::Error;
                return;
            }
        };

        let bound = check_ports().await;
        if !bound.is_empty() {
            self.docker_logs.push(format!("Warning: ports already bound: {:?}", bound));
            self.docker_logs.push("You may need to free these ports or edit docker-compose.yml".into());
        }

        let cwd = std::path::PathBuf::from("./openhack");
        if !cwd.exists() {
            self.docker_logs.push("Cloning openhack repository...".into());
            let clone = tokio::process::Command::new("git")
                .args(["clone", "https://github.com/mintychochip/openhack.git", "./openhack"])
                .output()
                .await;
            if let Ok(out) = clone {
                if !out.status.success() {
                    let stderr = String::from_utf8_lossy(&out.stderr);
                    self.error_message = Some(format!("Git clone failed:\n{}", stderr));
                    self.screen = CurrentScreen::Error;
                    return;
                }
            } else {
                self.error_message = Some("Failed to run git clone. Is git installed?".into());
                self.screen = CurrentScreen::Error;
                return;
            }
        }

        let env_path = cwd.join(".env");
        if env_path.exists() {
            self.docker_logs.push("Existing .env found — overwriting with new configuration".into());
        }
        if let Err(e) = self.wizard.config.write_env(&env_path) {
            self.error_message = Some(format!("Failed to write .env: {}", e));
            self.screen = CurrentScreen::Error;
            return;
        }
        self.docker_logs.push("Configuration written to .env".into());

        let (log_tx, mut log_rx) = tokio::sync::mpsc::unbounded_channel::<String>();
        let runner = ComposeRunner::new(compose_cmd, cwd.clone());

        let docker_handle = tokio::spawn(async move {
            runner.run_streaming(log_tx).await
        });

        loop {
            while let Ok(line) = log_rx.try_recv() {
                self.docker_logs.push(line);
            }

            if docker_handle.is_finished() {
                while let Ok(line) = log_rx.try_recv() {
                    self.docker_logs.push(line);
                }
                match docker_handle.await {
                    Ok(Ok(())) => {
                        self.screen = CurrentScreen::Done;
                        return;
                    }
                    Ok(Err(e)) => {
                        self.error_message = Some(format!("Docker Compose failed: {}", e));
                        self.screen = CurrentScreen::Error;
                        return;
                    }
                    Err(e) => {
                        self.error_message = Some(format!("Docker task panicked: {}", e));
                        self.screen = CurrentScreen::Error;
                        return;
                    }
                }
            }

            tokio::time::sleep(Duration::from_millis(100)).await;
        }
    }
}
