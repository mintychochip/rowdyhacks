use crossterm::event::{self, Event, KeyCode, KeyEvent, KeyEventKind, KeyModifiers};
use ratatui::{backend::Backend, Terminal};
use std::path::PathBuf;
use std::time::{Duration, Instant};

use crate::config::InstallConfig;
use crate::containers::{
    compose_down, compose_restart, compose_up, container_logs, list_containers, ContainerInfo,
};
use crate::docker::{check_compose, check_docker, check_ports, ComposeRunner};
use crate::env_editor::EnvFile;
use crate::ui::draw;
use crate::wizard::Wizard;

pub enum CurrentScreen {
    Splash,
    MainMenu,
    Wizard,
    ConfigEditor,
    DiscordBotConfig,
    ContainerMonitor,
    LogViewer,
    InstallingDeps,
    Progress,
    Done,
    Error,
}

pub const MENU_ITEMS: &[&str] = &[
    "Deploy OpenHack",
    "Edit Configuration",
    "Discord Bot Settings",
    "Container Monitor",
    "Quit",
];

pub const DISCORD_FIELDS: &[(&str, &str)] = &[
    ("DISCORD_BOT_TOKEN", "Bot Token"),
    ("DISCORD_CHANNEL_ID", "Channel ID"),
    ("DISCORD_WEBHOOK_URL", "Webhook URL"),
    ("DISCORD_CLIENT_ID", "Client ID"),
    ("DISCORD_CLIENT_SECRET", "Client Secret"),
];

pub struct App {
    pub screen: CurrentScreen,
    pub wizard: Wizard,
    pub install_logs: Vec<String>,
    pub error_message: Option<String>,
    pub should_quit: bool,
    pub operation_rx: Option<tokio::sync::mpsc::UnboundedReceiver<String>>,
    pub operation_handle: Option<tokio::task::JoinHandle<color_eyre::Result<()>>>,
    pub menu_selected: usize,
    pub env_file: Option<EnvFile>,
    pub config_field_index: usize,
    pub config_editing: bool,
    pub containers: Vec<ContainerInfo>,
    pub container_selected: usize,
    pub last_container_refresh: Instant,
    pub log_target: Option<String>,
    pub discord_config: InstallConfig,
    pub discord_field_index: usize,
    pub discord_editing: bool,
    pub compose_cwd: PathBuf,
}

impl App {
    pub fn new() -> Self {
        let cwd = PathBuf::from("./openhack");
        let env_path = cwd.join(".env");
        let env_file = if env_path.exists() {
            EnvFile::load(&env_path).ok()
        } else {
            None
        };
        let discord_config = InstallConfig::read_env(&env_path).unwrap_or_default();
        Self {
            screen: CurrentScreen::Splash,
            wizard: Wizard::new(),
            install_logs: vec![],
            error_message: None,
            should_quit: false,
            operation_rx: None,
            operation_handle: None,
            menu_selected: 0,
            env_file,
            config_field_index: 0,
            config_editing: false,
            containers: vec![],
            container_selected: 0,
            last_container_refresh: Instant::now() - Duration::from_secs(10),
            log_target: None,
            discord_config,
            discord_field_index: 0,
            discord_editing: false,
            compose_cwd: cwd,
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
                        self.handle_key(key).await;
                    }
                }
            }

            if last_tick.elapsed() >= tick_rate {
                self.on_tick().await;
                last_tick = tokio::time::Instant::now();
            }

            if let Some(ref mut rx) = self.operation_rx {
                while let Ok(line) = rx.try_recv() {
                    self.install_logs.push(line);
                }
            }
        }
        Ok(())
    }

    async fn handle_key(&mut self, key: KeyEvent) {
        if key.code == KeyCode::Char('c') && key.modifiers.contains(KeyModifiers::CONTROL) {
            self.should_quit = true;
            return;
        }

        match self.screen {
            CurrentScreen::Splash => {
                if key.code == KeyCode::Enter {
                    self.screen = CurrentScreen::MainMenu;
                }
            }
            CurrentScreen::MainMenu => match key.code {
                KeyCode::Up => {
                    if self.menu_selected > 0 {
                        self.menu_selected -= 1;
                    }
                }
                KeyCode::Down => {
                    if self.menu_selected + 1 < MENU_ITEMS.len() {
                        self.menu_selected += 1;
                    }
                }
                KeyCode::Enter => match self.menu_selected {
                    0 => self.screen = CurrentScreen::Wizard,
                    1 => self.screen = CurrentScreen::ConfigEditor,
                    2 => self.screen = CurrentScreen::DiscordBotConfig,
                    3 => self.screen = CurrentScreen::ContainerMonitor,
                    4 => self.should_quit = true,
                    _ => {}
                },
                _ => {}
            },
            CurrentScreen::Wizard => {
                match key.code {
                    KeyCode::Enter => {
                        if self.wizard.step() == crate::wizard::WizardStep::Review {
                            self.start_deployment().await;
                        } else {
                            if self.wizard.commit_step() {
                                self.wizard.advance();
                            }
                        }
                    }
                    KeyCode::Backspace => {
                        if self.wizard.step() == crate::wizard::WizardStep::Review {
                            self.wizard.retreat();
                        } else {
                            self.wizard.input.pop();
                        }
                    }
                    KeyCode::Left => {
                        if self.wizard.step() == crate::wizard::WizardStep::Color {
                            if self.wizard.selected_preset > 0 {
                                self.wizard.selected_preset -= 1;
                            }
                        }
                    }
                    KeyCode::Right => {
                        if self.wizard.step() == crate::wizard::WizardStep::Color {
                            let max = crate::wizard::WizardStep::presets().len() - 1;
                            if self.wizard.selected_preset < max {
                                self.wizard.selected_preset += 1;
                            }
                        }
                    }
                    KeyCode::Char(c) => {
                        self.wizard.input.push(c);
                    }
                    KeyCode::Esc => self.screen = CurrentScreen::MainMenu,
                    _ => {}
                }
            }
            CurrentScreen::ConfigEditor => match key.code {
                KeyCode::Up => {
                    if self.config_field_index > 0 {
                        self.config_field_index -= 1;
                    }
                }
                KeyCode::Down => {
                    if let Some(ref _env) = self.env_file {
                        if self.config_field_index + 1 < _env.entries.len() {
                            self.config_field_index += 1;
                        }
                    }
                }
                KeyCode::Enter => {
                    self.config_editing = !self.config_editing;
                }
                KeyCode::Char('s') => {
                    if let Some(ref mut env) = self.env_file {
                        if let Err(e) = env.save() {
                            self.error_message = Some(format!("Failed to save .env: {}", e));
                            self.screen = CurrentScreen::Error;
                        }
                    }
                }
                KeyCode::Char(c) => {
                    if self.config_editing {
                        if let Some(ref mut env) = self.env_file {
                            if let Some((ref _k, ref mut v)) = env.entries.get_mut(self.config_field_index) {
                                v.push(c);
                            }
                        }
                    }
                }
                KeyCode::Backspace => {
                    if self.config_editing {
                        if let Some(ref mut env) = self.env_file {
                            if let Some((_, ref mut v)) = env.entries.get_mut(self.config_field_index) {
                                v.pop();
                            }
                        }
                    }
                }
                KeyCode::Esc => {
                    self.config_editing = false;
                    self.screen = CurrentScreen::MainMenu;
                }
                _ => {}
            },
            CurrentScreen::DiscordBotConfig => match key.code {
                KeyCode::Up => {
                    if self.discord_field_index > 0 {
                        self.discord_field_index -= 1;
                    }
                }
                KeyCode::Down => {
                    if self.discord_field_index + 1 < DISCORD_FIELDS.len() {
                        self.discord_field_index += 1;
                    }
                }
                KeyCode::Enter => {
                    self.discord_editing = !self.discord_editing;
                }
                KeyCode::Char('s') => {
                    if !self.discord_editing {
                        let env_path = self.compose_cwd.join(".env");
                        let mut env = if env_path.exists() {
                            EnvFile::load(&env_path).unwrap_or_else(|_| EnvFile::from_map(&env_path, std::collections::HashMap::new()))
                        } else {
                            EnvFile::from_map(&env_path, std::collections::HashMap::new())
                        };
                        env.set("DISCORD_BOT_TOKEN", &self.discord_config.discord_bot_token);
                        env.set("DISCORD_CHANNEL_ID", &self.discord_config.discord_channel_id);
                        env.set("DISCORD_WEBHOOK_URL", &self.discord_config.discord_webhook_url);
                        env.set("DISCORD_CLIENT_ID", &self.discord_config.discord_client_id);
                        env.set("DISCORD_CLIENT_SECRET", &self.discord_config.discord_client_secret);
                        if let Err(e) = env.save() {
                            self.error_message = Some(format!("Failed to save .env: {}", e));
                            self.screen = CurrentScreen::Error;
                        }
                    }
                }
                KeyCode::Char(c) => {
                    if self.discord_editing {
                        match self.discord_field_index {
                            0 => self.discord_config.discord_bot_token.push(c),
                            1 => self.discord_config.discord_channel_id.push(c),
                            2 => self.discord_config.discord_webhook_url.push(c),
                            3 => self.discord_config.discord_client_id.push(c),
                            4 => self.discord_config.discord_client_secret.push(c),
                            _ => {}
                        }
                    }
                }
                KeyCode::Backspace => {
                    if self.discord_editing {
                        match self.discord_field_index {
                            0 => { self.discord_config.discord_bot_token.pop(); }
                            1 => { self.discord_config.discord_channel_id.pop(); }
                            2 => { self.discord_config.discord_webhook_url.pop(); }
                            3 => { self.discord_config.discord_client_id.pop(); }
                            4 => { self.discord_config.discord_client_secret.pop(); }
                            _ => {}
                        }
                    }
                }
                KeyCode::Esc => {
                    self.discord_editing = false;
                    self.screen = CurrentScreen::MainMenu;
                }
                _ => {}
            },
            CurrentScreen::ContainerMonitor => match key.code {
                KeyCode::Up => {
                    if self.container_selected > 0 {
                        self.container_selected -= 1;
                    }
                }
                KeyCode::Down => {
                    if self.container_selected + 1 < self.containers.len() {
                        self.container_selected += 1;
                    }
                }
                KeyCode::Enter => {
                    if let Some(c) = self.containers.get(self.container_selected) {
                        let name = c.name.clone();
                        self.start_log_stream(&name).await;
                    }
                }
                KeyCode::Char('r') => {
                    if let Some(c) = self.containers.get(self.container_selected) {
                        let name = c.name.clone();
                        let cwd = self.compose_cwd.clone();
                        let (tx, rx) = tokio::sync::mpsc::unbounded_channel();
                        self.operation_rx = Some(rx);
                        self.install_logs.clear();
                        self.log_target = Some(name.clone());
                        self.screen = CurrentScreen::InstallingDeps;
                        self.operation_handle = Some(tokio::spawn(async move {
                            compose_restart(tx, cwd, Some(&name)).await
                        }));
                    }
                }
                KeyCode::Char('s') => {
                    let cwd = self.compose_cwd.clone();
                    let (tx, rx) = tokio::sync::mpsc::unbounded_channel();
                    self.operation_rx = Some(rx);
                    self.install_logs.clear();
                    self.log_target = Some("all".into());
                    self.screen = CurrentScreen::InstallingDeps;
                    self.operation_handle = Some(tokio::spawn(async move {
                        compose_down(tx, cwd).await
                    }));
                }
                KeyCode::Char('u') => {
                    let cwd = self.compose_cwd.clone();
                    let (tx, rx) = tokio::sync::mpsc::unbounded_channel();
                    self.operation_rx = Some(rx);
                    self.install_logs.clear();
                    self.log_target = Some("all".into());
                    self.screen = CurrentScreen::InstallingDeps;
                    self.operation_handle = Some(tokio::spawn(async move {
                        compose_up(tx, cwd).await
                    }));
                }
                KeyCode::Esc => self.screen = CurrentScreen::MainMenu,
                _ => {}
            },
            CurrentScreen::LogViewer => {
                if key.code == KeyCode::Esc {
                    self.log_target = None;
                    self.operation_rx = None;
                    self.operation_handle = None;
                    self.screen = CurrentScreen::ContainerMonitor;
                }
            }
            CurrentScreen::InstallingDeps | CurrentScreen::Progress => {
                if key.code == KeyCode::Esc {
                    self.screen = CurrentScreen::ContainerMonitor;
                }
            }
            CurrentScreen::Done => {
                if key.code == KeyCode::Enter {
                    self.screen = CurrentScreen::MainMenu;
                }
            }
            CurrentScreen::Error => {
                if key.code == KeyCode::Enter {
                    self.screen = CurrentScreen::MainMenu;
                    self.error_message = None;
                }
            }
        }
    }

    async fn on_tick(&mut self) {
        if let CurrentScreen::ContainerMonitor = self.screen {
            if self.last_container_refresh.elapsed() >= Duration::from_secs(3) {
                if let Ok(containers) = list_containers().await {
                    self.containers = containers;
                }
                self.last_container_refresh = Instant::now();
            }
        }

        if let Some(ref handle) = self.operation_handle {
            if handle.is_finished() {
                if let Some(handle) = self.operation_handle.take() {
                    match handle.await {
                        Ok(Ok(())) => {
                            if let CurrentScreen::InstallingDeps = self.screen {
                                self.screen = CurrentScreen::ContainerMonitor;
                            }
                        }
                        Ok(Err(e)) => {
                            self.error_message = Some(format!("Operation failed: {}", e));
                            self.screen = CurrentScreen::Error;
                        }
                        Err(e) => {
                            self.error_message = Some(format!("Task panicked: {}", e));
                            self.screen = CurrentScreen::Error;
                        }
                    }
                }
                self.operation_rx = None;
            }
        }
    }

    async fn start_log_stream(&mut self, name: &str) {
        let (tx, rx) = tokio::sync::mpsc::unbounded_channel();
        self.operation_rx = Some(rx);
        self.install_logs.clear();
        self.log_target = Some(name.to_string());
        self.screen = CurrentScreen::LogViewer;
        let name = name.to_string();
        self.operation_handle = Some(tokio::spawn(async move {
            container_logs(&name, 100, tx).await
        }));
    }

    async fn start_deployment(&mut self) {
        self.screen = CurrentScreen::Progress;
        self.install_logs.clear();

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
            self.install_logs.push(format!("Warning: ports already bound: {:?}", bound));
            self.install_logs.push("You may need to free these ports or edit docker-compose.yml".into());
        }

        let cwd = self.compose_cwd.clone();
        if !cwd.exists() {
            self.install_logs.push("Cloning openhack repository...".into());
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
            self.install_logs.push("Existing .env found — overwriting with new configuration".into());
        }
        if let Err(e) = self.wizard.config.write_env(&env_path) {
            self.error_message = Some(format!("Failed to write .env: {}", e));
            self.screen = CurrentScreen::Error;
            return;
        }
        self.install_logs.push("Configuration written to .env".into());

        let (log_tx, mut log_rx) = tokio::sync::mpsc::unbounded_channel::<String>();
        let runner = ComposeRunner::new(compose_cmd, cwd.clone());

        let docker_handle = tokio::spawn(async move {
            runner.run_streaming(log_tx).await
        });

        loop {
            while let Ok(line) = log_rx.try_recv() {
                self.install_logs.push(line);
            }

            if docker_handle.is_finished() {
                while let Ok(line) = log_rx.try_recv() {
                    self.install_logs.push(line);
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
